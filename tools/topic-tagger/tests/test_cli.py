import json
import re

import pytest

from conftest import FIXTURES, StubProvider
from test_runner import answer
from topic_tagger.cli import main
from topic_tagger.providers import ProviderError

SMALL = str(FIXTURES / "scheme_small.toml")


def tag(variables_path, out, stub, *extra, clock=None):
    scheme = [] if "--scheme" in extra else ["--scheme", SMALL]
    argv = ["tag", str(variables_path), "--out", str(out), *scheme, *extra]
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


def test_a_scheme_must_be_chosen(tmp_path, variables_path, capsys):
    stub = StubProvider(answer())
    argv = ["tag", str(variables_path), "--out", str(tmp_path / "out")]
    with pytest.raises(SystemExit) as e:
        main(argv, provider_factory=lambda args: stub)
    assert e.value.code == 2 and "--scheme" in capsys.readouterr().err
    assert stub.calls == [] and not (tmp_path / "out").exists()


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
    argv = ["tag", str(variables_path), "--out", str(tmp_path), "--scheme", SMALL]
    argv += ["--model", "m1", "--timeout", "7"]
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
        "--group-by",
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
    assert len(sent_names(second)) == 60 - 40  # only what the first run did not tag
    assert topics_by_key(out) == topics_by_key(whole)
    assert len(records(out)) == 60  # compacted: one line per variable


def test_a_scheme_change_redoes_everything(tmp_path, variables_path, small_scheme_path):
    tag(variables_path, tmp_path, StubProvider(answer()), "--scheme", str(small_scheme_path))
    edited = tmp_path / "edited.toml"
    edited.write_text(small_scheme_path.read_text().replace("Tobacco use.", "Tobacco and vaping."))
    again = StubProvider(answer())
    assert tag(variables_path, tmp_path, again, "--scheme", str(edited)) == 0
    assert len(sent_names(again)) == 60


def test_current_tags_are_skipped_unless_retag(tmp_path, variables_path, capsys):
    tag(variables_path, tmp_path, StubProvider(answer()))
    capsys.readouterr()
    again = StubProvider(answer())
    assert tag(variables_path, tmp_path, again) == 0
    assert again.calls == []
    assert "60 already tagged, 0 to do" in capsys.readouterr().err
    retag = StubProvider(answer())
    assert tag(variables_path, tmp_path, retag, "--retag") == 0
    assert len(sent_names(retag)) == 60


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
    assert run["settings"]["group_by"] == "sweep" and run["settings"]["scheme"] == SMALL
    assert run["failed"] == []
    assert "api_key" not in json.dumps(run).lower()


# --- The scheme commands (US3) -----------------------------------------------------------


def test_group_by_is_recorded(tmp_path, variables_path):
    tag(variables_path, tmp_path, StubProvider(answer()), "--group-by", "questionnaire")
    assert (
        json.loads((tmp_path / "run.json").read_text())["settings"]["group_by"] == "questionnaire"
    )


def test_check_scheme_needs_a_file(capsys):
    with pytest.raises(SystemExit) as e:
        main(["check-scheme"])
    assert e.value.code == 2


def test_check_scheme_summarises_a_scheme(bundled_scheme_path, capsys):
    assert main(["check-scheme", str(bundled_scheme_path)]) == 0
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


# --- Watching a run (US4) ----------------------------------------------------------------

PLAIN = re.compile(r"^\[\d\d:\d\d:\d\d\] \d+/\d+ \(\d+%\) \d+/min eta \S+ failed \d+ retries \d+$")


@pytest.mark.parametrize("extra", [(), ("--plain",)])
def test_without_a_terminal_the_run_writes_plain_lines(tmp_path, variables_path, capsys, extra):
    assert tag(variables_path, tmp_path, StubProvider(answer()), *extra) == 0
    err = capsys.readouterr().err
    assert "\x1b[" not in err
    lines = [x for x in err.splitlines() if PLAIN.match(x)]
    assert lines and lines[-1].split()[1] == "60/60"


