import json

import pytest

from conftest import StubProvider
from test_runner import answer
from topic_tagger.cli import main
from topic_tagger.providers import ProviderError


def tag(variables_path, out, stub, *extra, clock=None):
    argv = ["tag", str(variables_path), "--out", str(out), *extra]
    return main(argv, provider_factory=lambda args: stub, clock=clock)


def records(out):
    return [json.loads(x) for x in (out / "tags.jsonl").read_text().splitlines()]


def test_tags_every_variable(tmp_path, variables_path, small_scheme_path, small_scheme, capsys):
    stub = StubProvider(answer("smoking", 0.7))
    code = tag(variables_path, tmp_path / "out", stub, "--scheme", str(small_scheme_path))
    assert code == 0
    recs = records(tmp_path / "out")
    assert len(recs) == 60
    for r in recs:
        assert r["topics"]
        for topic, conf in r["topics"]:
            assert topic in small_scheme.topic_ids
            assert 0 <= conf <= 1
    assert json.loads((tmp_path / "out" / "scheme.json").read_text())["hash"] == small_scheme.hash
    assert "60" in capsys.readouterr().out


def test_uses_the_bundled_scheme_by_default(tmp_path, variables_path):
    stub = StubProvider(answer("smoking", 0.7))
    assert tag(variables_path, tmp_path / "out", stub) == 0
    assert json.loads((tmp_path / "out" / "scheme.json").read_text())["name"] == "CLOSER topics"


def test_a_missing_input_file_exits_2(tmp_path, capsys):
    stub = StubProvider(answer())
    assert tag(tmp_path / "nope.jsonl", tmp_path / "out", stub) == 2
    assert "nope.jsonl" in capsys.readouterr().err
    assert stub.calls == []


def test_an_unreachable_host_exits_3_before_any_request(tmp_path, variables_path, capsys):
    stub = StubProvider(
        answer(), check_error=ProviderError("Ollama is not reachable at http://x/v1")
    )
    assert tag(variables_path, tmp_path / "out", stub) == 3
    assert "Ollama is not reachable at http://x/v1" in capsys.readouterr().err
    assert stub.calls == []


def test_dry_run_prints_the_prompt_and_sends_nothing(
    tmp_path, variables_path, small_scheme_path, capsys
):
    stub = StubProvider(answer(), check_error=ProviderError("not running"))
    code = tag(
        variables_path, tmp_path / "out", stub, "--scheme", str(small_scheme_path), "--dry-run"
    )
    assert code == 0
    out = capsys.readouterr().out
    assert "Tag each variable with the topics it measures." in out
    assert '"name": "A01AGE"' in out
    assert stub.calls == [] and stub.checked == 0
    assert not (tmp_path / "out" / "tags.jsonl").exists()


def test_a_remote_model_needs_yes(tmp_path, variables_path, capsys):
    stub = StubProvider(answer(), remote=True)
    assert tag(variables_path, tmp_path / "out", stub) == 2
    err = capsys.readouterr().err
    assert "leave this machine" in err and "--yes" in err
    assert stub.calls == []
    assert tag(variables_path, tmp_path / "out", stub, "--yes") == 0
    assert stub.calls


def test_failures_exit_1_and_are_listed(tmp_path, variables_path, capsys):
    stub = StubProvider(answer(skip={"A01AGE"}))
    assert tag(variables_path, tmp_path / "out", stub) == 1
    assert "alpha/A01AGE" in capsys.readouterr().err
    assert len(records(tmp_path / "out")) == 59


def test_settings_reach_the_provider_factory(tmp_path, variables_path, monkeypatch):
    seen = {}

    def factory(args):
        seen.update(vars(args))
        return StubProvider(answer())

    monkeypatch.setenv("TOPIC_TAGGER_BASE_URL", "http://box:1/v1")
    argv = ["tag", str(variables_path), "--out", str(tmp_path), "--model", "m1", "--timeout", "7"]
    assert main(argv, provider_factory=factory) == 0
    assert seen["base_url"] == "http://box:1/v1"
    assert seen["model"] == "m1" and seen["timeout"] == 7.0
    assert seen["provider"] == "ollama"
    rec = records(tmp_path)[1]
    assert rec["model"] == "ollama:m1"


def test_help_lists_every_option(capsys):
    with pytest.raises(SystemExit):
        main(["tag", "--help"])
    out = capsys.readouterr().out
    for opt in (
        "--scheme",
        "--provider",
        "--base-url",
        "--model",
        "--batch-size",
        "--workers",
        "--timeout",
        "--retries",
        "--files",
        "--limit",
        "--retag",
        "--dry-run",
        "--yes",
        "--plain",
        "--force",
    ):
        assert opt in out
