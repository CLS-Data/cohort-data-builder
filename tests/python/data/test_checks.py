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
    "d1_bad_json": (
        truncate,
        "mini/manifest.json",
        "not valid JSON",
    ),
    "d1_missing_field": (
        edit("mini/manifest.json", lambda m: m.pop("identifier")),
        "mini/manifest.json",
        "missing required field 'identifier'",
    ),
    "d2_count_mismatch": (
        edit("datasets.json", lambda d: d["datasets"][0].update(variables=17)),
        "datasets.json",
        "'variables' is 17",
    ),
    "d2_bad_key": (
        edit("datasets.json", lambda d: d["datasets"][0].update(key="Mini")),
        "datasets.json",
        "key should be lower-case",
    ),
    "d3_unknown_wave": (
        edit("mini/manifest.json", lambda m: m["files"][3].update(wave="99y")),
        "mini/manifest.json",
        "sweep '99y' is not declared",
    ),
    "d3_duplicate_file": (
        edit("mini/manifest.json", lambda m: m["files"].append(dict(m["files"][0]))),
        "mini/manifest.json",
        "is listed twice",
    ),
    "d4_index_out_of_range": (
        edit("mini/index.json", lambda rows: rows[1].__setitem__(2, 9)),
        "mini/index.json",
        "file index 9 is out of range",
    ),
    "d4_odd_topics": (
        edit("mini/index.json", lambda rows: rows[2].__setitem__(5, [0, 95, 1])),
        "mini/index.json",
        "(odd length)",
    ),
    "d5_missing_dict": (
        lambda data: (data / "mini" / "dict" / "mini_grid.json").unlink(),
        "mini/dict/mini_grid.json",
        "file is missing",
    ),
    "d5_unknown_variable": (
        edit("mini/index.json", lambda rows: rows[1].__setitem__(0, "ghost")),
        "mini/index.json",
        "not in the dictionary of",
    ),
    "d5_duplicate_variable": (
        edit(
            "mini/dict/mini_age10.json",
            lambda d: d["variables"].append({"variable": "SEX", "label": "Sex again"}),
        ),
        "mini/dict/mini_age10.json",
        "same name as",
    ),
    "d6_bad_values": (
        edit(
            "mini/dict/mini_age5.json",
            lambda d: variable(d, "sex")["values"][0].pop("label"),
        ),
        "mini/dict/mini_age5.json",
        "should have 'value' and 'label'",
    ),
    "d6_bad_range": (
        edit(
            "mini/dict/mini_age5.json",
            lambda d: variable(d, "tenure5")["na"].update(ranges=[[5, 1]]),
        ),
        "mini/dict/mini_age5.json",
        "has low above high",
    ),
    "d7_unknown_topic": (
        edit(
            "mini/dict/mini_age5.json",
            lambda d: variable(d, "smoke5").update(topics=[["vaping", 0.9]]),
        ),
        "mini/dict/mini_age5.json",
        "topic 'vaping' is not in",
    ),
    "d7_confidence": (
        edit(
            "mini/dict/mini_age5.json",
            lambda d: variable(d, "smoke5").update(topics=[["smoking", 1.5]]),
        ),
        "mini/dict/mini_age5.json",
        "should be between 0 and 1",
    ),
    "d8_hasid_wrong": (
        edit("mini/manifest.json", lambda m: m["files"][3].update(hasId=True)),
        "mini/manifest.json",
        "hasId is true",
    ),
}


@pytest.fixture
def data(tmp_path):
    copy = tmp_path / "data"
    shutil.copytree(FIXTURE, copy)
    return copy


def test_the_valid_fixture_has_no_problems():
    assert check_data(FIXTURE) == []


@pytest.mark.parametrize("case", sorted(BROKEN))
def test_each_broken_case_is_reported_against_its_file_and_says_why(case, data):
    breaks, path, says = BROKEN[case]
    breaks(data)
    problems = check_data(data)
    text = "\n".join(map(str, problems))
    assert problems, f"{case} was not reported"
    assert {p.path for p in problems} == {path}, text
    assert says in text, text


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


def test_a_folder_without_a_catalogue_says_so(tmp_path):
    assert [str(p) for p in check_data(tmp_path)] == ["datasets.json: file is missing"]


def test_an_empty_catalogue_is_valid(tmp_path):
    save(tmp_path / "datasets.json", {"built": "2026-01-01", "datasets": []})
    assert check_data(tmp_path) == []


def test_a_catalogue_entry_without_its_folder_is_reported(data):
    shutil.rmtree(data / "mini")
    text = "\n".join(map(str, check_data(data)))
    assert "datasets.json: datasets[0] (mini): no mini/manifest.json or mini/index.json" in text


def test_an_empty_index_disagrees_with_the_manifest_count(data):
    save(data / "mini" / "index.json", [])
    text = "\n".join(map(str, check_data(data)))
    assert "mini/manifest.json: counts.variables: is" in text
    assert "index.json has 0 rows" in text


def test_a_short_index_row_is_reported(data):
    rows = load(data / "mini" / "index.json")
    rows[1] = ["short", "row"]
    save(data / "mini" / "index.json", rows)
    assert "mini/index.json: row 1: should be [name, label, file, sweep, level]" in "\n".join(
        map(str, check_data(data))
    )


@pytest.mark.parametrize("tag", [["smoking", -0.1], ["smoking"], "smoking"])
def test_a_negative_or_malformed_topic_tag_is_reported(data, tag):
    edit("mini/dict/mini_age5.json", lambda d: variable(d, "smoke5").update(topics=[tag]))(data)
    problems = check_data(data)
    assert [p.path for p in problems] == ["mini/dict/mini_age5.json"]
    assert "smoke5" in problems[0].location


def test_a_file_that_is_not_utf8_is_reported(data):
    (data / "datasets.json").write_bytes(b'{"built": "\xff"}')
    assert [str(p) for p in check_data(data)] == [
        "datasets.json: not valid UTF-8 (invalid start byte at byte 11)"
    ]
