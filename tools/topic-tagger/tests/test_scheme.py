import json
import re

from topic_tagger.scheme import load_scheme


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
