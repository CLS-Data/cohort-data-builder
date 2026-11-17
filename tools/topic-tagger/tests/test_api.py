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

    v = Variable("alpha", "SMK", "Smokes", (("1", "Yes"), ("2", "No")))
    line = {"file": "beta", "variable": "AGE", "label": "Age now", "values": [[1, "16-24"]]}
    results = tag([v, line, "plain"], scheme_run_path, provider=fake_decision)
    assert [r.input for r in results] == [v, line, "plain"]
    states = [s for s, _, _ in fake_decision.calls]
    assert {"name": "SMK", "label": "Smokes", "values": ["1: Yes", "2: No"]} in states
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


# --- US2: choose the model, provider and method in code ----------------------------------


def test_a_call_argument_overrides_the_file(scheme_run_path, fake_decision):
    from topic_tagger import tag

    results = tag(["a", "b"], scheme_run_path, provider=fake_decision, method="flat")
    assert results.settings["method"] == "flat" and results.sources["method"] == "call"
    assert all(r.path is None and r.method == "flat" for r in results)
    n_leaves = len(load_scheme(scheme_run_path).topics)
    assert [len(options) for _, _, options in fake_decision.calls] == [n_leaves, n_leaves]


def test_tiered_settings_from_the_call(scheme_run_path, fake_decision):
    from topic_tagger import tag

    results = tag(["a"], scheme_run_path, provider=fake_decision, descend_at=0.9, max_follow=1)
    assert (results.settings["descend_at"], results.settings["max_follow"]) == (0.9, 1)
    assert results.sources["descend_at"] == results.sources["max_follow"] == "call"


def test_a_scheme_from_text_tags_as_the_file(scheme_run_path, fake_decision):
    from topic_tagger import parse_scheme, tag

    from_text = tag(["a"], parse_scheme(scheme_run_path.read_text()), provider=fake_decision)
    from_file = tag(["a"], scheme_run_path, provider=fake_decision)
    assert from_text.scheme_hash == from_file.scheme_hash
    assert from_text[0].tags == from_file[0].tags


def test_no_scheme_means_the_bundled_one(fake_decision):
    from topic_tagger import tag

    results = tag(["a"], provider=fake_decision)
    assert results.scheme_hash == "3c9f6b4b4ef9"
    assert results.scheme_name == "CLOSER topics"


def test_a_provider_object_is_a_decision_or_a_chat_model(
    small_scheme_path, fake_decision, fake_chat
):
    from topic_tagger import Tagger

    decision = Tagger(small_scheme_path, provider=fake_decision)
    assert decision.settings["provider"] == "ollama-decision"
    assert decision.settings["method"] == "tiered" and decision.settings["keep_at"] == 0.3
    chat = Tagger(small_scheme_path, provider=fake_chat)
    assert chat.settings["provider"] == "ollama"
    assert chat.settings["method"] == "flat" and chat.settings["keep_at"] is None
    assert decision.sources["provider"] == chat.sources["provider"] == "call"


@pytest.mark.parametrize("method", ["flat", "tiered"])
def test_a_chat_model_tags_flat_and_tiered(small_scheme_path, fake_chat, method):
    from topic_tagger import tag

    results = tag(["a", "b"], small_scheme_path, provider=fake_chat, method=method)
    allowed = leaves(load_scheme(small_scheme_path))
    assert all(r.tags and set(r.topics) <= allowed for r in results)
    assert all((r.path is None) == (method == "flat") for r in results)


def test_a_one_tier_taxonomy_tags_flat_with_a_note(fixtures_dir, fake_decision):
    from topic_tagger import tag

    results = tag(["a"], fixtures_dir / "scheme_1tier.toml", provider=fake_decision)
    assert results.settings["method"] == "flat"
    assert results.notes == ["This taxonomy has one tier: tagging flat."]


def test_the_model_label_for_a_provider_object(small_scheme_path, fake_decision):
    from topic_tagger import classify

    named = classify("a", small_scheme_path, provider=fake_decision, model="my-model")
    assert named.model == "ollama-decision:my-model"
    assert classify("a", small_scheme_path, provider=fake_decision).model == (
        "ollama-decision:custom"
    )


