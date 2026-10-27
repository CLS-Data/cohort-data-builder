"""Helpers for the topics script tests: the fixture data, and reading and writing it."""

import json
from pathlib import Path

FIXTURE = Path(__file__).parents[2] / "fixtures" / "data"


def read(path: Path):
    """Parse a JSON file."""
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, data) -> None:
    """Write JSON compactly, as the site's data files are."""
    path.write_text(json.dumps(data, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")


def strip_topics(cohort: Path) -> None:
    """Remove every topic field, as data arriving from a provider would be."""
    manifest = read(cohort / "manifest.json")
    manifest.pop("topics", None)
    write(cohort / "manifest.json", manifest)
    write(cohort / "index.json", [row[:5] for row in read(cohort / "index.json")])
    for path in (cohort / "dict").glob("*.json"):
        d = read(path)
        for v in d["variables"]:
            v.pop("topics", None)
        write(path, d)
