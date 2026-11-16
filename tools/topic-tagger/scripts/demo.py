"""Run the topic tagger through every feature, one run at a time, and check each result.

Every run uses the fictional fixture variables in ``tests/fixtures/variables.jsonl`` (a few
of them, so the runs are short and cheap) and checks what the run wrote: exit codes,
``run.json``, ``tags.jsonl`` and ``scheme.json``.

What it covers:

- **Without a model** (``--offline`` runs only these): ``check-scheme`` on one-, two- and
  three-tier schemes and on a bad one; bad ``[run]`` values and options refused with exit 2;
  dry runs printing every tier, with the scheme's questions and guidance, for both kinds
  of model.
- **With models**: one, two and three tiers × chat and decision model × flat and tiered
  (twelve runs); a decision model refusing a question with too many options, flat and at a
  group (exit 5); a scheme's ``[run]`` table driving a run on its own; carrying on from
  where a run stopped; editing ``[run]`` keeping the tags, editing ``[questions]`` or the
  method redoing them.

Run it from ``tools/topic-tagger``::

    uv run python scripts/demo.py --offline              # no model needed
    uv run python scripts/demo.py --yes                  # every step; Ollama must be running
    uv run python scripts/demo.py --yes --only refus     # only the steps whose name matches

Models default to ``gpt-oss:20b-cloud`` (chat) and ``clef:cloud`` (decision), both through
the local Ollama. Cloud models send the variables' metadata off this machine, so model steps
need ``--yes``. Every run's folder is kept under ``--out`` to look at afterwards.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

TOOL = Path(__file__).resolve().parents[1]
FIXTURES = TOOL / "tests" / "fixtures"
SCHEMES = TOOL / "src" / "topic_tagger" / "schemes"
VARIABLES = FIXTURES / "variables.jsonl"
SCHEME_1 = SCHEMES / "example-1-tier.toml"
SCHEME_2 = FIXTURES / "scheme_small.toml"
SCHEME_3 = SCHEMES / "example-3-tier.toml"
CLOSER = SCHEMES / "closer.toml"
CLOSER_HASH = "3c9f6b4b4ef9"  # the bundled scheme's hash since 004: it must not change
GUIDANCE_START = "You are classifying variables from a UK cohort study"  # example-3-tier


@dataclass
class Result:
    """One command's outcome."""

    code: int
    out: str
    err: str


@dataclass
class Check:
    """One expectation and whether it held; ``detail`` says what was seen."""

    what: str
    ok: bool
    detail: str = ""


@dataclass
class Step:
    """A named demonstration: one or more commands, then checks on what they wrote."""

    name: str
    needs_model: bool
    run: Callable[[Context], list[Check]]
    checks: list[Check] = field(default_factory=list)
    seconds: float = 0.0


