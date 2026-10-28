"""Stage 2: run the Topic Tagger on each staged cohort, restarting it when it crashes.

    uv run python adhoc/tag.py [ncds bcs70 next_steps mcs] [--model gpt-oss:120b-cloud]

A long run can be ended by one bad reply from the model host (e.g. an empty body, which
the tagger stops on with a JSON decoding error). The tagger saves its tags a batch at a
time and carries on where it stopped, so this script runs it again after a short wait,
until the cohort is finished or several runs in a row tag nothing new. Ctrl-C, bad input
(exit 2) and a locked output folder (exit 4) stop it at once. Standard library only.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from collections.abc import Callable
from pathlib import Path

HERE = Path(__file__).resolve().parent
TAGGER = HERE.parent / "tools" / "topic-tagger"
STOP = {2, 4, 130}  # bad input, locked folder, Ctrl-C: running again will not help


def tag_cohort(
    run: Callable[[], int],
    tagged: Callable[[], int],
    *,
    tries: int,
    wait: float,
    sleep: Callable[[float], None] = time.sleep,
) -> int:
    """Run the tagger until it finishes, restarting it after a crash.

    Args:
        run: Runs the tagger once and returns its exit code.
        tagged: How many variables are tagged so far.
        tries: Runs in a row without a new tag before giving up.
        wait: Seconds to wait before running again.
        sleep: Waits; replaced in tests.

    Returns:
        0 when the tagger finished, otherwise the last exit code.
    """
    idle = 0
    before = tagged()
    while True:
        code = run()
        if code == 0 or code in STOP:
            return code
        after = tagged()
        idle = 0 if after > before else idle + 1
        before = after
        if idle >= tries:
            return code
        print(f"Tagger stopped (exit {code}) with {after:,} tagged; again in {wait:g} s")
        sleep(wait)


def count_tagged(path: Path) -> int:
    """The number of different variables in a ``tags.jsonl``."""
    if not path.exists():
        return 0
    keys = set()
    with path.open(encoding="utf-8") as f:
        for line in f:
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue  # a line cut short by a crash
            keys.add(f"{rec['file']}/{rec['variable']}".lower())
    return len(keys)


def main() -> int:
    """Run stage 2 from the command line."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("keys", nargs="*", help="cohorts to tag (default: all)")
    parser.add_argument("--staging", type=Path, default=HERE / "data/staging")
    parser.add_argument("--scheme", type=Path, default=HERE / "scheme.toml")
    parser.add_argument("--model", default="gpt-oss:120b-cloud")
    parser.add_argument("--tries", type=int, default=5, help="runs without progress")
    parser.add_argument("--wait", type=float, default=30, help="seconds between runs")
    args, extra = parser.parse_known_args()

    cohorts = json.loads((HERE / "cohorts.json").read_text())
    for key in args.keys or [v["key"] for k, v in cohorts.items() if k[0] != "_"]:
        folder = args.staging.resolve() / key
        out = folder / "tags"
        command = [
            *("uv", "run", "topic-tagger", "tag", str(folder / "tagger/variables.jsonl")),
            *("--out", str(out), "--scheme", str(args.scheme.resolve())),
            *("--model", args.model, "--yes", *extra),
        ]
        print(f"== {key}")
        code = tag_cohort(
            lambda command=command: subprocess.run(command, cwd=TAGGER).returncode,
            lambda out=out: count_tagged(out / "tags.jsonl"),
            tries=args.tries,
            wait=args.wait,
        )
        if code:
            print(f"{key}: stopped with exit {code}; run this again to carry on")
            return code
    return 0


if __name__ == "__main__":
    sys.exit(main())
