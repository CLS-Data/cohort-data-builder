import copy
import json
import re

import pytest

from topic_tagger.scheme import SchemeError, load_scheme, validate


def test_loads_the_small_scheme(small_scheme):
    s = small_scheme
    assert s.name == "Test topics"
    assert s.version == 1
    assert "Tag each variable" in s.guidance
    assert s.identifier_topic == "identifiers"
    assert s.fallback_topic == "other"
    assert [d.id for d in s.domains] == ["demographics", "health", "survey"]
    assert s.topic_ids == [
        "age",
        "gender",
        "smoking",
        "alcohol",
        "physical_health",
        "identifiers",
        "survey_weights",
        "other",
    ]


def test_topic_numbers_run_across_the_whole_scheme(small_scheme):
    assert small_scheme.topic_number("age") == 0
    assert small_scheme.topic_number("smoking") == 2
    assert small_scheme.topic_number("other") == 7


def test_domain_of_a_topic(small_scheme):
    assert small_scheme.domain_of("alcohol").id == "health"
    assert small_scheme.domain_of("identifiers").id == "survey"


def test_hash_is_short_stable_and_follows_the_content(small_scheme_path, tmp_path):
    a = load_scheme(small_scheme_path)
    assert re.fullmatch(r"[0-9a-f]{12}", a.hash)
    assert load_scheme(small_scheme_path).hash == a.hash

    text = small_scheme_path.read_text()
    changed = tmp_path / "s.toml"
    changed.write_text(text.replace("Tobacco use.", "Tobacco and vaping."))
    assert load_scheme(changed).hash != a.hash
    changed.write_text(text.replace("Tag each variable", "Tag every variable"))
    assert load_scheme(changed).hash != a.hash


def test_comments_and_layout_do_not_change_the_hash(small_scheme_path, tmp_path):
    text = small_scheme_path.read_text()
    other = tmp_path / "s.toml"
    other.write_text(
        "# a new comment\n\n" + text.replace("  [[domains.topics]]", "[[domains.topics]]")
    )
    assert load_scheme(other).hash == load_scheme(small_scheme_path).hash


def test_to_json_has_the_documented_shape(small_scheme):
    data = small_scheme.to_json()
    assert set(data) == {
        "name",
        "version",
        "hash",
        "guidance",
        "identifier_topic",
        "fallback_topic",
        "domains",
    }
    assert data["hash"] == small_scheme.hash
    first = data["domains"][0]
    assert first["id"] == "demographics" and first["label"] == "Demographics"
    assert first["topics"][0] == {
        "id": "age",
        "label": "Age",
        "description": "Age or date of birth.",
    }
    json.dumps(data)  # serialisable


def test_the_bundled_scheme_loads():
    s = load_scheme(None)
    assert len(s.domains) == 15
    assert len(s.topic_ids) > 90
    assert s.identifier_topic == "identifiers" and s.fallback_topic == "other"
    assert s.topic_number(s.fallback_topic) == len(s.topic_ids) - 1


# --- Checking a scheme (US3) --------------------------------------------------------------

GOOD = {
    "name": "S",
    "version": 1,
    "guidance": "g",
    "identifier_topic": "ids",
    "fallback_topic": "other",
    "domains": [
        {
            "id": "a",
            "label": "A",
            "description": "d",
            "topics": [{"id": "ids", "label": "Ids", "description": "d"}],
        },
        {
            "id": "b",
            "label": "B",
            "description": "d",
            "topics": [
                {"id": "other", "label": "Other", "description": "d"},
                {"id": "smoke", "label": "Smoke", "description": "d"},
            ],
        },
    ],
}


def broken(change):
    raw = copy.deepcopy(GOOD)
    change(raw)
    return {p.location: p.message for p in validate(raw)}


def test_a_good_scheme_has_no_problems():
    assert validate(GOOD) == []


@pytest.mark.parametrize(
    "change, location, words",
    [
        (
            lambda r: r["domains"][1]["topics"][1].update(id="Smoke"),
            "domains[1].topics[1].id",
            "lower-case",
        ),
        (
            lambda r: r["domains"][1]["topics"][1].update(id="9lives"),
            "domains[1].topics[1].id",
            "lower-case",
        ),
        (
            lambda r: r["domains"][1]["topics"][1].update(id="ids"),
            "domains[1].topics[1].id",
            "also used at domains[0].topics[0].id",
        ),
        (
            lambda r: r["domains"][1].update(id="ids"),
            "domains[1].id",
            "also used at domains[0].topics[0].id",
        ),
        (lambda r: r["domains"][0].update(topics=[]), "domains[0].topics", "no topics"),
        (
            lambda r: r["domains"][1]["topics"][0].pop("description"),
            "domains[1].topics[0].description",
            "missing",
        ),
        (lambda r: r["domains"][0].update(label="  "), "domains[0].label", "missing"),
        (lambda r: r.pop("guidance"), "guidance", "missing"),
        (lambda r: r.pop("name"), "name", "missing"),
        (lambda r: r.update(version="one"), "version", "whole number"),
        (lambda r: r.update(identifier_topic="nope"), "identifier_topic", "not a topic"),
        (lambda r: r.update(fallback_topic="b"), "fallback_topic", "not a topic"),
        (lambda r: r.update(domains=[]), "domains", "no domains"),
    ],
)
def test_each_mistake_is_found_with_its_location(change, location, words):
    problems = broken(change)
    assert location in problems, problems
    assert words in problems[location]


def test_every_mistake_is_reported_not_only_the_first():
    def many(r):
        r["domains"][0]["topics"] = []
        r["domains"][1]["topics"][1]["id"] = "Bad"
        r.pop("guidance")

    assert len(broken(many)) >= 3


def test_load_scheme_raises_with_every_problem(small_scheme_path, tmp_path):
    text = small_scheme_path.read_text()
    bad = tmp_path / "bad.toml"
    bad.write_text(
        text.replace('id = "alcohol"', 'id = "smoking"').replace('id = "age"', 'id = "Age"')
    )
    with pytest.raises(SchemeError) as err:
        load_scheme(bad)
    assert len(err.value.problems) == 2
    assert "smoking" in str(err.value) and "domains[0].topics[0].id" in str(err.value)


def test_invalid_toml_names_the_line(tmp_path):
    bad = tmp_path / "bad.toml"
    bad.write_text('name = "x"\nversion = \n')
    with pytest.raises(SchemeError) as err:
        load_scheme(bad)
    assert "line 2" in str(err.value)
