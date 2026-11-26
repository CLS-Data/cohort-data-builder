"""scripts/sweep_ages.py: a sweep's age read from its label (feature 007, task T002a).

The CLS metadata gives each sweep a `sweep-year-age` text, built into sweep labels such as
"Sweep 6.1: age 44/45, 2002/04". Every manifest here is a copy of the fictional fixture.
"""

import json
import shutil
from pathlib import Path

import pytest
from sweep_ages import BAD_INPUT, CHECKS_FAILED, OK, age_from_label, fill_ages, main

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "data"


@pytest.mark.parametrize(
    ("label", "expected"),
    [
        ("Sweep 6.1: age 44/45, 2002/04", (44, [44, 45])),
        ("Sweep 4: age 16, 1986", (16, None)),
        ("Sweep 2: age 5 years, 1975", (5, None)),
        ("Sweep 1: age 9 months, 2001/02", (0.75, None)),
        ("Sweep 1: age 9/10 months, 2001/02", (0.75, [0.75, 10 / 12])),
        ("Sweep 0: age birth, 1958", (0, None)),
        ("Sweep 0: birth, 1970", (0, None)),
        ("Sweep 3: age 2.5, 2003/04", (2.5, None)),
        ("Sweep 7: age 33-35, 1991", (33, [33, 35])),
        ("Sweep 7: age 33–35, 1991", (33, [33, 35])),
        ("Sweep 9: Age 42", (42, None)),
        ("Sweep6.1 - 2002/04 - 44/45 years old", (44, [44, 45])),
        ("Age 5", (5, None)),
    ],
)
def test_ages_are_read_from_labels(label, expected):
    age, span = age_from_label(label)
    assert age == pytest.approx(expected[0])
    assert span == (None if expected[1] is None else pytest.approx(expected[1]))


@pytest.mark.parametrize(
    "label",
    [
        "Cross-sweep files",
        "Sweep 6: 2002/04",  # a year span, not an age
        "Wave 2",
        "Linked records",
        "Sweep 7: age 45/44, 2004",  # a span backwards: unreadable, not guessed
        "Sweep 1: age 130",  # beyond the checks' 0-120
        "",
    ],
)
def test_labels_without_an_age_give_none(label):
    assert age_from_label(label) == (None, None)


def test_fill_sets_ages_and_keeps_existing_ones():
    manifest = {
        "wave": {
            "list": [
                {"key": "s1", "label": "Sweep 1: age 9 months, 2001/02"},
                {"key": "s2", "label": "Sweep 2: age 3, 2004", "age": 3.1},
                {"key": "s3", "label": "Sweep 3: age 44/45, 2002/04"},
                {"key": "xwave", "label": "Cross-sweep"},
            ]
        }
    }
    outcome = fill_ages(manifest)
    waves = manifest["wave"]["list"]
    assert waves[0]["age"] == pytest.approx(0.75)
    assert "ageRange" not in waves[0]
    assert waves[1]["age"] == 3.1  # kept, not replaced by the label's 3
    assert (waves[2]["age"], waves[2]["ageRange"]) == (44, [44, 45])
    assert "age" not in waves[3]
    assert outcome.set == ["s1", "s3"]
    assert outcome.kept == ["s2"]
    assert outcome.unknown == ["xwave"]


def test_whole_ages_are_written_as_integers():
    manifest = {"wave": {"list": [{"key": "s1", "label": "Sweep 1: age 16, 1986"}]}}
    fill_ages(manifest)
    assert json.dumps(manifest["wave"]["list"][0]["age"]) == "16"


@pytest.fixture
def data(tmp_path):
    """A copy of the fixture data whose `mini` sweeps carry CLS-style labels and no ages."""
    root = tmp_path / "data"
    shutil.copytree(FIXTURES, root)
    path = root / "mini" / "manifest.json"
    m = json.loads(path.read_text())
    waves = m["wave"]["list"]
    waves[0].update(key="s1", label="Sweep 1: age 5, 1975")
    waves[1].update(key="s2", label="Sweep 2: age 9/10, 1980")
    for f in m["files"]:
        f["wave"] = {"5y": "s1", "10y": "s2"}.get(f["wave"], f["wave"])
    path.write_text(json.dumps(m))
    for d in (root / "mini" / "dict").glob("*.json"):
        dic = json.loads(d.read_text())
        dic["wave"] = {"5y": "s1", "10y": "s2"}.get(dic["wave"], dic["wave"])
        d.write_text(json.dumps(dic))
    return root


def waves_of(root, key="mini"):
    """The sweep list of a cohort's manifest on disk."""
    return json.loads((root / key / "manifest.json").read_text())["wave"]["list"]


def test_a_dry_run_writes_nothing(data, capsys):
    before = (data / "mini" / "manifest.json").read_text()
    assert main([str(data / "mini")]) == OK
    assert (data / "mini" / "manifest.json").read_text() == before
    out = capsys.readouterr().out
    assert "s1" in out and "5" in out
    assert "--write" in out


def test_write_adds_ages_and_the_checks_pass(data, capsys):
    assert main([str(data / "mini"), "--write"]) == OK
    waves = waves_of(data)
    assert waves[0]["age"] == 5
    assert (waves[1]["age"], waves[1]["ageRange"]) == (9, [9, 10])
    assert "age" not in waves[2]  # xwave
    assert "xwave" in capsys.readouterr().out


def test_several_cohorts_at_once(data):
    assert main([str(data / "mini"), str(data / "mini3"), "--write"]) == OK
    assert waves_of(data, "mini3")[0]["age"] == 16  # its label is "Age 16"


def test_repeated_and_earlier_ages_are_written(data):
    # As in the real cohorts: sub-sweeps at one age, listed before a younger sweep.
    path = data / "mini" / "manifest.json"
    m = json.loads(path.read_text())
    m["wave"]["list"][0]["label"] = "Sweep 1.1: age 63, 2020"
    m["wave"]["list"][1]["label"] = "Sweep 2: age 61/65, 2020/24"
    m["wave"]["list"][2]["label"] = "Sweep 1.2: age 63, 2021"
    path.write_text(json.dumps(m))
    assert main([str(data / "mini"), "--write"]) == OK
    assert [w["age"] for w in waves_of(data)] == [63, 61, 63]


def test_problems_in_the_data_fail_the_checks(data, capsys):
    path = data / "mini" / "manifest.json"
    m = json.loads(path.read_text())
    m["wave"]["list"][2]["age"] = 200  # kept as it is, and out of range
    path.write_text(json.dumps(m))
    assert main([str(data / "mini"), "--write"]) == CHECKS_FAILED
    assert "0 to 120" in capsys.readouterr().out


def test_a_folder_without_a_manifest_is_bad_input(tmp_path, capsys):
    assert main([str(tmp_path)]) == BAD_INPUT
    assert "manifest.json" in capsys.readouterr().err