class Context:
    """Paths, models and helpers shared by the steps.

    Args:
        args: The parsed command line.
        out: The folder every run's output goes under.
    """

    def __init__(self, args: argparse.Namespace, out: Path):
        self.args = args
        self.out = out
        self.variables = out / "variables.jsonl"
        lines = VARIABLES.read_text(encoding="utf-8").splitlines()
        n = max(2, min(args.variables, len(lines)))
        # Spread out across the file, so the sample covers several topics.
        picks = sorted({round(i * (len(lines) - 1) / (n - 1)) for i in range(n)})
        self.variables.write_text("\n".join(lines[i] for i in picks) + "\n", encoding="utf-8")
        self.n = len(picks)

    def cli(self, *args) -> Result:
        """Run ``topic-tagger`` with ``args`` in this Python, never waiting for input."""
        done = subprocess.run(
            [sys.executable, "-m", "topic_tagger", *map(str, args)],
            cwd=TOOL,
            capture_output=True,
            text=True,
            stdin=subprocess.DEVNULL,
            timeout=self.args.timeout,
        )
        return Result(done.returncode, done.stdout, done.stderr)

    def tag(self, folder: str, *extra) -> Result:
        """``topic-tagger tag`` on the sample variables, into ``out/folder``."""
        host = ["--base-url", self.args.base_url] if self.args.base_url else []
        yes = ["--yes"] if self.args.yes else []
        return self.cli(
            "tag", self.variables, "--out", self.out / folder, "--plain", *host, *yes, *extra
        )

    def model(self, kind: str) -> tuple[str, ...]:
        """The provider and model options for ``chat`` or ``decision``."""
        if kind == "chat":
            return ("--provider", "ollama", "--model", self.args.chat_model)
        return ("--provider", "ollama-decision", "--model", self.args.decision_model)

    def run_json(self, folder: str) -> dict:
        """The run's ``run.json``."""
        return json.loads((self.out / folder / "run.json").read_text(encoding="utf-8"))

    def records(self, folder: str) -> list[dict]:
        """The current record per variable in ``tags.jsonl`` (the last line wins)."""
        latest = {}
        path = self.out / folder / "tags.jsonl"
        for line in path.read_text(encoding="utf-8").splitlines() if path.exists() else []:
            r = json.loads(line)
            latest[(r["file"], r["variable"])] = r
        return list(latest.values())

    def taxonomy(self, folder: str) -> tuple[set[str], set[str]]:
        """The leaf ids and group ids of the scheme the run saved."""
        scheme = json.loads((self.out / folder / "scheme.json").read_text(encoding="utf-8"))
        leaves, groups = set(), set()

        def visit(items):
            for c in items:
                if c.get("categories"):
                    groups.add(c["id"])
                    visit(c["categories"])
                else:
                    leaves.add(c["id"])

        visit(scheme["categories"])
        return leaves, groups

    def copy_scheme(self, source: Path, name: str, *edits: tuple[str, str]) -> Path:
        """Copy a scheme into the output folder, applying ``(old, new)`` text edits."""
        text = source.read_text(encoding="utf-8")
        for old, new in edits:
            if old not in text:
                raise ValueError(f"{old!r} is not in {source.name}")
            text = text.replace(old, new, 1)
        path = self.out / name
        path.write_text(text, encoding="utf-8")
        return path


def tail(text: str, lines: int = 6) -> str:
    """The last few lines of ``text``, for showing what went wrong."""
    return " | ".join(text.strip().splitlines()[-lines:])


def exit_is(r: Result, *codes: int) -> Check:
    """Check the exit code, showing the end of stderr when it is wrong."""
    ok = r.code in codes
    want = " or ".join(map(str, codes))
    return Check(f"exit {want}", ok, f"exit {r.code}" + ("" if ok else f": {tail(r.err)}"))


def to_do(r: Result) -> tuple[int, int] | None:
    """``(already tagged, to do)`` from a run's first line on stderr."""
    m = re.search(r"(\d+) already tagged, (\d+) to do", r.err)
    return (int(m[1]), int(m[2])) if m else None


# --- Without a model --------------------------------------------------------------------


def check_schemes(ctx: Context) -> list[Check]:
    """check-scheme reports the tiers of each scheme, and the bundled hash is unchanged."""
    checks = []
    for path, tiers in ((SCHEME_1, "1 tier,"), (CLOSER, "2 tiers,"), (SCHEME_3, "3 tiers,")):
        r = ctx.cli("check-scheme", path)
        checks += [
            exit_is(r, 0),
            Check(
                f"{path.name}: {tiers[:-1]}", tiers in r.out, r.out.splitlines()[0] if r.out else ""
            ),
        ]
    r = ctx.cli("check-scheme", CLOSER)
    checks.append(Check("bundled scheme keeps its 004 hash", CLOSER_HASH in r.out))
    r = ctx.cli("check-scheme", SCHEME_3)
    checks += [
        Check("largest question at tier 3 is reported", "largest question, tier 3:" in r.out),
        Check("the file's [run] settings are shown", "run settings:" in r.out),
    ]
    return checks


