import json

from topic_tagger.store import TagStore, make_record
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
