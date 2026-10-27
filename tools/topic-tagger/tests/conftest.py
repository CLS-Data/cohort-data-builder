"""Shared test helpers: a stand-in model, a fake clock and the fixture paths."""

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