def test_the_summary_matches_the_stored_tags(tmp_path, variables_path, capsys):
    stub = StubProvider(
        answer(skip=("A05HEAL",)),
    )
    tag(variables_path, tmp_path, stub, "--retries", "0")
    out = capsys.readouterr().out
    n = len(records(tmp_path))
    assert f"Tagged {n} of 60" in out and n == 59


# --- The statistics and the report (US5) -------------------------------------------------


def test_a_finished_run_writes_stats_a_report_and_a_summary(tmp_path, variables_path, capsys):
    assert tag(variables_path, tmp_path, StubProvider(answer("smoking", 0.7))) == 0
    run = json.loads((tmp_path / "run.json").read_text())
    assert run["stats"]["per_topic"]["smoking"] == 60
    assert run["timeline"] and run["settings"]["variables"] == str(variables_path)
    html = (tmp_path / "report.html").read_text()
    assert "<svg" in html
    out = capsys.readouterr().out
    for part in (
        "Tagged 60 of 60",
        "0 failed",
        "Run time",
        "/min",
        "Mean topics per variable: 1.0",
        "Only below 50%: 0%",
        "Leading topics",
        "Smoking 60",
        "Unused topics: 7 of 8",
        "report.html",
    ):
        assert part in out, out


def test_the_summary_lists_at_most_ten_files_and_groups(tmp_path, capsys):
    # 15 files, file i holding i + 1 variables, each in its own group.
    lines = [
        json.dumps({"file": f"f{i:02d}", "variable": f"v{j}", "group": f"g{i:02d}"})
        for i in range(15)
        for j in range(i + 1)
    ]
    path = tmp_path / "v.jsonl"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    assert tag(path, tmp_path / "out", StubProvider(answer()), "--group-by", "group") == 0
    out = capsys.readouterr().out
    by_file = next(x for x in out.splitlines() if x.startswith("By file: "))
    by_group = next(x for x in out.splitlines() if x.startswith("By group: "))
    # Largest first, then a count of the rest.
    assert by_file == "By file: " + ", ".join(f"f{i:02d} {i + 1}" for i in range(14, 4, -1)) + (
        ", and 5 more"
    )
    assert by_group.startswith("By group: g14 15, g13 14,") and by_group.endswith(", and 5 more")


def test_a_stopped_run_writes_the_report_too(tmp_path, variables_path):
    box = []

    def stop_first(messages, schema):
        box[0].request_stop()
        return answer()(messages, schema)

    stub = StubProvider(stop_first)
    argv = ["tag", str(variables_path), "--out", str(tmp_path), "--scheme", SMALL, "--workers", "1"]
    assert main(argv, provider_factory=lambda a: stub, runner_created=box.append) == 130
    assert json.loads((tmp_path / "run.json").read_text())["status"] == "stopped"
    assert (tmp_path / "report.html").exists()


def test_report_rebuilds_and_can_regroup(tmp_path, variables_path, capsys):
    tag(variables_path, tmp_path, StubProvider(answer()))
    (tmp_path / "report.html").unlink()
    assert main(["report", str(tmp_path)]) == 0
    assert (tmp_path / "report.html").exists()
    assert main(["report", str(tmp_path), "--group-by", "file_group"]) == 0
    stats = json.loads((tmp_path / "run.json").read_text())["stats"]
    assert stats["group_by"] == "file_group" and stats["per_group"] == {}


def test_report_needs_a_finished_folder(tmp_path, capsys):
    assert main(["report", str(tmp_path)]) == 2
    assert "run.json" in capsys.readouterr().err


# --- Tiered tagging (feature 004) ---------------------------------------------------


def test_method_defaults_to_flat_and_tiered_tags_every_variable(tmp_path, variables_path):
    from test_runner import tiered_answer

    stub = StubProvider(answer("smoking", 0.7))
    assert tag(variables_path, tmp_path / "flat", stub) == 0
    assert len(stub.calls) == 3  # 60 variables, batches of 20, one request each
    stub = StubProvider(tiered_answer)
    assert tag(variables_path, tmp_path / "tiered", stub, "--method", "tiered") == 0
    assert len(records(tmp_path / "tiered")) == 60
    assert len(stub.calls) == 6  # tier 1 and one area per batch


