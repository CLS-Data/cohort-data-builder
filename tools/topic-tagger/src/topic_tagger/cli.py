"""The ``topic-tagger`` command line. Commands and exit codes are in the README."""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from rich.console import Console

from topic_tagger.clock import SystemClock
from topic_tagger.display import RunView
from topic_tagger.prompt import build_messages, build_option_messages
from topic_tagger.providers import Provider, ProviderError, get_provider
from topic_tagger.report import render_report
from topic_tagger.runner import Runner, Settings, install_stop_handler
from topic_tagger.scheme import SchemeError, bundled_scheme_text, load_scheme, scheme_from_json
from topic_tagger.stats import compute_stats
from topic_tagger.store import LockedError, StaleLockError, TagStore
from topic_tagger.tiered import DecisionDecider, build_tree, choice_problems, decision_request
from topic_tagger.variables import InputError, read_variables

OK, SOME_FAILED, BAD_INPUT, NO_HOST, LOCKED, STOPPED = 0, 1, 2, 3, 4, 130
DEFAULT_BASE_URL = "http://localhost:11434/v1"
SUMMARY_TOP = 10  # files or groups listed in the end-of-run summary


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
    if args.command == "report":
        return _report(args.folder, args.group_by)
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
    tag.add_argument(
        "--provider",
        default="ollama",
        help="the model host: ollama (chat models) or ollama-decision (decision models, "
        "e.g. --model clef:cloud)",
    )
    tag.add_argument(
        "--base-url",
        default=os.environ.get("TOPIC_TAGGER_BASE_URL", DEFAULT_BASE_URL),
        help="where the host's API is (also TOPIC_TAGGER_BASE_URL)",
    )
    tag.add_argument("--model", default="gpt-oss:20b", help="model name on the host")
    tag.add_argument(
        "--method",
        choices=["flat", "tiered"],
        help="flat: every topic in one request; tiered: areas first, then topics within them "
        "(default flat; tiered for ollama-decision, which can only tag tiered)",
    )
    tag.add_argument(
        "--descend-at",
        type=float,
        help="tiered: follow an area at this confidence or above (default 0.5)",
    )
    tag.add_argument(
        "--keep-at",
        type=float,
        help="decision models (--provider ollama-decision): keep a topic at this probability "
        "or above; 0 keeps every topic (default 0.3)",
    )
    tag.add_argument(
        "--max-areas",
        type=int,
        help="tiered: follow at most this many areas per variable; 0 for no cap (default 3)",
    )
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
    report = sub.add_parser("report", help="rebuild report.html from a tagged folder")
    report.add_argument("folder", type=Path, help="the folder given to tag --out")
    report.add_argument("--group-by", help="input field to group by (default: the run's)")
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
    problem = _check_method(args)
    if problem:
        _err(problem)
        return BAD_INPUT
    try:
        variables = read_variables(args.variables)
        scheme = load_scheme(args.scheme)
        provider = factory(args)
    except (InputError, SchemeError, ProviderError) as e:
        _err(str(e))
        return BAD_INPUT
    if args.provider == "ollama-decision":
        problems = choice_problems(build_tree(scheme))
        if problems:
            _err("This scheme does not fit a decision model: " + "; ".join(problems) + ".")
            return BAD_INPUT

    if args.dry_run:
        batch = variables[: args.batch_size]
        if args.provider == "ollama-decision":
            _print_decision_requests(args, scheme, variables[0])
            return OK
        if args.method == "tiered":
            _print_tiered_requests(scheme, batch)
            return OK
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


def _check_method(args: argparse.Namespace) -> str | None:
    """Fill in the tiered and decision defaults, or say what is wrong with them."""
    if args.provider != "ollama-decision" and args.keep_at is not None:
        return "--keep-at needs --provider ollama-decision"
    if args.provider == "ollama-decision":
        if args.method == "flat":
            return (
                "--provider ollama-decision tags tiered only: a decision model chooses among "
                "at most 26 options, so it cannot be asked every topic at once"
            )
        args.method = "tiered"
        args.keep_at = 0.3 if args.keep_at is None else args.keep_at
        if not 0 <= args.keep_at <= 1:
            return "--keep-at must be between 0 and 1"
    args.method = args.method or "flat"
    if args.method != "tiered":
        if args.descend_at is not None or args.max_areas is not None:
            return "--descend-at and --max-areas need --method tiered"
        return None
    args.descend_at = 0.5 if args.descend_at is None else args.descend_at
    args.max_areas = 3 if args.max_areas is None else args.max_areas
    if not 0 <= args.descend_at <= 1:
        return "--descend-at must be between 0 and 1"
    if args.max_areas < 0:
        return "--max-areas must be 0 (no cap) or more"
    return None


