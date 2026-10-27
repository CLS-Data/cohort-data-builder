import json

from conftest import StubProvider
from topic_tagger.providers import ProviderError
from topic_tagger.reply import ReplyError
from topic_tagger.runner import Runner, Settings
from topic_tagger.store import TagStore
from topic_tagger.variables import read_variables


def ids_in(messages):
    return [json.loads(x)["id"] for x in messages[1]["content"].splitlines() if x.startswith("{")]


def answer(topic="other", conf=0.4, skip=()):
    """A stand-in model that tags every variable it is sent, except names in ``skip``."""

    def reply(messages, schema):
        rows = [json.loads(x) for x in messages[1]["content"].splitlines() if x.startswith("{")]
        return json.dumps(
            {
                "variables": [
                    {"id": r["id"], "topics": [{"topic": topic, "confidence": conf}]}
                    for r in rows
                    if r["name"] not in skip
                ]
            }
        )

    return reply


def run(tmp_path, scheme, provider, variables, clock, **kw):
    events = []
    settings = Settings(
        batch_size=kw.pop("batch_size", 20),
        workers=kw.pop("workers", 2),
        retries=kw.pop("retries", 2),
        model="stub:test",
    )
    runner = Runner(
        scheme,
        provider,
        TagStore(tmp_path),
        settings,
        clock,
        on_event=lambda kind, data: events.append((kind, data)),
    )
    result = runner.run(variables)
    records = [json.loads(x) for x in (tmp_path / "tags.jsonl").read_text().splitlines()]
    return result, records, events


def test_batches_and_tags_every_variable(tmp_path, small_scheme, variables_path, clock):
    variables = read_variables(variables_path)
    stub = StubProvider(answer())
    result, records, _ = run(tmp_path, small_scheme, stub, variables, clock)
    assert len(stub.calls) == 3  # 59 to send, in batches of 20
    assert sorted(len(ids_in(m)) for m, _ in stub.calls) == [19, 20, 20]
    assert {(r["file"], r["variable"]) for r in records} == {
        (v.file, v.variable) for v in variables
    }
    assert result.tagged == 60 and result.failed == []


def test_the_identifier_is_tagged_by_rule(tmp_path, small_scheme, variables_path, clock):
    stub = StubProvider(answer())
    _, records, _ = run(tmp_path, small_scheme, stub, read_variables(variables_path), clock)
    (pid,) = [r for r in records if r["variable"] == "PID"]
    assert pid["topics"] == [["identifiers", 1.0]] and pid["model"] == "rule"
    sent = [
        json.loads(x)["name"]
        for m, _ in stub.calls
        for x in m[1]["content"].splitlines()
        if x.startswith("{")
    ]
    assert "PID" not in sent


def test_a_failing_batch_is_retried(tmp_path, small_scheme, variables_path, clock):
    variables = read_variables(variables_path)[1:6]
    failures = [ReplyError("bad reply"), ProviderError("timed out")]

    def reply(messages, schema):
        if failures:
            raise failures.pop(0)
        return answer()(messages, schema)

    stub = StubProvider(reply)
    result, records, events = run(tmp_path, small_scheme, stub, variables, clock)
    assert len(stub.calls) == 3
    assert len(records) == 5 and result.retries == 2
    assert [k for k, _ in events].count("retry") == 2


def test_after_the_retries_variables_go_one_at_a_time(
    tmp_path, small_scheme, variables_path, clock
):
    variables = read_variables(variables_path)[1:5]  # 4 variables, one batch

    def reply(messages, schema):
        if len(ids_in(messages)) > 1:
            raise ReplyError("the whole batch fails")
        if json.loads(messages[1]["content"].splitlines()[-1])["name"] == variables[2].variable:
            raise ReplyError("this one fails on its own too")
        return answer()(messages, schema)

    stub = StubProvider(reply)
    result, records, events = run(tmp_path, small_scheme, stub, variables, clock, retries=2)
    assert len(stub.calls) == 3 + 4  # batch + 2 retries, then each variable once
    assert len(records) == 3
    assert result.failed == [variables[2].key]
    assert ("failed", {"key": variables[2].key}) in events
    assert result.singles == 4


def test_variables_left_out_of_a_reply_are_sent_alone(
    tmp_path, small_scheme, variables_path, clock
):
    variables = read_variables(variables_path)[1:5]
    stub = StubProvider(answer(skip={variables[1].variable}))
    _, records, _ = run(tmp_path, small_scheme, stub, variables, clock)
    # the batch, then the skipped one alone; the stub skips it again, so it fails
    assert len(stub.calls) == 2
    assert ids_in(stub.calls[1][0]) == [0]
    assert len(records) == 3


def test_an_unlabelled_variable_gets_what_the_model_says(
    tmp_path, small_scheme, variables_path, clock
):
    variables = [v for v in read_variables(variables_path) if v.label is None]
    assert len(variables) == 1
    _, records, _ = run(
        tmp_path, small_scheme, StubProvider(answer("other", 0.2)), variables, clock
    )
    assert records[0]["topics"] == [["other", 0.2]]


def test_records_carry_the_scheme_hash_and_model(tmp_path, small_scheme, variables_path, clock):
    variables = read_variables(variables_path)[1:3]
    _, records, events = run(tmp_path, small_scheme, StubProvider(answer()), variables, clock)
    assert {r["scheme"] for r in records} == {small_scheme.hash}
    assert {r["model"] for r in records} == {"stub:test"}
    done = [d for k, d in events if k == "batch_done"]
    assert sum(d["n"] for d in done) == 2
    assert done[0]["tags"] == [[("other", 0.4)], [("other", 0.4)]]


def test_never_more_requests_in_flight_than_workers(tmp_path, small_scheme, variables_path, clock):
    import time

    def slow(messages, schema):
        time.sleep(0.02)
        return answer()(messages, schema)

    stub = StubProvider(slow)
    run(
        tmp_path, small_scheme, stub, read_variables(variables_path), clock, batch_size=5, workers=2
    )
    assert stub.max_in_flight == 2