@pytest.mark.parametrize(
    "extra",
    [
        ("--method", "tiered", "--descend-at", "1.5"),
        ("--method", "tiered", "--max-areas", "-1"),
        ("--descend-at", "0.5"),
        ("--max-areas", "2"),
    ],
)
def test_tiered_settings_are_checked(tmp_path, variables_path, capsys, extra):
    stub = StubProvider(answer())
    assert tag(variables_path, tmp_path / "out", stub, *extra) == 2
    assert stub.calls == []
    assert capsys.readouterr().err


def test_max_areas_zero_means_no_cap(tmp_path, variables_path):
    from test_runner import tiered_answer

    stub = StubProvider(tiered_answer)
    assert tag(variables_path, tmp_path / "o", stub, "--method", "tiered", "--max-areas", "0") == 0


def test_tiered_dry_run_prints_tier_1_and_a_tier_2_example(tmp_path, variables_path, capsys):
    stub = StubProvider(answer(), check_error=ProviderError("not running"))
    assert tag(variables_path, tmp_path / "out", stub, "--method", "tiered", "--dry-run") == 0
    out = capsys.readouterr().out
    tier1, tier2 = out.split("--- tier 2 example (Demographics) ---")
    assert "- demographics: Demographics" in tier1 and "Includes: Age" in tier1
    assert "- age: Age" in tier2 and "- smoking:" not in tier2
    assert '"name": "A01AGE"' in tier1 and '"name": "A01AGE"' in tier2
    assert stub.calls == [] and stub.checked == 0


def test_help_lists_the_tiered_options(capsys):
    with pytest.raises(SystemExit):
        main(["tag", "--help"])
    out = capsys.readouterr().out
    for opt in ("--method", "--descend-at", "--max-areas"):
        assert opt in out


