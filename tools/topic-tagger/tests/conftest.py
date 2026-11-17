"""Shared test helpers: stand-in models, a fake clock and the fixture paths."""

import json
import threading
from collections.abc import Callable
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


class StubProvider:
    """A stand-in for a model host, so no test needs Ollama or the network.

    Give it either a function ``(messages, schema) -> str`` or a list of replies, each a
    string to return or an exception to raise, used in order. Every call is recorded.
    """

    def __init__(
        self,
        reply: Callable | list | None = None,
        *,
        remote: bool = False,
        check_error: Exception | None = None,
    ):
        self._reply = reply
        self._queue = list(reply) if isinstance(reply, list) else None
        self.remote = remote
        self.check_error = check_error
        self.calls: list[tuple[list[dict], dict]] = []
        self.checked = 0
        self.in_flight = 0
        self.max_in_flight = 0
        self._lock = threading.Lock()

    def check(self) -> None:
        self.checked += 1
        if self.check_error:
            raise self.check_error

    def is_remote(self) -> bool:
        return self.remote

    def complete(self, messages: list[dict], schema: dict) -> str:
        with self._lock:
            self.calls.append((messages, schema))
            self.in_flight += 1
            self.max_in_flight = max(self.max_in_flight, self.in_flight)
            answer = self._queue.pop(0) if self._queue is not None else None
        try:
            if self._queue is None:
                answer = self._reply(messages, schema)
            if isinstance(answer, BaseException):
                raise answer
            return answer
        finally:
            with self._lock:
                self.in_flight -= 1


def schema_options(schema: dict) -> list[str]:
    """The option ids a reply schema allows, in order."""
    topic = schema["$defs"]["TopicTag"]["properties"]["topic"]
    return list(topic["enum"]) if "enum" in topic else [topic["const"]]


def first_option(messages: list[dict], schema: dict) -> str:
    """A chat reply giving every variable sent the schema's first option, at 0.8.

    It depends only on the request, so the same request always gets the same reply.
    """
    first = schema_options(schema)[0]
    rows = [json.loads(x) for x in messages[1]["content"].split("\n") if x.startswith("{")]
    return json.dumps(
        {
            "variables": [
                {"id": r["id"], "topics": [{"topic": first, "confidence": 0.8}]} for r in rows
            ]
        }
    )


class FakeDecisionModel:
    """A decision-model object (``check``, ``is_remote``, ``decide``), with no host.

    Args:
        probability: ``(state, option) -> float``; by default 0.9 for the first option and
            the rest shared equally.
        remote: What ``is_remote`` says.
        refuse_over: Refuse (``OptionLimitError``) a question with more options than this.
        fail_for: Labels whose every question raises ``ProviderError("no answer")``.
        check_error: Raised by ``check``.
    """

    def __init__(
        self, probability=None, *, remote=False, refuse_over=None, fail_for=(), check_error=None
    ):
        self.probability = probability
        self.remote = remote
        self.refuse_over = refuse_over
        self.fail_for = set(fail_for)
        self.check_error = check_error
        self.calls: list[tuple[dict, str, dict]] = []
        self.checked = 0
        self._lock = threading.Lock()

    def check(self) -> None:
        self.checked += 1
        if self.check_error:
            raise self.check_error

    def is_remote(self) -> bool:
        return self.remote

    def decide(self, state: dict, instructions: str, options: dict) -> dict[str, float]:
        from topic_tagger.providers import OptionLimitError, ProviderError

        with self._lock:
            self.calls.append((state, instructions, options))
        if self.refuse_over is not None and len(options) > self.refuse_over:
            raise OptionLimitError(400, "too many options", len(options))
        if state["label"] in self.fail_for:
            raise ProviderError("no answer")
        ids = list(options)
        if self.probability:
            return {o: self.probability(state, o) for o in ids}
        rest = 0.1 / (len(ids) - 1) if len(ids) > 1 else 0.0
        return {o: (0.9 if i == 0 else rest) for i, o in enumerate(ids)}


class FakeClock:
    """A clock the tests move by hand, so nothing depends on the real time."""

    def __init__(self, start: float = 1_800_000_000.0):
        self.t = start

    def now(self) -> float:
        return self.t

    def advance(self, seconds: float) -> None:
        self.t += seconds


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES


@pytest.fixture
def variables_path() -> Path:
    return FIXTURES / "variables.jsonl"


@pytest.fixture
def small_scheme_path() -> Path:
    return FIXTURES / "scheme_small.toml"


@pytest.fixture
def bundled_scheme_path(tmp_path) -> Path:
    from topic_tagger.scheme import bundled_scheme_text

    path = tmp_path / "bundled.toml"
    path.write_text(bundled_scheme_text(), encoding="utf-8")
    return path


@pytest.fixture
def small_scheme(small_scheme_path):
    from topic_tagger.scheme import load_scheme

    return load_scheme(small_scheme_path)


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def fake_decision() -> FakeDecisionModel:
    return FakeDecisionModel()


@pytest.fixture
def fake_chat() -> StubProvider:
    return StubProvider(first_option)


@pytest.fixture
def scheme_run_path() -> Path:
    return FIXTURES / "scheme_run.toml"