def bad_inputs(ctx: Context) -> list[Check]:
    """A fourth tier, a bad [run] value and a misplaced --keep-at all exit 2."""
    deep = ctx.copy_scheme(
        SCHEME_3,
        "bad-4-tier.toml",
        (
            '    description = "Asthma, bronchitis, wheeze."\n',
            '    description = "Asthma, bronchitis, wheeze."\n\n'
            "      [[categories.categories.categories.categories]]\n"
            '      id = "asthma"\n      label = "Asthma"\n',
        ),
    )
    r = ctx.cli("check-scheme", deep)
    checks = [
        exit_is(r, 2),
        Check("a fourth tier is refused", "at most 3 tiers" in r.err, tail(r.err, 2)),
    ]
    bad_run = ctx.copy_scheme(SCHEME_3, "bad-run.toml", ("descend_at = 0.3", "descend_at = 1.5"))
    r = ctx.tag("bad-run", "--scheme", bad_run)
    checks += [
        exit_is(r, 2),
        Check("run.descend_at is named", "run.descend_at" in r.err, tail(r.err, 2)),
    ]
    r = ctx.tag("bad-keep", "--scheme", SCHEME_2, *ctx.model("chat"), "--keep-at", "0.2")
    checks += [exit_is(r, 2), Check("--keep-at with a chat model is refused", "--keep-at" in r.err)]
    return checks


def dry_run_decision(ctx: Context) -> list[Check]:
    """A decision dry run prints a body per tier, each with guidance and question."""
    r = ctx.tag("dry", "--scheme", SCHEME_3, *ctx.model("decision"), "--dry-run")
    heads = [line for line in r.out.splitlines() if line.startswith("--- ")]
    want = [
        "--- tier 1 ---",
        "--- tier 2 example (Health) ---",
        "--- tier 3 example (Physical health) ---",
    ]
    checks = [exit_is(r, 0), Check("one request per tier", heads == want, str(heads))]
    try:
        parts = re.split(r"^--- .* ---$", r.out, flags=re.M)[1:]
        asks = [json.loads(p)["questions"]["option"]["instructions"] for p in parts]
    except (json.JSONDecodeError, KeyError) as e:
        return [*checks, Check("request bodies are JSON", False, str(e))]
    checks += [
        Check("the guidance opens every question", all(a.startswith(GUIDANCE_START) for a in asks)),
        Check(
            "the tier-2 question fills in {group}",
            asks[1].endswith("Which topic within Health is this variable about?")
            if len(asks) > 1
            else False,
        ),
    ]
    r = ctx.tag(
        "dry", "--scheme", SCHEME_3, *ctx.model("decision"), "--method", "flat", "--dry-run"
    )
    try:
        n = len(json.loads(r.out)["questions"]["option"]["criteria"])
    except (json.JSONDecodeError, KeyError):
        n = -1
    checks.append(Check("flat: one request offering all 10 leaves", n == 10, f"{n} options"))
    return checks


def dry_run_chat(ctx: Context) -> list[Check]:
    """A chat dry run prints a prompt per tier, each with a Question: line."""
    r = ctx.tag("dry", "--scheme", SCHEME_3, *ctx.model("chat"), "--dry-run")
    questions = [line for line in r.out.splitlines() if line.startswith("Question: ")]
    return [
        exit_is(r, 0),
        Check("tiered from the file's [run]", "--- tier 3 example" in r.out),
        Check("a Question: line at every tier", len(questions) == 3, str(questions)),
        Check(
            "a file keep_at is ignored for a chat model, with a note",
            "keep_at in the scheme applies to decision models only; ignored." in r.err,
        ),
    ]


# --- With models: the twelve combinations -----------------------------------------------


