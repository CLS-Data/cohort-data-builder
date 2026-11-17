"""Where each run setting comes from: the command line, the scheme's [run] table, or the
default (feature 005, US3)."""

import pytest

from topic_tagger.run_settings import RunSettings, resolve

NONE = dict.fromkeys(("provider", "model", "method", "descend_at", "max_follow", "keep_at"))


def cli(**given):
    return {**NONE, **given}


def test_the_defaults():
    r = resolve(cli(), None)
    assert r.values == {
        "provider": "ollama",
        "model": "gpt-oss:20b",
        "method": "flat",
        "descend_at": 0.5,
        "max_follow": 3,
        "keep_at": None,
    }
    assert set(r.sources.values()) == {"default"}
    assert r.notes == []


def test_a_decision_model_defaults_to_tiered_and_keep_at():
    r = resolve(cli(provider="ollama-decision"), None)
    assert r.values["method"] == "tiered" and r.values["keep_at"] == 0.3
    assert r.sources["provider"] == "cli" and r.sources["method"] == "default"


def test_the_command_line_wins_then_the_file_then_the_default():
    file = RunSettings(provider="ollama-decision", model="clef:cloud", descend_at=0.3)
    r = resolve(cli(model="other", max_follow=1), file)
    assert r.values["provider"] == "ollama-decision" and r.sources["provider"] == "file"
    assert r.values["model"] == "other" and r.sources["model"] == "cli"
    assert r.values["descend_at"] == 0.3 and r.sources["descend_at"] == "file"
    assert r.values["max_follow"] == 1 and r.sources["max_follow"] == "cli"
    assert r.sources["keep_at"] == "default"


def test_the_method_default_follows_the_provider_the_file_names():
    r = resolve(cli(), RunSettings(provider="ollama-decision"))
    assert r.values["method"] == "tiered" and r.sources["method"] == "default"
    r = resolve(cli(provider="ollama"), RunSettings(provider="ollama-decision"))
    assert r.values["method"] == "flat"


def test_a_file_keep_at_is_ignored_by_a_chat_model_with_a_note():
    r = resolve(cli(provider="ollama"), RunSettings(provider="ollama-decision", keep_at=0.2))
    assert r.values["keep_at"] is None and "keep_at" not in r.sources
    assert r.notes == ["keep_at in the scheme applies to decision models only; ignored."]


@pytest.mark.parametrize("source", ["cli", "file"])
def test_zero_is_a_value_not_a_missing_setting(source):
    file = RunSettings(max_follow=0, descend_at=0.0) if source == "file" else None
    given = cli(max_follow=0, descend_at=0.0) if source == "cli" else cli()
    r = resolve(given, file)
    assert r.values["max_follow"] == 0 and r.values["descend_at"] == 0.0
    assert r.sources["max_follow"] == source


# --- settle: the checks the CLI and the API share (feature 006) -------------------------

from topic_tagger.run_settings import settle  # noqa: E402
from topic_tagger.scheme import load_scheme  # noqa: E402


@pytest.fixture
def two_tier(small_scheme):
    return small_scheme


def test_settle_resolves_as_resolve_does_with_the_label_it_is_given(fixtures_dir):
    scheme = load_scheme(fixtures_dir / "scheme_run.toml")
    given = cli(method="flat")
    plain = resolve(given, scheme.run)
    settled = settle(given, scheme, label="call")
    assert settled.values == {**plain.values}
    assert settled.sources["method"] == "call"
    assert settled.sources["provider"] == "file"
    assert "cli" not in settled.sources.values()


@pytest.mark.parametrize(
    ("given", "message"),
    [
        ({"descend_at": 1.5}, "--descend-at must be between 0 and 1"),
        ({"keep_at": -0.1, "provider": "ollama-decision"}, "--keep-at must be between 0 and 1"),
        ({"max_follow": -1}, "--max-follow must be 0 (no cap) or more"),
        ({"keep_at": 0.4, "provider": "ollama"}, "--keep-at needs --provider ollama-decision"),
        (
            {"method": "flat", "descend_at": 0.4},
            "--descend-at and --max-follow need --method tiered",
        ),
    ],
)
def test_settle_rejects_what_the_command_line_rejects(two_tier, given, message):
    with pytest.raises(ValueError) as err:
        settle(cli(**given), two_tier)
    assert str(err.value) == message


def test_a_one_tier_taxonomy_settles_on_flat_with_a_note(fixtures_dir):
    scheme = load_scheme(fixtures_dir / "scheme_1tier.toml")
    settled = settle(cli(method="tiered"), scheme)
    assert settled.values["method"] == "flat"
    assert "This taxonomy has one tier: tagging flat." in settled.notes


def test_flat_drops_the_tiered_settings_from_the_sources(two_tier):
    settled = settle(cli(), two_tier)
    assert settled.values["method"] == "flat"
    assert "descend_at" not in settled.sources and "max_follow" not in settled.sources


def test_settle_keeps_the_note_about_a_file_keep_at(fixtures_dir):
    scheme = load_scheme(fixtures_dir / "scheme_run.toml")
    settled = settle(cli(provider="ollama"), scheme)
    assert any("keep_at" in n for n in settled.notes)
