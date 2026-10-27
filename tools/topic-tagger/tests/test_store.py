import json
import os
import subprocess
import sys

import pytest

from topic_tagger.store import LockedError, StaleLockError, TagStore, make_record
from topic_tagger.variables import Variable


def test_creates_the_folder_and_writes_the_scheme(tmp_path, small_scheme):
    out = tmp_path / "a" / "b"
    store = TagStore(out)
    store.write_scheme(small_scheme)
    assert json.loads((out / "scheme.json").read_text()) == small_scheme.to_json()


def test_make_record_has_the_documented_fields(clock):
    var = Variable("alpha", "A01", "x")
    rec = make_record(var, [("smoking", 0.9)], "abc123abc123", "ollama:m", clock.now())
    assert rec == {
        "file": "alpha",
        "variable": "A01",
        "topics": [["smoking", 0.9]],
        "scheme": "abc123abc123",
        "model": "ollama:m",
        "tagged": "2027-01-15T08:00:00Z",
    }


def test_append_writes_one_line_per_record_at_once(tmp_path, clock):
    store = TagStore(tmp_path)
    recs = [
        make_record(Variable("f", v), [("age", 0.5)], "h", "m", clock.now()) for v in ("a", "b")
    ]
    store.append(recs)
    # Readable straight away, before the store is closed: each batch is flushed.
    lines = (tmp_path / "tags.jsonl").read_text().splitlines()
    assert [json.loads(x)["variable"] for x in lines] == ["a", "b"]
    store.append(recs[:1])
    assert len((tmp_path / "tags.jsonl").read_text().splitlines()) == 3


# --- Resuming (US2) ---------------------------------------------------------------------


def rec(variable, scheme="h1", topics=(("age", 0.5),), file="f"):
    return {
        "file": file,
        "variable": variable,
        "topics": [list(t) for t in topics],
        "scheme": scheme,
        "model": "m",
        "tagged": "2027-01-15T08:00:00Z",
    }


def test_load_reads_records_and_the_last_line_wins(tmp_path):
    store = TagStore(tmp_path)
    store.append([rec("a"), rec("b"), rec("a", scheme="h2")])
    fresh = TagStore(tmp_path)
    fresh.load()
    assert fresh.state("f/a", "h2") == "current"
    assert fresh.state("f/a", "h1") == "stale"
    assert fresh.state("f/b", "h1") == "current"
    assert fresh.state("f/c", "h1") == "missing"


def test_a_cut_off_last_line_is_ignored(tmp_path):
    store = TagStore(tmp_path)
    store.append([rec("a"), rec("b")])
    with (tmp_path / "tags.jsonl").open("a") as fh:
        fh.write('{"file": "f", "variable": "c", "topi')
    fresh = TagStore(tmp_path)
    fresh.load()
    assert fresh.state("f/b", "h1") == "current"
    assert fresh.state("f/c", "h1") == "missing"


def test_compact_sorts_one_line_per_variable(tmp_path):
    store = TagStore(tmp_path)
    store.append([rec("b", file="g"), rec("z"), rec("a"), rec("z", scheme="h2")])
    store.load()
    store.compact()
    lines = [json.loads(x) for x in (tmp_path / "tags.jsonl").read_text().splitlines()]
    assert [(r["file"], r["variable"], r["scheme"]) for r in lines] == [
        ("f", "a", "h1"),
        ("f", "z", "h2"),
        ("g", "b", "h1"),
    ]
    assert not list(tmp_path.glob("*.tmp"))


def test_a_lock_refuses_a_second_run_while_the_first_is_alive(tmp_path):
    store = TagStore(tmp_path)
    store.lock()
    assert (tmp_path / ".lock").read_text().strip() == str(os.getpid())
    with pytest.raises(LockedError):
        TagStore(tmp_path).lock()
    store.unlock()
    assert not (tmp_path / ".lock").exists()
    TagStore(tmp_path).lock()  # free again


@pytest.mark.skipif(sys.platform == "win32", reason="a lock is always treated as live there")
def test_a_lock_left_by_a_run_that_ended_needs_force(tmp_path):
    ended = subprocess.run(
        [sys.executable, "-c", "import os; print(os.getpid())"], capture_output=True, text=True
    )
    (tmp_path / ".lock").write_text(ended.stdout)
    with pytest.raises(StaleLockError):
        TagStore(tmp_path).lock()
    TagStore(tmp_path).lock(force=True)
    assert (tmp_path / ".lock").read_text().strip() == str(os.getpid())
