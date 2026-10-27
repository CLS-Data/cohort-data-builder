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


def test_failures_say_why(tmp_path, variables_path, capsys):
    from topic_tagger.reply import ReplyError

    stub = StubProvider(lambda m, s: (_ for _ in ()).throw(ReplyError("the reply is not JSON")))
    assert tag(variables_path, tmp_path / "out", stub) == 1
    err = capsys.readouterr().err
    assert "Last error: the reply is not JSON" in err


# --- Stopping and carrying on (US2) ------------------------------------------------------


def sent_names(stub):
    return [
        json.loads(x)["name"]
        for m, _ in stub.calls
        for x in m[1]["content"].splitlines()
        if x.startswith("{")
    ]


def topics_by_key(out):
    return {(r["file"], r["variable"]): r["topics"] for r in records(out)}


def test_resume_after_interrupt(tmp_path, variables_path, small_scheme_path):
    scheme = ["--scheme", str(small_scheme_path), "--workers", "1"]
    whole = tmp_path / "whole"
    assert tag(variables_path, whole, StubProvider(answer("smoking", 0.7)), *scheme) == 0

    out = tmp_path / "out"
    box = []

    def stop_on_second(messages, schema):
        if len(first.calls) == 2:
            box[0].request_stop()
        return answer("smoking", 0.7)(messages, schema)

    first = StubProvider(stop_on_second)
    argv = ["tag", str(variables_path), "--out", str(out), *scheme]
    assert main(argv, provider_factory=lambda a: first, runner_created=box.append) == 130
    run = json.loads((out / "run.json").read_text())
    assert run["status"] == "stopped"
    assert not (out / ".lock").exists()

    second = StubProvider(answer("smoking", 0.7))
    assert tag(variables_path, out, second, *scheme) == 0
    assert len(sent_names(second)) == 59 - 40  # only what the first run did not tag
    assert topics_by_key(out) == topics_by_key(whole)
    assert len(records(out)) == 60  # compacted: one line per variable


def test_a_scheme_change_redoes_everything(tmp_path, variables_path, small_scheme_path):
    tag(variables_path, tmp_path, StubProvider(answer()), "--scheme", str(small_scheme_path))
    edited = tmp_path / "edited.toml"
    edited.write_text(small_scheme_path.read_text().replace("Tobacco use.", "Tobacco and vaping."))
    again = StubProvider(answer())
    assert tag(variables_path, tmp_path, again, "--scheme", str(edited)) == 0
    assert len(sent_names(again)) == 59


def test_current_tags_are_skipped_unless_retag(tmp_path, variables_path, capsys):
    tag(variables_path, tmp_path, StubProvider(answer()))
    capsys.readouterr()
    again = StubProvider(answer())
    assert tag(variables_path, tmp_path, again) == 0
    assert again.calls == []
    assert "60 already tagged, 0 to do" in capsys.readouterr().err
    retag = StubProvider(answer())
    assert tag(variables_path, tmp_path, retag, "--retag") == 0
    assert len(sent_names(retag)) == 59


def test_files_limits_the_run(tmp_path, variables_path):
    stub = StubProvider(answer())
    assert tag(variables_path, tmp_path, stub, "--files", "beta") == 0
    assert {r["file"] for r in records(tmp_path)} == {"beta"}
    assert len(sent_names(stub)) == 20


def test_limit_caps_the_run(tmp_path, variables_path):
    stub = StubProvider(answer())
    assert tag(variables_path, tmp_path, stub, "--limit", "5") == 0
    assert len(records(tmp_path)) == 5


def test_a_live_lock_exits_4_and_sends_nothing(tmp_path, variables_path, capsys):
    import os

    tmp_path.mkdir(exist_ok=True)
    (tmp_path / ".lock").write_text(str(os.getpid()))
    stub = StubProvider(answer())
    assert tag(variables_path, tmp_path, stub) == 4
    assert "another run" in capsys.readouterr().err
    assert stub.calls == [] and stub.checked == 0


def test_a_finished_run_writes_run_json(tmp_path, variables_path):
    tag(variables_path, tmp_path, StubProvider(answer()), "--batch-size", "10")
    run = json.loads((tmp_path / "run.json").read_text())
    assert run["status"] == "finished"
    assert run["counts"]["total"] == 60 and run["counts"]["tagged"] == 60
    assert run["counts"]["requests"] == 6
    assert run["settings"]["batch_size"] == 10 and run["settings"]["model"] == "gpt-oss:20b"
    assert run["failed"] == []
    assert "api_key" not in json.dumps(run).lower()


# --- The scheme commands (US3) -----------------------------------------------------------


def test_check_scheme_summarises_the_bundled_scheme(capsys):
    assert main(["check-scheme"]) == 0
    out = capsys.readouterr().out
    assert "15 domains, 107 topics" in out and "hash" in out


def test_check_scheme_lists_every_mistake(tmp_path, small_scheme_path, capsys):
    text = small_scheme_path.read_text()
    text = text.replace('id = "alcohol"', 'id = "smoking"')  # duplicate id
    text = text.replace('id = "gender"', 'id = "Gender"')  # bad id
    text = text.replace('description = "Tobacco use."\n', "")  # missing description
    text += '\n[[domains]]\nid = "empty"\nlabel = "Empty"\ndescription = "None."\ntopics = []\n'
    bad = tmp_path / "bad.toml"
    bad.write_text(text)
    assert main(["check-scheme", str(bad)]) == 2
    err = capsys.readouterr().err
    for where in (
        "domains[1].topics[1].id",
        "domains[0].topics[1].id",
        "domains[1].topics[0].description",
        "domains[3].topics",
    ):
        assert where in err, err


def test_init_scheme_copies_the_bundled_scheme(tmp_path, capsys):
    target = tmp_path / "mine.toml"
    assert main(["init-scheme", str(target)]) == 0
    assert "CLOSER topics" in target.read_text()
    assert main(["check-scheme", str(target)]) == 0
    assert main(["init-scheme", str(target)]) == 2  # never overwrites
    assert "already exists" in capsys.readouterr().err


def test_edits_reach_the_prompt(tmp_path, variables_path, capsys):
    mine = tmp_path / "mine.toml"
    main(["init-scheme", str(mine)])
    text = mine.read_text().replace(
        "You are classifying variables", "You are carefully classifying variables"
    )
    mine.write_text(text.replace("Tobacco", "Tobacco, snuff", 1))
    capsys.readouterr()
    stub = StubProvider(answer())
    assert tag(variables_path, tmp_path / "out", stub, "--scheme", str(mine), "--dry-run") == 0
    out = capsys.readouterr().out
    assert "You are carefully classifying variables" in out and "Tobacco, snuff" in out


def test_tag_refuses_a_broken_scheme_before_any_request(
    tmp_path, variables_path, small_scheme_path, capsys
):
    bad = tmp_path / "bad.toml"
    bad.write_text(small_scheme_path.read_text().replace('id = "alcohol"', 'id = "smoking"'))
    stub = StubProvider(answer())
    assert tag(variables_path, tmp_path / "out", stub, "--scheme", str(bad)) == 2
    assert "smoking" in capsys.readouterr().err
    assert stub.calls == [] and stub.checked == 0