def combination(
    tiers: int, scheme: Path, kind: str, method: str
) -> Callable[[Context], list[Check]]:
    """A step tagging ``scheme`` with a ``kind`` model by ``method``, and its checks."""

    def run(ctx: Context) -> list[Check]:
        folder = f"{tiers}-tier-{kind}-{method}"
        r = ctx.tag(folder, "--scheme", scheme, *ctx.model(kind), "--method", method)
        checks = [exit_is(r, 0, 1)]  # 1: finished, but some variables could not be tagged
        if r.code not in (0, 1):
            return checks
        expect = "flat" if tiers == 1 else method
        run_ = ctx.run_json(folder)
        recs = ctx.records(folder)
        leaves, groups = ctx.taxonomy(folder)
        counts = run_["counts"]
        paths = [r_.get("path") or [] for r_ in recs]
        checks += [
            Check(
                "variables tagged",
                counts["tagged"] > 0,
                f"{counts['tagged']} of {counts['todo']}, {counts['requests']} requests",
            ),
            Check(
                f"run.json: method {expect}, {tiers} tiers",
                (run_["settings"]["method"], run_["tiers"]) == (expect, tiers),
            ),
            Check(f"every record says method {expect}", all(x["method"] == expect for x in recs)),
            Check(
                "every tag is a leaf of the taxonomy",
                all(t in leaves for x in recs for t, _ in x["topics"]),
            ),
            Check(
                "requests counted per tier",
                1 <= len(counts["requests_by_tier"]) <= tiers,
                str(counts["requests_by_tier"]),
            ),
            Check("the summary names method, model and tiers", f"Method: {expect} with " in r.out),
        ]
        if tiers == 1 and method == "tiered":
            checks.append(
                Check("says it tags flat", "This taxonomy has one tier: tagging flat." in r.err)
            )
        if expect == "flat":
            checks.append(Check("flat records have no path", not any(paths)))
        else:
            deepest = max(map(len, paths), default=0)
            checks += [
                Check("paths hold only groups", all(g in groups for p in paths for g, _ in p)),
                Check(
                    "some variables were routed through groups",
                    deepest > 0,
                    f"deepest path {deepest}",
                ),
            ]
        if kind == "decision" and expect == "flat":
            checks.append(
                Check(
                    "one question per variable",
                    counts["requests"] >= counts["tagged"] and len(counts["requests_by_tier"]) == 1,
                )
            )
        return checks

    return run


# --- With models: refusals --------------------------------------------------------------


def refusal_flat(ctx: Context) -> list[Check]:
    """Every topic of the bundled scheme, flat, is too many options for Clef: exit 5."""
    r = ctx.tag("refusal-flat", "--scheme", CLOSER, *ctx.model("decision"), "--method", "flat")
    checks = [exit_is(r, 5)]
    if r.code != 5:
        checks.append(
            Check(
                "the model refused 107 options (if not, its refusal text may not match)",
                False,
                tail(r.err + r.out),
            )
        )
        return checks
    run_ = ctx.run_json("refusal-flat")
    return [
        *checks,
        Check(
            "names the question and its size",
            "refused a question with 107 options (every topic, asked flat)" in r.err,
            tail(r.err, 4),
        ),
        Check("suggests tagging tiered", "--method tiered" in r.err),
        Check("run.json has stop_reason", "stop_reason" in run_),
        Check(
            "no variable marked failed, nothing retried",
            (run_["counts"]["failed"], run_["counts"]["retries"]) == (0, 0),
        ),
    ]


def big_group_scheme(ctx: Context) -> Path:
    """A two-tier scheme with one group of 30 topics, too many for a model such as Clef."""
    topics = "".join(
        f'\n  [[domains.topics]]\n  id = "b{i}"\n  label = "Topic {i}"\n'
        f'  description = "Fictional topic {i}."\n'
        for i in range(30)
    )
    path = ctx.out / "big-group.toml"
    path.write_text(
        'name = "Big group"\nversion = 1\nfallback_topic = "other"\n'
        'guidance = "Tag each variable."\n\n'
        '[[domains]]\nid = "big"\nlabel = "Big topics"\ndescription = "Thirty fictional topics."\n'
        + topics
        + '\n[[domains]]\nid = "misc"\nlabel = "Misc"\ndescription = "Anything else."\n'
        '\n  [[domains.topics]]\n  id = "other"\n  label = "Other"\n'
        '  description = "Nothing fits."\n',
        encoding="utf-8",
    )
    return path


