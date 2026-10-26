"""The repository layout from plan.md exists, so CI has something to run from day one."""

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize(
    "folder",
    [
        "site/js/core",
        "site/js/ui",
        "site/templates",
        "site/data",
        "tests/js",
        "tests/fixtures",
        "tests/python/data",
        "tests/python/generated",
        "tests/python/e2e",
        "docs",
    ],
)
def test_folder_exists(folder):
    assert (ROOT / folder).is_dir()
