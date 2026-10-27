"""The supplied-data checks (rules D1-D8 in contracts/site-data.md) on broken fixtures.

Each broken case is the valid fixture cohort with exactly one violation, made by a small
function below rather than kept as a folder of copies: the break is then the only thing to
read, and the copies cannot drift from the valid fixture.
"""

import json
import shutil
from pathlib import Path

import pytest
from checks import Problem, check_data

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / "tests" / "fixtures" / "data"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def save(path, value):
    path.write_text(json.dumps(value), encoding="utf-8")


def edit(rel, change):
    """Return a break that loads one JSON file, changes it with `change`, and saves it."""

    def apply(data):
        path = data / rel
        value = load(path)
        change(value)
        save(path, value)

    return apply


def variable(value, name):
    return next(v for v in value["variables"] if v["variable"] == name)


def truncate(data):
    path = data / "mini" / "manifest.json"
    path.write_text(path.read_text(encoding="utf-8")[:200], encoding="utf-8")


BROKEN = {
    "d1_bad_json": (truncate, "mini/manifest.json"),
    "d1_missing_field": (
        edit("mini/manifest.json", lambda m: m.pop("identifier")),
        "mini/manifest.json",
    ),
    "d2_count_mismatch": (
        edit("datasets.json", lambda d: d["datasets"][0].update(variables=17)),
        "datasets.json",
    ),
    "d2_bad_key": (
        edit("datasets.json", lambda d: d["datasets"][0].update(key="Mini")),
        "datasets.json",
    ),
    "d3_unknown_wave": (
        edit("mini/manifest.json", lambda m: m["files"][3].update(wave="99y")),
        "mini/manifest.json",
    ),
    "d3_duplicate_file": (
        edit("mini/manifest.json", lambda m: m["files"].append(dict(m["files"][0]))),
        "mini/manifest.json",
    ),
    "d4_index_out_of_range": (
        edit("mini/index.json", lambda rows: rows[1].__setitem__(2, 9)),
        "mini/index.json",
    ),
    "d4_odd_topics": (
        edit("mini/index.json", lambda rows: rows[2].__setitem__(5, [0, 95, 1])),
        "mini/index.json",
    ),
    "d5_missing_dict": (
        lambda data: (data / "mini" / "dict" / "mini_grid.json").unlink(),
        "mini/dict/mini_grid.json",
    ),
    "d5_unknown_variable": (
        edit("mini/index.json", lambda rows: rows[1].__setitem__(0, "ghost")),
        "mini/index.json",
    ),
    "d5_duplicate_variable": (
        edit(
            "mini/dict/mini_age10.json",
            lambda d: d["variables"].append({"variable": "SEX", "label": "Sex again"}),
        ),
        "mini/dict/mini_age10.json",
    ),
    "d6_bad_values": (
        edit(
            "mini/dict/mini_age5.json",
            lambda d: variable(d, "sex")["values"][0].pop("label"),
        ),
        "mini/dict/mini_age5.json",
    ),
    "d6_bad_range": (
        edit(
            "mini/dict/mini_age5.json",
            lambda d: variable(d, "tenure5")["na"].update(ranges=[[5, 1]]),
        ),
        "mini/dict/mini_age5.json",
    ),
    "d7_unknown_topic": (
        edit(
            "mini/dict/mini_age5.json",
            lambda d: variable(d, "smoke5").update(topics=[["vaping", 0.9]]),
        ),
        "mini/dict/mini_age5.json",
    ),
    "d7_confidence": (
        edit(
            "mini/dict/mini_age5.json",
            lambda d: variable(d, "smoke5").update(topics=[["smoking", 1.5]]),
        ),
        "mini/dict/mini_age5.json",
    ),
    "d8_hasid_wrong": (
        edit("mini/manifest.json", lambda m: m["files"][3].update(hasId=True)),
        "mini/manifest.json",
    ),
}


@pytest.fixture
def data(tmp_path):
    copy = tmp_path / "data"
    shutil.copytree(FIXTURE, copy)
    return copy


def test_the_valid_fixture_has_no_problems():
    assert check_data(FIXTURE) == []


def test_the_supplied_site_data_has_no_problems():
    problems = check_data(ROOT / "site" / "data")
    assert problems == [], "\n".join(map(str, problems))


@pytest.mark.parametrize("case", sorted(BROKEN))
def test_each_broken_case_is_reported_against_its_file_only(case, data):
    breaks, path = BROKEN[case]
    breaks(data)
    problems = check_data(data)
    assert problems, f"{case} was not reported"
    assert {p.path for p in problems} == {path}, "\n".join(map(str, problems))


def test_messages_name_what_is_wrong(data):
    BROKEN["d2_count_mismatch"][0](data)
    BROKEN["d6_bad_range"][0](data)
    text = "\n".join(map(str, check_data(data)))
    assert "datasets.json: datasets[0] (mini): 'variables' is 17" in text
    assert "mini/dict/mini_age5.json: variable tenure5: na.ranges[0] [5, 1]" in text


def test_every_problem_is_reported_in_one_run(data):
    for case in ("d2_count_mismatch", "d4_odd_topics", "d7_confidence", "d8_hasid_wrong"):
        BROKEN[case][0](data)
    paths = {p.path for p in check_data(data)}
    assert paths == {
        "datasets.json",
        "mini/index.json",
        "mini/dict/mini_age5.json",
        "mini/manifest.json",
    }


def test_problem_reads_as_path_location_message():
    assert str(Problem("mini/index.json", "row 3", "bad")) == "mini/index.json: row 3: bad"
    assert str(Problem("datasets.json", "", "bad")) == "datasets.json: bad"


def test_a_cohort_without_topics_is_valid_when_its_dictionaries_have_none(data):
    edit("mini/manifest.json", lambda m: m.pop("topics"))(data)
    for row in (rows := load(data / "mini" / "index.json")):
        del row[5:]
    save(data / "mini" / "index.json", rows)
    for path in (data / "mini" / "dict").glob("*.json"):
        d = load(path)
        for v in d["variables"]:
            v.pop("topics", None)
        save(path, d)
    assert check_data(data) == []
