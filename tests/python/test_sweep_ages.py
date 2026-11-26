"""Sweep ages in the manifest: the D3 checks of feature 007 (contracts/sweep-ages.md).

Kept outside tests/python/data/ so it can be read and edited where that folder cannot.
Every manifest here is a copy of the fictional fixture with one thing changed.
"""

import json
import shutil
from pathlib import Path

import pytest
from checks import check_data, sweep_age_warnings

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "data"


@pytest.fixture
def data(tmp_path):
    """A copy of the fixture data, with a function to change mini's sweep list."""
    root = tmp_path / "data"
    shutil.copytree(FIXTURES, root)

    def set_waves(edit):
        path = root / "mini" / "manifest.json"
        m = json.loads(path.read_text())
        edit(m["wave"]["list"])
        path.write_text(json.dumps(m))
        return root

    return set_waves


def messages(root):
    """The problems check_data finds, as strings."""
    return [str(p) for p in check_data(root)]


def test_the_fixture_with_its_ages_is_valid():
    assert check_data(FIXTURES) == []


@pytest.mark.parametrize("age", [-1, 121, "5", True])
def test_an_age_outside_0_to_120_or_not_a_number_is_a_problem(data, age):
    def edit(waves):
        waves[0]["age"] = age

    found = messages(data(edit))
    assert any("wave.list[0]" in m and "age" in m for m in found), found


def test_age_range_must_be_ordered_and_contain_the_age(data):
    def backwards(waves):
        waves[0]["ageRange"] = [8, 6]

    assert any("ageRange" in m and "min" in m for m in messages(data(backwards)))

    def outside(waves):
        waves[0]["age"] = 5
        waves[0]["ageRange"] = [1, 2]

    assert any("ageRange" in m and "contain" in m for m in messages(data(outside)))


def test_age_range_must_be_two_numbers(data):
    def edit(waves):
        waves[0]["ageRange"] = [1, 2, 3]

    assert any("ageRange" in m for m in messages(data(edit)))


def test_ages_need_not_follow_list_order(data):
    # The real lists are in sweep-number order: sub-sweeps share an age, and one can be
    # older than the sweep after it (ncds s9_1, 63, before s10, 61). The site sorts by age.
    def edit(waves):
        waves[0]["age"] = 10
        waves[1]["age"] = 5
        waves[2]["age"] = 5

    assert messages(data(edit)) == []


def test_a_sweep_with_no_known_age_is_a_warning_not_a_problem():
    assert check_data(FIXTURES) == []
    found = [str(w) for w in sweep_age_warnings(FIXTURES)]
    assert any(m.startswith("mini/manifest.json") and "xwave" in m for m in found), found
    assert any(m.startswith("mini2/manifest.json") and "extra" in m for m in found), found
    # w2 has an explicit age, 3y and 11y are age-shaped: none of them is warned about.
    assert not any("'w2'" in m or "'3y'" in m or "'11y'" in m for m in found), found