def refusal_group(ctx: Context) -> list[Check]:
    """A group of 30 topics is too many options for Clef at tier 2: exit 5."""
    # Following every group (descend at 0, no cap) sends every variable into "big".
    scheme = big_group_scheme(ctx)
    opts = ("--method", "tiered", "--descend-at", "0", "--max-follow", "0")
    r = ctx.tag("refusal-group", "--scheme", scheme, *ctx.model("decision"), *opts)
    checks = [exit_is(r, 5)]
    if r.code == 5:
        checks += [
            Check("names the group", 'group big, "Big topics"' in r.err, tail(r.err, 4)),
            Check("suggests splitting it", "Split big into smaller groups" in r.err),
        ]
    return checks


# --- With models: the scheme file controls the run --------------------------------------


def file_controls_the_run(ctx: Context) -> list[Check]:
    """The scheme's [run] alone drives a run; [run] edits keep tags, others redo them."""
    model_line = 'model      = "clef:cloud"'
    scheme = ctx.copy_scheme(
        SCHEME_3, "file-run.toml", (model_line, f'model      = "{ctx.args.decision_model}"')
    )
    folder = "file-run"
    checks = []

    r = ctx.tag(folder, "--scheme", scheme)  # no provider, model or method on the command line
    checks.append(exit_is(r, 0, 1))
    if r.code not in (0, 1):
        return checks
    run_ = ctx.run_json(folder)
    tagged = run_["counts"]["tagged"]
    sources = run_["settings_source"]
    checks += [
        Check("every setting came from the file", set(sources.values()) == {"file"}, str(sources)),
        Check(
            "summary line",
            f"Method: tiered with ollama-decision:{ctx.args.decision_model}, 3 tiers" in r.out,
        ),
    ]

    r = ctx.tag(folder, "--scheme", scheme)
    checks.append(
        Check("run again: nothing left to do", to_do(r) == (tagged, ctx.n - tagged), str(to_do(r)))
    )

    ctx.copy_scheme(scheme, "file-run.toml", ("descend_at = 0.3", "descend_at = 0.4"))
    r = ctx.tag(folder, "--scheme", scheme)
    checks.append(
        Check("editing [run] keeps the tags", to_do(r) == (tagged, ctx.n - tagged), str(to_do(r)))
    )

    ctx.copy_scheme(
        scheme, "file-run.toml", ("Which topic within {group}", "Which subject within {group}")
    )
    r = ctx.tag(folder, "--scheme", scheme)
    checks += [
        exit_is(r, 0, 1),
        Check("editing a question redoes every tag", to_do(r) == (0, ctx.n), str(to_do(r))),
    ]

    r = ctx.tag(folder, "--scheme", scheme, "--method", "flat")
    checks.append(Check("another method redoes every tag", to_do(r) == (0, ctx.n), str(to_do(r))))
    if r.code in (0, 1):
        run_ = ctx.run_json(folder)
        checks.append(
            Check(
                "the command line overrides the file",
                (
                    run_["settings"]["method"],
                    run_["settings_source"]["method"],
                    run_["settings_source"]["model"],
                )
                == ("flat", "cli", "file"),
                str(run_["settings_source"]),
            )
        )
    return checks


