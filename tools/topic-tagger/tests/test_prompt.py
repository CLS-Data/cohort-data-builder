import json

from topic_tagger.prompt import MAX_VALUES, build_messages, reply_schema
from topic_tagger.scheme import load_scheme
from topic_tagger.variables import Variable


def batch():
    return [
        Variable("alpha", "A01SMOK", "Smokes now", (("1", "Yes"), ("2", "No"))),
        Variable("alpha", "A02X", None),
        Variable("beta", "B01BIG", "Many values", tuple((str(i), f"L{i}") for i in range(200))),
    ]


def test_system_message_has_guidance_topics_and_rules(small_scheme):
    system, _ = build_messages(small_scheme, batch())
    assert system["role"] == "system"
    text = system["content"]
    assert "Tag each variable with the topics it measures." in text
    assert "Health" in text
    assert "smoking: Smoking — Tobacco use." in text
    # every topic appears, under its domain
    for t in small_scheme.topics:
        assert f"{t.id}: {t.label} — {t.description}" in text
    assert text.index("Health") < text.index("smoking:") < text.index("Survey administration")
    assert "if nothing fits, use `other` with a low confidence" in text.lower()


def test_the_fallback_topic_comes_from_the_scheme(small_scheme_path, tmp_path):
    other = tmp_path / "s.toml"
    other.write_text(
        small_scheme_path.read_text().replace(
            'fallback_topic = "other"', 'fallback_topic = "survey_weights"'
        )
    )
    system, _ = build_messages(load_scheme(other), batch())
    assert "use `survey_weights` with a low confidence" in system["content"]


def test_user_message_lists_the_batch_with_local_ids(small_scheme):
    _, user = build_messages(small_scheme, batch())
    assert user["role"] == "user"
    lines = [json.loads(x) for x in user["content"].splitlines() if x.startswith("{")]
    assert [x["id"] for x in lines] == [0, 1, 2]
    assert lines[0] == {
        "id": 0,
        "name": "A01SMOK",
        "label": "Smokes now",
        "values": ["1: Yes", "2: No"],
    }
    assert lines[1] == {"id": 1, "name": "A02X", "label": "", "values": []}


def test_long_value_lists_are_cut(small_scheme):
    _, user = build_messages(small_scheme, batch())
    big = [json.loads(x) for x in user["content"].splitlines() if x.startswith("{")][2]
    assert len(big["values"]) == MAX_VALUES + 1 == 31
    assert big["values"][-1] == "… and 170 more"


def test_only_metadata_is_sent(small_scheme):
    _, user = build_messages(small_scheme, batch())
    for x in user["content"].splitlines():
        if x.startswith("{"):
            assert set(json.loads(x)) == {"id", "name", "label", "values"}


def test_reply_schema_limits_topics_and_confidences(small_scheme):
    schema = reply_schema(small_scheme)
    text = json.dumps(schema)
    assert json.dumps(small_scheme.topic_ids) in text  # the enum, in scheme order
    tag = schema["$defs"]["TopicTag"]["properties"]
    assert tag["confidence"]["minimum"] == 0 and tag["confidence"]["maximum"] == 1


def test_the_reply_format_comes_from_the_langchain_parser(small_scheme):
    # Some hosts (e.g. Ollama cloud models) ignore the JSON schema, so the prompt carries
    # the standard PydanticOutputParser format instructions too.
    from langchain_core.output_parsers import PydanticOutputParser

    from topic_tagger.reply import reply_model

    system, _ = build_messages(small_scheme, batch())
    parser = PydanticOutputParser(pydantic_object=reply_model(small_scheme))
    assert system["content"].endswith(parser.get_format_instructions())