def test_a_tagger_shows_its_settings_before_any_call(scheme_run_path, fake_decision):
    from topic_tagger import Tagger

    t = Tagger(scheme_run_path, provider=fake_decision)
    assert t.settings["model"] == "fake-decision" and t.sources["model"] == "file"
    assert t.notes == [] and fake_decision.checked == 0 and fake_decision.calls == []


def test_host_settings_reach_the_provider(monkeypatch, small_scheme_path, fake_decision):
    from topic_tagger import Tagger

    made = []

    def get_provider(name, **kwargs):
        made.append((name, kwargs))
        return fake_decision

    monkeypatch.setattr("topic_tagger.api.get_provider", get_provider)
    Tagger(
        small_scheme_path,
        provider="ollama-decision",
        model="clef",
        base_url="http://h:1/v1",
        timeout=7,
        api_key="k",
    )
    assert made[-1] == (
        "ollama-decision",
        {"base_url": "http://h:1/v1", "model": "clef", "timeout": 7, "api_key": "k"},
    )
    monkeypatch.setenv("TOPIC_TAGGER_API_KEY", "env")
    Tagger(small_scheme_path, provider="ollama-decision")
    assert made[-1][1]["api_key"] == "env"


def test_batch_size_sets_how_many_variables_share_a_request(small_scheme_path, fake_chat):
    from conftest import StubProvider, first_option
    from topic_tagger import tag

    tag(["a", "b", "c"], small_scheme_path, provider=fake_chat, batch_size=1)
    assert len(fake_chat.calls) == 3
    one = StubProvider(first_option)
    tag(["a", "b", "c"], small_scheme_path, provider=one)
    assert len(one.calls) == 1


def test_a_scheme_cannot_set_batch_size(small_scheme_path):
    from topic_tagger import SchemeError, parse_scheme

    text = small_scheme_path.read_text() + "\n[run]\nbatch_size = 5\n"
    with pytest.raises(SchemeError) as err:
        parse_scheme(text)
    assert "run.batch_size" in str(err.value.problems[0])


class NoRemote:
    def check(self):
        pass

    def decide(self, state, instructions, options):
        return {}


class NeitherKind:
    def check(self):
        pass

    def is_remote(self):
        return False


@pytest.mark.parametrize(
    ("obj", "missing"), [(NoRemote(), "is_remote"), (NeitherKind(), "decide or complete")]
)
def test_a_provider_object_must_have_what_is_needed(small_scheme_path, obj, missing):
    from topic_tagger import Tagger

    with pytest.raises(TypeError, match=missing):
        Tagger(small_scheme_path, provider=obj)


# --- US3: errors a caller can handle ----------------------------------------------------


def test_a_broken_scheme_is_a_scheme_error(tmp_path_factory):
    from topic_tagger import SchemeError, parse_scheme, tag

    bad = tmp_path_factory.mktemp("schemes") / "bad.toml"
    bad.write_text('name = "x"\nversion = 1\n', encoding="utf-8")
    with pytest.raises(SchemeError) as err:
        tag(["a"], bad)
    assert len(err.value.problems) > 1
    with pytest.raises(SchemeError):
        parse_scheme('name = "x"\n')


def test_a_bad_setting_is_a_value_error_and_reaches_no_provider(
    small_scheme_path, fake_decision, fake_chat
):
    from topic_tagger import tag

    with pytest.raises(ValueError) as err:
        tag(["a"], small_scheme_path, provider=fake_decision, descend_at=1.5)
    assert str(err.value) == "--descend-at must be between 0 and 1"
    with pytest.raises(ValueError, match="--keep-at"):
        tag(["a"], small_scheme_path, provider=fake_chat, keep_at=0.4)
    assert fake_decision.calls == [] and fake_decision.checked == 0
    assert fake_chat.calls == [] and fake_chat.checked == 0


def test_a_bad_input_names_its_position(small_scheme_path, fake_decision):
    from topic_tagger import tag

    with pytest.raises(TypeError, match="input 0"):
        tag([42], small_scheme_path, provider=fake_decision)
    with pytest.raises(ValueError, match="^input 1: 'file' is missing"):
        tag(["ok", {"variable": "x"}], small_scheme_path, provider=fake_decision)
    assert fake_decision.calls == []


