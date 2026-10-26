"""Supplied data is in place: every cohort listed in datasets.json has its folder.

The full format checks (rules D1-D8 in contracts/site-data.md) arrive with User Story 5.
"""

import json
from pathlib import Path

DATA = Path(__file__).resolve().parents[3] / "site" / "data"


def test_every_listed_cohort_has_manifest_and_index():
    catalogue = json.loads((DATA / "datasets.json").read_text(encoding="utf-8"))
    keys = [d["key"] for d in catalogue["datasets"]]
    assert keys
    for key in keys:
        assert (DATA / key / "manifest.json").is_file(), key
        assert (DATA / key / "index.json").is_file(), key
