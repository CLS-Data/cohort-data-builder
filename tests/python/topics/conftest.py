"""Fixtures for the topics processing script: the mini cohort with its topics removed."""

import shutil
from pathlib import Path

import pytest
from topics_data import FIXTURE, strip_topics


@pytest.fixture
def data_dir(tmp_path) -> Path:
    """A copy of the fixture data folder whose mini cohort has no topics."""
    out = tmp_path / "data"
    shutil.copytree(FIXTURE, out)
    strip_topics(out / "mini")
    return out


@pytest.fixture
def cohort(data_dir) -> Path:
    return data_dir / "mini"