def _print_tiered_requests(scheme, batch) -> None:
    """Print the tier-1 request and, as an example, the first area's tier-2 request."""
    root = build_tree(scheme)
    system, user = build_option_messages(scheme.guidance, root, batch)
    print(system["content"], user["content"], sep="\n\n---\n\n")
    area = root.children[0]
    print(f"\n--- tier 2 example ({area.label}) ---\n")
    system, user = build_option_messages(scheme.guidance, area, batch)
    print(system["content"], user["content"], sep="\n\n---\n\n")


def _print_decision_requests(args, scheme, variable) -> None:
    """Print the first variable's first request to the decision model, and a tier-2 example."""
    root = build_tree(scheme)
    print(json.dumps(decision_request(args.model, root, variable), indent=1))
    area = root.children[0]
    print(f"\n--- tier 2 example ({area.label}) ---\n")
    print(json.dumps(decision_request(args.model, area, variable), indent=1))


def _run(args, variables, scheme, provider, store, clock, runner_created) -> int:
    store.load()
    chosen = variables
    if args.files:
        wanted = {f.strip() for f in args.files.split(",")}
        chosen = [v for v in chosen if v.file in wanted]

    def current(v) -> bool:
        return store.state(v.key, scheme.hash, args.method) == "current"

    todo = [v for v in chosen if args.retag or not current(v)]
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
        method=args.method,
        descend_at=args.descend_at if args.descend_at is not None else 0.5,
        max_areas=args.max_areas if args.max_areas is not None else 3,
    )
    view = RunView(len(variables), len(todo), scheme, clock)
    decider = None
    if args.provider == "ollama-decision":
        decider = DecisionDecider(provider, keep_at=args.keep_at)
    runner = Runner(
        scheme, provider, store, settings, clock, on_event=view.on_event, decider=decider
    )
    if runner_created:
        runner_created(runner)
    started = clock.now()
    # The live view needs a terminal; logs and pipes get a plain line every 10 seconds.
    if args.plain or not sys.stderr.isatty():
        showing = view.plain(sys.stderr)
    else:
        showing = view.live(Console(stderr=True))
    restore = install_stop_handler(runner)
    try:
        with showing:
            result = runner.run(todo)
    finally:
        restore()
    store.compact()

    run = _run_record(
        args, scheme, started, clock.now(), result, len(variables), len(todo), skipped
    )
    run["timeline"] = view.timeline()
    store.load()
    stats = _save(store.folder, run, store.records.values(), variables, scheme, args.group_by)
    print(
        f"Tagged {result.tagged} of {len(todo)} variables in "
        f"{result.requests} requests; {len(result.failed)} failed."
    )
    print(_summary(run, stats, scheme, store.folder))
    if args.method == "tiered":
        print(_tier_lines(result))
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


def _run_record(args, scheme, started, ended, result, total, todo, skipped) -> dict:
    """This run's settings, counts and failures, as saved in ``run.json``."""
    return {
        "started": _iso(started),
        "ended": _iso(ended),
        "status": "stopped" if result.stopped else "finished",
        # No API key here: it is only ever read from the environment.
        "settings": {
            "provider": args.provider,
            "base_url": args.base_url,
            "model": args.model,
            "method": args.method,
            **(
                {"descend_at": args.descend_at, "max_areas": args.max_areas}
                if args.method == "tiered"
                else {}
            ),
            **({"keep_at": args.keep_at} if args.provider == "ollama-decision" else {}),
            "batch_size": args.batch_size,
            "workers": args.workers,
            "timeout": args.timeout,
            "retries": args.retries,
            "files": args.files,
            "limit": args.limit,
            "retag": args.retag,
            "group_by": args.group_by,
            "variables": str(args.variables),
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
            "requests_by_tier": result.requests_by_tier or [result.requests],
            "retries": result.retries,
            "singles": result.singles,
        },
        "failed": result.failed,
    }


