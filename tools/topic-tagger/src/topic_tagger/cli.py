"""The ``topic-tagger`` command line. Commands and exit codes are in the README."""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Callable
from pathlib import Path

from topic_tagger.clock import SystemClock
from topic_tagger.prompt import build_messages
from topic_tagger.providers import Provider, ProviderError, get_provider
from topic_tagger.runner import Runner, Settings
from topic_tagger.scheme import SchemeError, load_scheme
from topic_tagger.store import TagStore
from topic_tagger.variables import InputError, read_variables

OK, SOME_FAILED, BAD_INPUT, NO_HOST, LOCKED = 0, 1, 2, 3, 4
DEFAULT_BASE_URL = "http://localhost:11434/v1"


def main(
    argv: list[str] | None = None,
    provider_factory: Callable[[argparse.Namespace], Provider] | None = None,
    clock=None,
) -> int:
    """Run the command line.

    Args:
        argv: Arguments without the program name; defaults to ``sys.argv[1:]``.
        provider_factory: Makes the model host from the parsed options; tests pass a
            stand-in. Defaults to the provider named by ``--provider``.
        clock: The clock; defaults to the real time.

    Returns:
        The exit code.
    """
    args = _parser().parse_args(argv)
    if args.command == "tag":
        return _tag(args, provider_factory or _provider, clock or SystemClock())
    _parser().print_help(sys.stderr)
    return BAD_INPUT


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="topic-tagger", description="Tag survey variables by topic with a language model."
    )
    sub = parser.add_subparsers(dest="command")
    tag = sub.add_parser(
        "tag",
        help="tag the variables in a variables.jsonl file",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    tag.add_argument("variables", type=Path, help="the variables.jsonl file to tag")
    tag.add_argument("--out", type=Path, required=True, help="output folder for the tags")
    tag.add_argument("--scheme", type=Path, help="scheme file (default: the bundled CLOSER one)")
    tag.add_argument("--provider", default="ollama", help="the model host")
    tag.add_argument(
        "--base-url",
        default=os.environ.get("TOPIC_TAGGER_BASE_URL", DEFAULT_BASE_URL),
        help="where the host's API is (also TOPIC_TAGGER_BASE_URL)",
    )
    tag.add_argument("--model", default="gpt-oss:20b", help="model name on the host")
    tag.add_argument("--batch-size", type=int, default=20, help="variables per request")
    tag.add_argument("--workers", type=int, default=2, help="requests in flight at once")
    tag.add_argument(
        "--timeout", type=float, default=120, help="seconds before a request is retried"
    )
    tag.add_argument(
        "--retries", type=int, default=2, help="retries per batch before one at a time"
    )
    tag.add_argument("--files", help="tag only these data files, comma-separated")
    tag.add_argument("--limit", type=int, help="tag at most this many variables")
    tag.add_argument("--retag", action="store_true", help="redo variables that have current tags")
    tag.add_argument("--dry-run", action="store_true", help="print the first request; send nothing")
    tag.add_argument("--yes", action="store_true", help="do not ask before using a remote model")
    tag.add_argument("--plain", action="store_true", help="plain progress lines, no live display")
    tag.add_argument("--force", action="store_true", help="clear a lock left by a run that ended")
    return parser


def _provider(args: argparse.Namespace) -> Provider:
    # The key comes only from the environment, so it is never in shell history or run.json.
    return get_provider(
        args.provider,
        base_url=args.base_url,
        model=args.model,
        timeout=args.timeout,
        api_key=os.environ.get("TOPIC_TAGGER_API_KEY"),
    )


def _err(message: str) -> None:
    print(message, file=sys.stderr)


def _tag(args: argparse.Namespace, factory, clock) -> int:
    try:
        variables = read_variables(args.variables)
        scheme = load_scheme(args.scheme)
        provider = factory(args)
    except (InputError, SchemeError, ProviderError) as e:
        _err(str(e))
        return BAD_INPUT

    if args.dry_run:
        batch = [v for v in variables if not v.identifier][: args.batch_size]
        system, user = build_messages(scheme, batch)
        print(system["content"], user["content"], sep="\n\n---\n\n")
        return OK

    if provider.is_remote() and not args.yes and not _confirm_remote(args):
        return BAD_INPUT
    try:
        provider.check()
    except ProviderError as e:
        _err(str(e))
        return NO_HOST

    store = TagStore(args.out)
    store.write_scheme(scheme)
    settings = Settings(
        batch_size=args.batch_size,
        workers=args.workers,
        retries=args.retries,
        model=f"{args.provider}:{args.model}",
    )
    result = Runner(scheme, provider, store, settings, clock).run(variables)
    rule = sum(v.identifier for v in variables)
    print(
        f"Tagged {result.tagged} of {len(variables)} variables ({rule} by rule) in "
        f"{result.requests} requests; {len(result.failed)} failed."
    )
    if result.failed:
        _err("Could not tag:\n  " + "\n  ".join(result.failed))
        if result.last_error:
            _err(f"Last error: {result.last_error}")
        return SOME_FAILED
    return OK


def _confirm_remote(args: argparse.Namespace) -> bool:
    message = (
        f"The model {args.model} at {args.base_url} does not run on this machine: variable "
        "names, labels and value labels will leave this machine (no study data is sent)."
    )
    if not sys.stdin.isatty():
        _err(message + " Run again with --yes to allow this.")
        return False
    _err(message)
    return input("Continue? [y/N] ").strip().lower() in ("y", "yes")
