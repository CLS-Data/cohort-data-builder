"""The ``topic-tagger`` command line. Commands and exit codes are in the README."""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from topic_tagger.clock import SystemClock
from topic_tagger.prompt import build_messages
from topic_tagger.providers import Provider, ProviderError, get_provider
from topic_tagger.runner import Runner, Settings, install_stop_handler
from topic_tagger.scheme import SchemeError, bundled_scheme_text, load_scheme
from topic_tagger.store import LockedError, StaleLockError, TagStore
from topic_tagger.variables import InputError, read_variables

OK, SOME_FAILED, BAD_INPUT, NO_HOST, LOCKED, STOPPED = 0, 1, 2, 3, 4, 130
DEFAULT_BASE_URL = "http://localhost:11434/v1"


def main(
    argv: list[str] | None = None,
    provider_factory: Callable[[argparse.Namespace], Provider] | None = None,
    clock=None,
    runner_created: Callable[[Runner], None] | None = None,
) -> int:
    """Run the command line.

    Args:
        argv: Arguments without the program name; defaults to ``sys.argv[1:]``.
        provider_factory: Makes the model host from the parsed options; tests pass a
            stand-in. Defaults to the provider named by ``--provider``.
        clock: The clock; defaults to the real time.
        runner_created: Called with the runner before it starts; tests use it to stop a
            run part way.

    Returns:
        The exit code.
    """
    args = _parser().parse_args(argv)
    if args.command == "tag":
        return _tag(args, provider_factory or _provider, clock or SystemClock(), runner_created)
    if args.command == "check-scheme":
        return _check_scheme(args.scheme)
    if args.command == "init-scheme":
        return _init_scheme(args.path)
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
    tag.add_argument(
        "--scheme",
        type=Path,
        required=True,
        help="scheme file: the topics and instructions (start one with init-scheme)",
    )
    tag.add_argument(
        "--group-by", default="sweep", help="input field the statistics are grouped by"
    )
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

    check = sub.add_parser("check-scheme", help="check a scheme file and list every mistake")
    check.add_argument("scheme", type=Path, help="the scheme file")
    init = sub.add_parser("init-scheme", help="copy the bundled example scheme to a file, to edit")
    init.add_argument("path", type=Path, help="where to write it; never overwrites")
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


def _tag(args: argparse.Namespace, factory, clock, runner_created) -> int:
    try:
        variables = read_variables(args.variables)
        scheme = load_scheme(args.scheme)
        provider = factory(args)
    except (InputError, SchemeError, ProviderError) as e:
        _err(str(e))
        return BAD_INPUT

    if args.dry_run:
        batch = variables[: args.batch_size]
        system, user = build_messages(scheme, batch)
        print(system["content"], user["content"], sep="\n\n---\n\n")
        return OK

    store = TagStore(args.out)
    try:
        store.lock(force=args.force)
    except (LockedError, StaleLockError) as e:
        _err(str(e))
        return LOCKED
    try:
        return _run(args, variables, scheme, provider, store, clock, runner_created)
    finally:
        store.unlock()


def _run(args, variables, scheme, provider, store, clock, runner_created) -> int:
    store.load()
    chosen = variables
    if args.files:
        wanted = {f.strip() for f in args.files.split(",")}
        chosen = [v for v in chosen if v.file in wanted]
    todo = [v for v in chosen if args.retag or store.state(v.key, scheme.hash) != "current"]
    skipped = len(chosen) - len(todo)
    if args.limit is not None:
        todo = todo[: args.limit]
    _err(f"{skipped} already tagged, {len(todo)} to do")
    if not todo:
        return OK

    if provider.is_remote() and not args.yes and not _confirm_remote(args):
        return BAD_INPUT
    try:
        provider.check()
    except ProviderError as e:
        _err(str(e))
        return NO_HOST

    store.write_scheme(scheme)
    settings = Settings(
        batch_size=args.batch_size,
        workers=args.workers,
        retries=args.retries,
        model=f"{args.provider}:{args.model}",
    )
    runner = Runner(scheme, provider, store, settings, clock)
    if runner_created:
        runner_created(runner)
    started = clock.now()
    restore = install_stop_handler(runner)
    try:
        result = runner.run(todo)
    finally:
        restore()
    store.compact()

    _write_run(
        args, store, scheme, started, clock.now(), result, len(variables), len(todo), skipped
    )
    print(
        f"Tagged {result.tagged} of {len(todo)} variables in "
        f"{result.requests} requests; {len(result.failed)} failed."
    )
    if result.stopped:
        _err("Stopped. Run the same command again to carry on.")
    if result.failed:
        _err("Could not tag:\n  " + "\n  ".join(result.failed))
        if result.last_error:
            _err(f"Last error: {result.last_error}")
    if result.stopped:
        return STOPPED
    return SOME_FAILED if result.failed else OK


def _iso(t: float) -> str:
    return datetime.fromtimestamp(t, UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _write_run(args, store, scheme, started, ended, result, total, todo, skipped) -> None:
    """Write ``run.json``: the settings, counts and failures of this run."""
    run = {
        "started": _iso(started),
        "ended": _iso(ended),
        "status": "stopped" if result.stopped else "finished",
        # No API key here: it is only ever read from the environment.
        "settings": {
            "provider": args.provider,
            "base_url": args.base_url,
            "model": args.model,
            "batch_size": args.batch_size,
            "workers": args.workers,
            "timeout": args.timeout,
            "retries": args.retries,
            "files": args.files,
            "limit": args.limit,
            "retag": args.retag,
            "group_by": args.group_by,
            "scheme": str(args.scheme),
            "scheme_hash": scheme.hash,
        },
        "counts": {
            "total": total,
            "todo": todo,
            "tagged": result.tagged,
            "skipped": skipped,
            "failed": len(result.failed),
            "requests": result.requests,
            "retries": result.retries,
            "singles": result.singles,
        },
        "failed": result.failed,
    }
    text = json.dumps(run, ensure_ascii=False, indent=1)
    (store.folder / "run.json").write_text(text + "\n", encoding="utf-8")


def _check_scheme(path: Path) -> int:
    try:
        scheme = load_scheme(path)
    except SchemeError as e:
        _err(str(e))
        return BAD_INPUT
    print(
        f"{scheme.name} (version {scheme.version}): {len(scheme.domains)} domains, "
        f"{len(scheme.topic_ids)} topics, hash {scheme.hash}"
    )
    return OK


def _init_scheme(path: Path) -> int:
    if path.exists():
        _err(f"{path} already exists; choose another name or delete it first")
        return BAD_INPUT
    path.write_text(bundled_scheme_text(), encoding="utf-8")
    print(f"Wrote {path}. Edit it, check it with: topic-tagger check-scheme {path}")
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
