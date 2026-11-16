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
        "fallback_topic",
        "domains",
        "tiers",
        "categories",
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


def test_the_bundled_scheme_loads(bundled_scheme_path):
    s = load_scheme(bundled_scheme_path)
    assert len(s.domains) == 15
    assert len(s.topic_ids) > 90
    assert s.fallback_topic == "other"
    assert not hasattr(s, "identifier_topic")
    assert s.topic_number(s.fallback_topic) == len(s.topic_ids) - 1


# --- Checking a scheme (US3) --------------------------------------------------------------

GOOD = {
    "name": "S",
    "version": 1,
    "guidance": "g",
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


# --- Taxonomies of one to three tiers (feature 005) -------------------------------------

FIXTURES = __import__("pathlib").Path(__file__).parent / "fixtures"
CLOSER = __import__("pathlib").Path(__file__).parents[1] / "src/topic_tagger/schemes/closer.toml"


def nested(tmp_path, text, name="n.toml"):
    path = tmp_path / name
    path.write_text('name = "N"\nversion = 1\nguidance = "G"\n' + text)
    return path


def test_004_schemes_keep_their_hash_and_views():
    closer = load_scheme(CLOSER)
    small = load_scheme(FIXTURES / "scheme_small.toml")
    assert closer.hash == "3c9f6b4b4ef9" and small.hash == "b2a923c4e9a5"
    assert closer.tiers == small.tiers == 2
    assert len(closer.topic_ids) == 107 and len(closer.domains) == 15
    assert small.domain_of("alcohol").id == "health"
    assert [t.id for t in small.domains[1].topics] == ["smoking", "alcohol", "physical_health"]


def test_a_one_tier_taxonomy_is_a_list_of_leaves():
    s = load_scheme(FIXTURES / "scheme_1tier.toml")
    assert s.tiers == 1
    assert s.topic_ids == ["age", "smoking", "housing", "income", "other"]
    # Each tier-1 leaf is an area of its own, for statistics and reports.
    assert [d.id for d in s.domains] == s.topic_ids
    assert s.domain_of("age").id == "age" and [t.id for t in s.domains[0].topics] == ["age"]
    assert s.path_of("age") == []


def test_a_three_tier_taxonomy_may_be_uneven():
    s = load_scheme(FIXTURES / "scheme_3tier.toml")
    assert s.tiers == 3
    assert s.topic_ids == [
        "respiratory",
        "cardiac",
        "diabetes",
        "depression",
        "anxiety",
        "smoking",
        "age",
        "gender",
        "other",
    ]
    assert s.domain_of("respiratory").id == "health"
    assert s.domain_of("smoking").id == "health"
    assert s.path_of("respiratory") == ["health", "physical_health"]
    assert s.path_of("smoking") == ["health"]
    assert s.path_of("other") == []
    cardiac = next(t for t in s.topics if t.id == "cardiac")
    assert cardiac.description == ""
    assert [c.id for c in s.root.children] == ["health", "demographics", "other"]


LEAVES = """
[[categories]]
id = "a"
label = "A"

[[categories]]
id = "other"
label = "Other"
"""


@pytest.mark.parametrize(
    ("text", "location", "words"),
    [
        (
            'fallback_topic = "other"\n[[categories]]\nid = "g1"\nlabel = "G1"\n'
            '[[categories.categories]]\nid = "g2"\nlabel = "G2"\n'
            '[[categories.categories.categories]]\nid = "g3"\nlabel = "G3"\n'
            '[[categories.categories.categories.categories]]\nid = "deep"\nlabel = "Deep"\n'
            + LEAVES,
            "categories[0].categories[0].categories[0].categories[0]",
            "at most 3 tiers",
        ),
        (
            'fallback_topic = "other"\n[[categories]]\nid = "a"\nlabel = "G"\n'
            '[[categories.categories]]\nid = "x"\nlabel = "X"\n'
            '[[categories.categories]]\nid = "y"\nlabel = "Y"\n' + LEAVES,
            "categories[1].id",
            "also used at categories[0].id",
        ),
        (
            'fallback_topic = "other"\n[[categories]]\nid = "g"\nlabel = "G"\ncategories = []\n'
            + LEAVES,
            "categories[0].categories",
            "no categories",
        ),
        (
            'fallback_topic = "other"\n[[categories]]\nid = "other"\nlabel = "Other"\n',
            "categories",
            "at least two leaves",
        ),
        (
            'fallback_topic = "g"\n[[categories]]\nid = "g"\nlabel = "G"\n'
            '[[categories.categories]]\nid = "x"\nlabel = "X"\n' + LEAVES,
            "fallback_topic",
            "not a leaf",
        ),
        (
            'fallback_topic = "other"\n[[domains]]\nid = "d"\nlabel = "D"\ndescription = "D."\n'
            '[[domains.topics]]\nid = "t"\nlabel = "T"\ndescription = "T."\n' + LEAVES,
            "categories",
            "not both",
        ),
        (
            'fallback_topic = "other"\n[[categories]]\nid = "nolabel"\n' + LEAVES,
            "categories[0].label",
            "missing",
        ),
    ],
)
def test_nested_mistakes_are_found_with_their_location(tmp_path, text, location, words):
    with pytest.raises(SchemeError) as err:
        load_scheme(nested(tmp_path, text))
    found = {p.location: p.message for p in err.value.problems}
    assert location in found, found
    assert words in found[location]


def test_every_nested_mistake_is_listed(tmp_path):
    text = (
        'fallback_topic = "zzz"\n[[categories]]\nid = "Bad"\nlabel = "B"\n'
        '[[categories]]\nid = "g"\nlabel = "G"\ncategories = []\n' + LEAVES
    )
    with pytest.raises(SchemeError) as err:
        load_scheme(nested(tmp_path, text))
    assert len(err.value.problems) >= 3


@pytest.mark.parametrize("name", ["scheme_1tier.toml", "scheme_small.toml", "scheme_3tier.toml"])
def test_scheme_json_round_trips_and_keeps_domains(name):
    from topic_tagger.scheme import scheme_from_json

    s = load_scheme(FIXTURES / name)
    data = s.to_json()
    assert data["tiers"] == s.tiers and "categories" in data
    assert [d["id"] for d in data["domains"]] == [d.id for d in s.domains]
    back = scheme_from_json(json.loads(json.dumps(data)))
    assert back.hash == s.hash and back.tiers == s.tiers
    assert back.topic_ids == s.topic_ids and back.root == s.root


def test_a_004_scheme_json_with_only_domains_still_reads(small_scheme):
    from topic_tagger.scheme import scheme_from_json

    data = small_scheme.to_json()
    data.pop("categories")
    data.pop("tiers")
    back = scheme_from_json(data)
    assert back.topic_ids == small_scheme.topic_ids and back.tiers == 2