def test_an_unreachable_host_is_raised_before_any_question(small_scheme_path):
    from conftest import FakeDecisionModel
    from topic_tagger import ProviderError, tag

    model = FakeDecisionModel(check_error=ProviderError("model missing"))
    with pytest.raises(ProviderError, match="model missing"):
        tag(["a"], small_scheme_path, provider=model)
    assert model.calls == []


def test_a_cloud_model_needs_allow_remote(small_scheme_path):
    from conftest import FakeDecisionModel
    from topic_tagger import ProviderError, RemoteModelError, tag

    model = FakeDecisionModel(remote=True)
    with pytest.raises(RemoteModelError) as err:
        tag(["a"], small_scheme_path, provider=model, model="clef:cloud")
    assert isinstance(err.value, ProviderError)
    assert "clef:cloud" in str(err.value) and "allow_remote=True" in str(err.value)
    assert model.calls == [] and model.checked == 0
    assert tag(["a"], small_scheme_path, provider=model, allow_remote=True)[0].tags


def test_a_refused_question_is_raised_with_its_name():
    from conftest import FakeDecisionModel
    from topic_tagger import OptionLimitError, tag

    model = FakeDecisionModel(refuse_over=5)
    with pytest.raises(OptionLimitError) as err:
        tag(["a", "b"], provider=model, method="flat")
    assert err.value.options == 107
    assert err.value.question == "every topic, asked flat"


def test_an_input_that_keeps_failing_is_a_failed_result(small_scheme_path):
    from conftest import FakeDecisionModel
    from topic_tagger import tag

    model = FakeDecisionModel(fail_for={"bad"})
    results = tag(["good", "bad", "also good"], small_scheme_path, provider=model)
    assert [r.failed for r in results] == [False, True, False]
    assert results[1].error == "no answer" and results[1].tags == []
    assert results[0].error == results[2].error == ""
    assert results.failed == [results[1]]


# --- US4: reuse one tagger ----------------------------------------------------------------


def test_one_tagger_checks_the_host_once(scheme_run_path, fake_decision):
    from topic_tagger import Tagger

    t = Tagger(scheme_run_path, provider=fake_decision)
    t.tag(["a", "b"])
    t.tag(["c"])
    t.classify("d")
    assert fake_decision.checked == 1


def test_one_tagger_gives_what_separate_calls_give(scheme_run_path):
    from conftest import FakeDecisionModel
    from topic_tagger import Tagger, tag

    def probability(state, option):
        return (len(state["label"]) * 7 + len(option)) % 10 / 10 + 0.05

    t = Tagger(scheme_run_path, provider=FakeDecisionModel(probability))
    reused = [t.tag(["Do you smoke?", "Age"]), t.tag(["Weight in kg"])]
    separate = [
        tag(["Do you smoke?", "Age"], scheme_run_path, provider=FakeDecisionModel(probability)),
        tag(["Weight in kg"], scheme_run_path, provider=FakeDecisionModel(probability)),
    ]
    for a, b in zip(reused, separate, strict=True):
        assert [(r.tags, r.path) for r in a] == [(r.tags, r.path) for r in b]


def test_check_false_never_checks(scheme_run_path, fake_decision):
    from topic_tagger import Tagger

    Tagger(scheme_run_path, provider=fake_decision, check=False).tag(["a"])
    assert fake_decision.checked == 0


def test_a_single_string_is_refused_rather_than_tagged_letter_by_letter(
    scheme_run_path, fake_decision
):
    from topic_tagger import tag

    with pytest.raises(TypeError, match="list"):
        tag("Do you smoke?", scheme_run_path, provider=fake_decision)


@pytest.mark.parametrize("setting", ["batch_size", "workers"])
def test_batch_size_and_workers_must_be_at_least_one(small_scheme_path, fake_decision, setting):
    from topic_tagger import Tagger

    with pytest.raises(ValueError, match=setting):
        Tagger(small_scheme_path, provider=fake_decision, **{setting: 0})