class DecisionStub:
    """A stand-in decision host for CLI runs: every question gets ``probability``."""

    def __init__(self, probability=lambda state, q: 0.6, remote=False):
        self.probability = probability
        self.remote = remote
        self.calls = []

    def check(self):
        pass

    def is_remote(self):
        return self.remote

    def requests_for(self, questions):
        return -(-questions // 64)

    def decide(self, state, questions):
        self.calls.append((state, questions))
        return {q: self.probability(state, q) for q in questions}


def clef(*extra):
    return ("--provider", "ollama-decision", "--model", "clef:cloud", *extra)


@pytest.mark.parametrize("method", ["flat", "tiered"])
def test_clef_tags_the_fixture_flat_or_tiered(tmp_path, variables_path, small_scheme, method):
    stub = DecisionStub()
    assert tag(variables_path, tmp_path / "o", stub, *clef("--method", method)) == 0
    recs = records(tmp_path / "o")
    assert len(recs) == 60 and all(r["topics"] for r in recs)
    asked = {tuple(q) for _, q in stub.calls}
    if method == "flat":
        assert asked == {tuple(small_scheme.topic_ids)}
        assert len(stub.calls) == 60
    else:
        assert ("demographics", "health", "survey") in asked
        assert ("smoking", "alcohol", "physical_health") in asked


def test_a_chat_model_flat_still_uses_the_flat_prompt(tmp_path, variables_path):
    stub = StubProvider(answer("smoking", 0.7))
    assert tag(variables_path, tmp_path / "o", stub, "--method", "flat") == 0
    assert "smoking: Smoking — Tobacco use." in stub.calls[0][0][0]["content"]


def test_keep_at_needs_the_decision_provider(tmp_path, variables_path, capsys):
    stub = StubProvider(answer())
    assert tag(variables_path, tmp_path / "o", stub, "--keep-at", "0.2") == 2
    assert "--keep-at" in capsys.readouterr().err and stub.calls == []


def test_keep_at_reaches_the_decider(tmp_path, variables_path):
    probs = {"smoking": 0.9, "alcohol": 0.25}
    stub = DecisionStub(lambda state, q: probs.get(q, 0.01) if q not in ("health",) else 0.9)
    tag(variables_path, tmp_path / "a", stub, *clef("--method", "tiered", "--keep-at", "0.2"))
    assert [t for t, _ in records(tmp_path / "a")[0]["topics"]] == ["smoking", "alcohol"]
    tag(variables_path, tmp_path / "b", stub, *clef("--method", "tiered"))
    assert [t for t, _ in records(tmp_path / "b")[0]["topics"]] == ["smoking"]


def test_a_cloud_decision_model_asks_before_sending(tmp_path, variables_path, capsys):
    argv = [
        "tag",
        str(variables_path),
        "--out",
        str(tmp_path / "o"),
        "--scheme",
        SMALL,
        *clef("--method", "tiered"),
    ]
    assert main(argv) == 2  # the real provider: clef:cloud is remote; no --yes, no terminal
    assert "leave this machine" in capsys.readouterr().err


def test_decision_dry_run_prints_the_request_bodies(tmp_path, variables_path, capsys):
    stub = DecisionStub()
    assert tag(variables_path, tmp_path / "o", stub, *clef("--method", "tiered", "--dry-run")) == 0
    out = capsys.readouterr().out
    first, second = out.split("--- tier 2 example (Demographics) ---")
    tier1, tier2 = json.loads(first), json.loads(second)
    assert tier1["model"] == "clef:cloud" and tier1["state"]["name"] == "PID"
    assert list(tier1["questions"]) == ["demographics", "health", "survey"]
    assert tier1["questions"]["health"]["type"] == "noul"
    assert list(tier2["questions"]) == ["age", "gender"]
    assert stub.calls == []


def run_json(out):
    return json.loads((out / "run.json").read_text())


def test_a_tiered_run_records_its_method_paths_and_requests_by_tier(
    tmp_path, variables_path, capsys
):
    from test_runner import tiered_answer

    out = tmp_path / "o"
    assert tag(variables_path, out, StubProvider(tiered_answer), "--method", "tiered") == 0
    run = run_json(out)
    assert run["settings"]["method"] == "tiered"
    assert run["settings"]["descend_at"] == 0.5 and run["settings"]["max_areas"] == 3
    assert run["counts"]["requests_by_tier"] == [3, 3]
    for r in records(out):
        assert r["method"] == "tiered" and r["path"] == [["health", 0.8]]
    text = capsys.readouterr().out
    assert "Requests by tier: 1: 3, 2: 3" in text
    assert "Areas followed per variable: 1.0" in text


def test_a_flat_run_records_one_tier(tmp_path, variables_path, capsys):
    out = tmp_path / "o"
    assert tag(variables_path, out, StubProvider(answer("smoking", 0.7))) == 0
    run = run_json(out)
    assert run["settings"]["method"] == "flat" and "descend_at" not in run["settings"]
    assert run["counts"]["requests_by_tier"] == [run["counts"]["requests"]]
    assert all(r["method"] == "flat" and "path" not in r for r in records(out))
    assert "Requests by tier" not in capsys.readouterr().out


def test_a_clef_run_records_keep_at(tmp_path, variables_path):
    tag(variables_path, tmp_path / "o", DecisionStub(), *clef("--method", "tiered"))
    assert run_json(tmp_path / "o")["settings"]["keep_at"] == 0.3


def test_switching_method_redoes_every_variable(tmp_path, variables_path, capsys):
    from test_runner import tiered_answer

    out = tmp_path / "o"
    tag(variables_path, out, StubProvider(answer("smoking", 0.7)))
    stub = StubProvider(tiered_answer)
    tag(variables_path, out, stub, "--method", "tiered")
    assert run_json(out)["counts"]["todo"] == 60 and stub.calls
    capsys.readouterr()
    stub = StubProvider(tiered_answer)
    tag(variables_path, out, stub, "--method", "tiered")
    assert "60 already tagged, 0 to do" in capsys.readouterr().err and not stub.calls