def _save(folder: Path, run: dict, records, variables, scheme, group_by: str) -> dict:
    """Work out the statistics, then write ``run.json`` with them and ``report.html``."""
    run.pop("stats", None)
    stats = compute_stats(records, variables, scheme, run, group_by)
    (folder / "report.html").write_text(render_report(run, stats, scheme), encoding="utf-8")
    text = json.dumps({**run, "stats": stats}, ensure_ascii=False, indent=1)
    (folder / "run.json").write_text(text + "\n", encoding="utf-8")
    return stats


def _tier_lines(result) -> str:
    """Requests per tier and areas followed per variable, for a tiered run's summary."""
    tiers = ", ".join(f"{i}: {n}" for i, n in enumerate(result.requests_by_tier, 1))
    mean = result.areas_followed / result.tagged if result.tagged else 0
    return f"Requests by tier: {tiers or 'none'}\nAreas followed per variable: {mean:.1f}"


def _summary(run: dict, stats: dict, scheme, folder: Path) -> str:
    """The end-of-run statistics, as lines for the terminal."""
    s = run["settings"]
    domain = {d.id: d.label for d in scheme.domains}
    topic = {t.id: t.label for t in scheme.topics}

    def counts(pairs, label=str) -> str:
        return ", ".join(f"{label(k)} {n}" for k, n in pairs) or "none"

    def largest(pairs) -> str:
        # Largest first (ties in their given order), at most SUMMARY_TOP, then the rest counted.
        pairs = sorted(pairs, key=lambda x: -x[1])
        rest = len(pairs) - SUMMARY_TOP
        return counts(pairs[:SUMMARY_TOP]) + (f", and {rest} more" if rest > 0 else "")

    areas = sorted(stats["per_domain"].items(), key=lambda x: -x[1])
    leading = sorted(stats["per_topic"].items(), key=lambda x: -x[1])[:10]
    bins = stats["confidence_histogram"]
    run_time = _hms(_seconds_between(run["started"], run["ended"]))
    lines = [
        f"Run time {run_time}, {stats['speed']:g} variables/min; "
        f"{run['counts']['skipped']} already tagged were skipped.",
        f"Model {s['provider']}:{s['model']}; scheme {scheme.name} version {scheme.version} "
        f"(hash {scheme.hash}).",
        f"Mean topics per variable: {stats['mean_topics']:.1f}. "
        f"Only below 50%: {stats['below_default']:.0%}.",
        "Confidence (tags per tenth, 0 to 1): " + " ".join(str(b) for b in bins),
        f"Topic areas: {counts([a for a in areas if a[1]], domain.get)}",
        f"Leading topics: {counts([t for t in leading if t[1]], topic.get)}",
        f"Unused topics: {len(stats['unused'])} of {len(topic)}",
        "By file: " + largest((f, c["tagged"]) for f, c in stats["per_file"].items()),
    ]
    if stats["per_group"]:
        lines.append(f"By {stats['group_by']}: {largest(stats['per_group'].items())}")
    lines.append(f"Report: {folder / 'report.html'}")
    return "\n".join(lines)


def _hms(seconds: float) -> str:
    s = round(seconds)
    return f"{s // 3600:02d}:{s // 60 % 60:02d}:{s % 60:02d}"


def _seconds_between(start: str, end: str) -> float:
    def parse(t: str) -> datetime:
        return datetime.fromisoformat(t.replace("Z", "+00:00"))

    return (parse(end) - parse(start)).total_seconds()


def _report(folder: Path, group_by: str | None) -> int:
    try:
        run = json.loads((folder / "run.json").read_text(encoding="utf-8"))
        scheme = scheme_from_json(json.loads((folder / "scheme.json").read_text(encoding="utf-8")))
    except (OSError, ValueError, KeyError) as e:
        _err(f"{folder} has no usable run.json and scheme.json from a tagging run: {e}")
        return BAD_INPUT
    try:
        variables = read_variables(Path(run["settings"]["variables"]))
    except InputError as e:
        _err(f"the variables file this run tagged is needed to group the statistics: {e}")
        return BAD_INPUT
    store = TagStore(folder)
    store.load()
    group_by = group_by or run["settings"].get("group_by", "sweep")
    _save(folder, run, store.records.values(), variables, scheme, group_by)
    print(f"Wrote {folder / 'report.html'}")
    return OK


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
