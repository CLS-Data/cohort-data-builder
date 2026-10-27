"""Speed checks. Timings depend on the machine, so these are left out of the default run.

Run them with ``uv run pytest -m slow``.
"""

import json
import time

import pytest

from conftest import StubProvider
from test_runner import answer
from topic_tagger.runner import Runner, Settings
from topic_tagger.store import TagStore
from topic_tagger.variables import Variable

pytestmark = pytest.mark.slow


def test_loading_35000_records_takes_under_2_seconds(tmp_path):
    line = {
        "topics": [["smoking", 0.9], ["alcohol", 0.4]],
        "scheme": "abc",
        "model": "m",
        "tagged": "2027-01-15T08:00:00Z",
    }
    text = "\n".join(
        json.dumps({"file": f"f{i // 1000}", "variable": f"v{i}", **line}) for i in range(35_000)
    )
    (tmp_path / "tags.jsonl").write_text(text + "\n", encoding="utf-8")
    store = TagStore(tmp_path)
    start = time.perf_counter()
    store.load()
    assert len(store.records) == 35_000
    assert time.perf_counter() - start < 2


def test_the_tools_own_overhead_for_1000_variables_is_under_1_second(tmp_path, small_scheme, clock):
    variables = [Variable("f", f"v{i}", f"Label {i}", (("1", "Yes"),)) for i in range(1000)]
    settings = Settings(batch_size=20, workers=2, retries=2, model="stub:test")
    runner = Runner(small_scheme, StubProvider(answer()), TagStore(tmp_path), settings, clock)
    start = time.perf_counter()
    result = runner.run(variables)
    assert result.tagged == 1000
    assert time.perf_counter() - start < 1
