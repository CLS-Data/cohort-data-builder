"""Give each sweep its age, read from the sweep's label (feature 007, task T002a).

The site lines several cohorts' sweeps up by age, from `age` (and `ageRange`) in each
`manifest.wave.list[]` entry (specs/007-multi-cohort-search/contracts/sweep-ages.md). The
CLS metadata gives each sweep a `sweep-year-age` text, which the build put into the sweep
labels, e.g. "Sweep 6.1: age 44/45, 2002/04". This reads the age back out:

    uv run python scripts/sweep_ages.py site/data/bcs70 site/data/ncds            # dry run
    uv run python scripts/sweep_ages.py site/data/bcs70 site/data/ncds --write

Only a number after "age" or before "years old"/"months old" is an age, so years such as
2002/04 are never taken for one. A sweep that already has `age` is left as it is. Standard
library only. Exit codes: 0 done, 1 written but the data checks found problems, 2 bad input.
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import re
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from checks import MAX_AGE, check_data

OK, CHECKS_FAILED, BAD_INPUT = 0, 1, 2

_NUM = r"\d+(?:\.\d+)?"
_SPAN = rf"({_NUM})(?:\s*(?:/|-|–|to)\s*({_NUM}))?"
_UNIT = r"(months?|mths?|years?|yrs?)"
# "age 44/45", "age 9 months", "age birth"
_AGE_RE = re.compile(rf"\bages?\s+(?:(birth)\b|{_SPAN}(?:\s*{_UNIT}\b)?)", re.IGNORECASE)
# "44/45 years old", "9 months old"
_OLD_RE = re.compile(rf"\b{_SPAN}\s*{_UNIT}\s+old\b", re.IGNORECASE)
_BIRTH_RE = re.compile(r"\bbirth\b", re.IGNORECASE)


class SweepAgesError(Exception):
    """A cohort folder cannot be used; nothing has been written."""


def _number(x: float) -> int | float:
    """A whole number as an int, so it is written as `16`, not `16.0`."""
    return int(x) if float(x).is_integer() else x


def age_from_label(label: str) -> tuple[int | float | None, list | None]:
    """Read a sweep's age from its label.

    Args:
        label: The sweep's label, e.g. "Sweep 6.1: age 44/45, 2002/04".

    Returns:
        `(age, ageRange)`: the age in years (months as a fraction; birth is 0) and, when the
        label gives a span such as 44/45, `[min, max]` with `age` the min; otherwise None.
        `(None, None)` when the label gives no age, or one that is backwards or beyond
        the data checks' 0 to 120.
    """
    text = str(label or "")
    match = _AGE_RE.search(text)
    if match and match.group(1):
        return 0, None
    if match:
        low, high, unit = match.group(2), match.group(3), match.group(4)
    else:
        match = _OLD_RE.search(text)
        if not match:
            return (0, None) if _BIRTH_RE.search(text) else (None, None)
        low, high, unit = match.groups()
    scale = 12 if unit and unit.lower().startswith("m") else 1
    lo = float(low) / scale
    hi = float(high) / scale if high else lo
    if hi < lo or hi > MAX_AGE:
        return None, None
    span = [_number(lo), _number(hi)] if hi != lo else None
    return _number(lo), span


@dataclass
class Outcome:
    """What `fill_ages` did, sweep keys in list order."""

    set: list[str] = field(default_factory=list)  # given an age from the label
    kept: list[str] = field(default_factory=list)  # already had one
    unknown: list[str] = field(default_factory=list)  # no age in the label
    ages: dict[str, tuple] = field(default_factory=dict)  # key -> (age, ageRange) set


def fill_ages(manifest: dict) -> Outcome:
    """Give every sweep without an `age` the age its label states, in place.

    Args:
        manifest: A cohort's manifest; its `wave.list` entries are changed.

    Returns:
        Which sweeps were given an age, which kept theirs, and which have none.
    """
    out = Outcome()
    for wave in manifest["wave"]["list"]:
        key = wave.get("key")
        if wave.get("age") is not None:
            out.kept.append(key)
            continue
        age, span = age_from_label(wave.get("label", ""))
        if age is None:
            out.unknown.append(key)
            continue
        wave["age"] = age
        if span:
            wave["ageRange"] = span
        out.set.append(key)
        out.ages[key] = (age, span)
    return out


def _read(folder: Path) -> dict:
    path = folder / "manifest.json"
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except OSError as e:
        raise SweepAgesError(f"cannot read {path}: {e.strerror}") from e
    except json.JSONDecodeError as e:
        raise SweepAgesError(f"{path} is not valid JSON: {e}") from e
    if not isinstance(manifest.get("wave", {}).get("list"), list):
        raise SweepAgesError(f"{path} has no wave.list")
    return manifest


def _write(path: Path, data) -> None:
    """Write JSON as the site's files are (compact, UTF-8), replacing the file at once."""
    text = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(tmp, path)


def _say(name: str, out: Outcome) -> None:
    def age_text(age, span):
        return f"{age} ({span[0]}–{span[1]})" if span else f"{age}"

    print(f"{name}:")
    for key in out.set:
        print(f"  {key}: age {age_text(*out.ages[key])}")
    if out.kept:
        print(f"  already had an age, kept: {', '.join(out.kept)}")
    if out.unknown:
        print(f"  no age in the label, left without one: {', '.join(out.unknown)}")


def main(argv: list[str] | None = None) -> int:
    """Run the command line.

    Args:
        argv: Arguments without the program name; defaults to ``sys.argv[1:]``.

    Returns:
        The exit code: 0 done, 1 written but the data checks found problems, 2 bad input.
    """
    parser = argparse.ArgumentParser(prog="sweep_ages.py", description=__doc__.split("\n")[0])
    parser.add_argument(
        "cohorts", type=Path, nargs="+", help="cohort folders, e.g. site/data/bcs70"
    )
    parser.add_argument("--write", action="store_true", help="write the ages (default: dry run)")
    args = parser.parse_args(argv)

    try:
        manifests = [(folder, _read(folder)) for folder in args.cohorts]
    except SweepAgesError as e:
        print(f"sweep_ages.py: {e}", file=sys.stderr)
        return BAD_INPUT

    for folder, manifest in manifests:
        target = manifest if args.write else copy.deepcopy(manifest)
        _say(folder.name, fill_ages(target))
    if not args.write:
        print("Dry run: nothing written. Add --write to write these ages.")
        return OK

    for folder, manifest in manifests:
        _write(folder / "manifest.json", manifest)
    problems = []
    for data_dir in dict.fromkeys(folder.resolve().parent for folder, _ in manifests):
        problems += [str(p) for p in check_data(data_dir)]
    if problems:
        print("Wrote the ages, but the data checks found problems:")
        for p in problems:
            print(f"  {p}")
        return CHECKS_FAILED
    print("Wrote the ages; the data checks pass.")
    return OK


if __name__ == "__main__":
    sys.exit(main())