def stop_and_carry_on(ctx: Context) -> list[Check]:
    """A run that stops part way is carried on by the same command."""
    # --limit stops after part of the work, as Ctrl-C would; the same command carries on.
    folder = "carry-on"
    half = max(1, ctx.n // 2)
    base = ("--scheme", SCHEME_2, *ctx.model("decision"))
    r = ctx.tag(folder, *base, "--limit", half)
    checks = [
        exit_is(r, 0, 1),
        Check(f"first run did {half}", to_do(r) == (0, half), str(to_do(r))),
    ]
    first = len(ctx.records(folder))
    r = ctx.tag(folder, *base)
    checks += [
        exit_is(r, 0, 1),
        Check("second run does only the rest", to_do(r) == (first, ctx.n - first), str(to_do(r))),
        Check(
            "every variable has a record",
            len(ctx.records(folder)) == ctx.n,
            f"{len(ctx.records(folder))} of {ctx.n}",
        ),
    ]
    return checks


def steps() -> list[Step]:
    """Every step, in the order they run."""
    out = [
        Step("check-scheme: one, two and three tiers", False, check_schemes),
        Step("bad schemes and options are refused", False, bad_inputs),
        Step(
            "dry run, decision model: every tier, guidance and questions", False, dry_run_decision
        ),
        Step("dry run, chat model: every tier and Question: lines", False, dry_run_chat),
    ]
    for tiers, scheme in ((1, SCHEME_1), (2, SCHEME_2), (3, SCHEME_3)):
        for kind in ("chat", "decision"):
            for method in ("flat", "tiered"):
                out.append(
                    Step(
                        f"{tiers} tier{'s' if tiers > 1 else ''}, {kind} model, {method}",
                        True,
                        combination(tiers, scheme, kind, method),
                    )
                )
    out += [
        Step("refusal: every topic flat to a decision model", True, refusal_flat),
        Step("refusal: a group too big for a decision model", True, refusal_group),
        Step("the scheme file controls the run; hash and resume", True, file_controls_the_run),
        Step("stop part way and carry on", True, stop_and_carry_on),
    ]
    return out


def main(argv: list[str] | None = None) -> int:
    """Run the steps, print each result, and return 0 only if every check held."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--chat-model", default="gpt-oss:20b-cloud", help="chat model (ollama)")
    parser.add_argument("--decision-model", default="clef:cloud", help="decision model")
    parser.add_argument("--base-url", help="the host's API, if not the local Ollama")
    parser.add_argument(
        "--variables", type=int, default=6, help="how many fixture variables to tag"
    )
    parser.add_argument(
        "--out", type=Path, help="where the runs go (default: a new temporary folder)"
    )
    parser.add_argument("--offline", action="store_true", help="only the steps that need no model")
    parser.add_argument("--only", help="only steps whose name contains this text")
    parser.add_argument("--timeout", type=float, default=900, help="seconds allowed per command")
    parser.add_argument("--yes", action="store_true", help="allow sending metadata to the models")
    args = parser.parse_args(argv)

    chosen = [s for s in steps() if not (args.offline and s.needs_model)]
    if args.only:
        chosen = [s for s in chosen if args.only.lower() in s.name.lower()]
    if any(s.needs_model for s in chosen) and not args.yes:
        print(
            "Model steps send the fixture variables' metadata (fictional) to "
            f"{args.chat_model} and {args.decision_model}. Pass --yes to allow, or --offline.",
            file=sys.stderr,
        )
        return 2
    out = args.out or Path(tempfile.mkdtemp(prefix="topic-tagger-demo-"))
    out.mkdir(parents=True, exist_ok=True)
    ctx = Context(args, out)
    print(f"{len(chosen)} steps, {ctx.n} variables each; runs in {out}\n")

    for step in chosen:
        print(f"▶ {step.name}", flush=True)
        started = time.monotonic()
        try:
            step.checks = step.run(ctx)
        except Exception as e:  # a demo reports a crash and goes on to the next step
            step.checks = [Check("ran without crashing", False, f"{type(e).__name__}: {e}")]
        step.seconds = time.monotonic() - started
        for c in step.checks:
            mark = "  ✓" if c.ok else "  ✗"
            print(f"{mark} {c.what}" + (f"  [{c.detail}]" if c.detail else ""))
        print(f"  {'PASS' if all(c.ok for c in step.checks) else 'FAIL'} in {step.seconds:.0f}s\n")

    failed = [s for s in chosen if not all(c.ok for c in s.checks)]
    summary = [
        {
            "step": s.name,
            "passed": all(c.ok for c in s.checks),
            "seconds": round(s.seconds, 1),
            "checks": [vars(c) for c in s.checks],
        }
        for s in chosen
    ]
    (out / "demo-summary.json").write_text(json.dumps(summary, indent=1) + "\n", encoding="utf-8")
    passed = len(chosen) - len(failed)
    print(f"{passed} of {len(chosen)} steps passed. Summary: {out / 'demo-summary.json'}")
    for s in failed:
        print(f"  FAILED: {s.name}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
