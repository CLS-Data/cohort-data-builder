"""The Python API: tag text and variables in code (feature 006)."""

import pytest

from topic_tagger.scheme import load_scheme
from topic_tagger.variables import Variable


@pytest.fixture(autouse=True)
def nothing_written_or_printed(tmp_path, monkeypatch, capsys):
    """Every API test runs in an empty folder, which must stay empty, and prints nothing."""
    monkeypatch.chdir(tmp_path)
    yield
    assert list(tmp_path.iterdir()) == []
    assert capsys.readouterr() == ("", "")


def leaves(scheme):
    return {t.id for t in scheme.topics}


# --- US1: tag in one call with a scheme file ---------------------------------------------


def test_tag_returns_one_result_per_input_in_order(scheme_run_path, fake_decision):
    from topic_tagger import tag

    texts = ["Do you smoke?", "Weight in kg", "Do you smoke?"]
    results = tag(texts, scheme_run_path, provider=fake_decision)
    assert len(results) == 3
    assert [r.input for r in results] == texts
    allowed = leaves(load_scheme(scheme_run_path))
    for r in results:
        assert not r.failed and r.error == ""
        assert r.tags and all(t.topic in allowed for t in r.tags)
        confidences = [t.confidence for t in r.tags]
        assert confidences == sorted(confidences, reverse=True)
        assert r.path and all(isinstance(g, str) and 0 <= c <= 1 for g, c in r.path)
    # The default fake prefers the first option at every tier.
    assert results[0].tags[0].topic == "age"
    assert results[0].tags[0].label == "Age"
    assert results[0].path == [("demographics", 0.9)]


def test_duplicates_are_asked_separately(scheme_run_path, fake_decision):
    from topic_tagger import tag

    tag(["Same", "Same"], scheme_run_path, provider=fake_decision)
    states = [s for s, _, _ in fake_decision.calls]
    assert states.count({"name": "", "label": "Same", "values": []}) == 4  # 2 tiers × 2


def test_text_is_sent_as_the_label(scheme_run_path, fake_decision):
    from topic_tagger import tag

    tag(["Do you smoke?"], scheme_run_path, provider=fake_decision)
    assert fake_decision.calls[0][0] == {"name": "", "label": "Do you smoke?", "values": []}


def test_variables_and_dicts_are_sent_as_the_command_line_sends_them(
    scheme_run_path, fake_decision
):
    from topic_tagger import tag
    from topic_tagger.tiered import _state

    v = Variable("alpha", "SMK", "Smokes", (("1", "Yes"), ("2", "No")))
    line = {"file": "beta", "variable": "AGE", "label": "Age now", "values": [[1, "16-24"]]}
    results = tag([v, line, "plain"], scheme_run_path, provider=fake_decision)
    assert [r.input for r in results] == [v, line, "plain"]
    states = [s for s, _, _ in fake_decision.calls]
    assert _state(v) in states
    assert {"name": "AGE", "label": "Age now", "values": ["1: 16-24"]} in states
    assert {"name": "", "label": "plain", "values": []} in states


def test_long_value_lists_are_cut_as_on_the_command_line(scheme_run_path, fake_decision):
    from topic_tagger import tag

    v = Variable("a", "x", "X", tuple((str(i), f"L{i}") for i in range(40)))
    tag([v], scheme_run_path, provider=fake_decision)
    values = fake_decision.calls[0][0]["values"]
    assert len(values) == 31 and values[-1] == "… and 10 more"


def test_classify_returns_one_result(scheme_run_path, fake_decision):
    from topic_tagger import Result, classify

    r = classify("Do you smoke?", scheme_run_path, provider=fake_decision)
    assert isinstance(r, Result)
    assert r.input == "Do you smoke?" and r.topics == ["age"]


def test_results_carry_the_settings_and_the_scheme(scheme_run_path, fake_decision):
    from topic_tagger import tag

    results = tag(["a", "b"], scheme_run_path, provider=fake_decision)
    assert list(results) == [results[0], results[1]]
    assert results.settings["method"] == "tiered"
    assert results.sources["method"] == "file"
    assert results.settings["descend_at"] == 0.3 and results.sources["descend_at"] == "file"
    assert results.scheme_name == "Test topics"
    assert results.scheme_hash == load_scheme(scheme_run_path).hash
    assert results.requests_by_tier == [2, 2]
    assert results.retries == 0 and results.failed == []


def test_an_empty_call_sends_nothing(scheme_run_path, fake_decision):
    from topic_tagger import tag

    results = tag([], scheme_run_path, provider=fake_decision)
    assert len(results) == 0
    assert fake_decision.calls == [] and fake_decision.checked == 0


def test_a_result_as_a_dict(scheme_run_path, fake_decision):
    from topic_tagger import classify

    d = classify("x", scheme_run_path, provider=fake_decision).to_dict()
    assert d["topics"] == [["age", 0.9]]
    assert d["path"] == [["demographics", 0.9]]
    assert d["method"] == "tiered"
    assert d["model"] == "ollama-decision:fake-decision"  # [run] names the model
    assert d["scheme"] == load_scheme(scheme_run_path).hash
    assert (d["failed"], d["error"]) == (False, "")


def test_every_public_name_imports_and_is_documented():
    import topic_tagger

    expected = {
        "tag",
        "classify",
        "Tagger",
        "Result",
        "Results",
        "Tag",
        "Variable",
        "Scheme",
        "load_scheme",
        "parse_scheme",
        "SchemeError",
        "ProviderError",
        "OptionLimitError",
        "RemoteModelError",
    }
    assert set(topic_tagger.__all__) == expected
    for name in topic_tagger.__all__:
        assert getattr(topic_tagger, name).__doc__, name
