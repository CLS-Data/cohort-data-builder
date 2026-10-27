"""The CI gate for supplied data (FR-030): site/data must pass every format check.

Run on its own with `uv run pytest tests/python/data`. A failure lists every problem, one
per line, as `<path>[: <location>]: <message>`.
"""

from pathlib import Path

from checks import check_data

DATA = Path(__file__).resolve().parents[3] / "site" / "data"


def test_supplied_data_matches_the_documented_format():
    problems = check_data(DATA)
    if problems:
        lines = "\n".join(map(str, problems))
        raise AssertionError(f"{len(problems)} problem(s) in site/data:\n{lines}")
