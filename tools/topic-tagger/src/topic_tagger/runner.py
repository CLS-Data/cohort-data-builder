"""Tagging a list of variables: batches, requests in parallel, and the retry ladder.

Each batch is sent; a failure (a timeout, a reply that fails the checks) is retried up to
``retries`` times; after that, and for any variable the reply left out, variables are sent
one at a time, once each; any still failing are recorded as failed.
"""

from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field

from topic_tagger.prompt import build_messages, reply_schema
from topic_tagger.providers import Provider, ProviderError
from topic_tagger.reply import ReplyError, parse_reply
from topic_tagger.scheme import Scheme
from topic_tagger.store import TagStore, make_record
from topic_tagger.variables import Variable

Tags = list[tuple[str, float]]


@dataclass
class Settings:
    """How a run sends requests.

    Attributes:
        batch_size: Variables per request.
        workers: Requests in flight at once.
        retries: Retries of a failed batch before its variables go one at a time.
        model: ``provider:model``, stored with each record.
    """

    batch_size: int = 20
    workers: int = 2
    retries: int = 2
    model: str = "ollama:gpt-oss:20b"


@dataclass
class RunResult:
    """What a run did."""

    tagged: int = 0
    failed: list[str] = field(default_factory=list)
    requests: int = 0
    retries: int = 0
    singles: int = 0


@dataclass
class _Outcome:
    tagged: list[tuple[Variable, Tags]] = field(default_factory=list)
    failed: list[Variable] = field(default_factory=list)
    requests: int = 0
    retries: int = 0
    singles: int = 0


class Runner:
    """Tags variables and stores the results.

    Args:
        scheme: The topic scheme.
        provider: The model host.
        store: Where records go.
        settings: Batch size, workers, retries and model label.
        clock: Gives the time stored with each record.
        on_event: Called in the main thread as ``on_event(kind, data)`` with ``retry``,
            ``batch_done`` (``n`` and each variable's ``tags``) and ``failed`` (``key``).
    """

    def __init__(
        self,
        scheme: Scheme,
        provider: Provider,
        store: TagStore,
        settings: Settings,
        clock,
        on_event: Callable[[str, dict], None] = lambda kind, data: None,
    ):
        self.scheme = scheme
        self.provider = provider
        self.store = store
        self.settings = settings
        self.clock = clock
        self.on_event = on_event
        self._schema = reply_schema(scheme)

    def run(self, variables: list[Variable]) -> RunResult:
        """Tag the variables, storing each batch's records as it completes."""
        result = RunResult()
        rule = [v for v in variables if v.identifier]
        rest = [v for v in variables if not v.identifier]
        if rule:
            tags = [(self.scheme.identifier_topic, 1.0)]
            self._store(result, _Outcome(tagged=[(v, tags) for v in rule]), model="rule")

        size = self.settings.batch_size
        batches = [rest[i : i + size] for i in range(0, len(rest), size)]
        with ThreadPoolExecutor(max_workers=self.settings.workers) as pool:
            futures = [pool.submit(self._batch, b) for b in batches]
            # Results are stored here, in the main thread, as each batch completes.
            for future in as_completed(futures):
                self._store(result, future.result(), model=self.settings.model)
        return result

    def _store(self, result: RunResult, out: _Outcome, model: str) -> None:
        now = self.clock.now()
        h = self.scheme.hash
        self.store.append([make_record(v, tags, h, model, now) for v, tags in out.tagged])
        for _ in range(out.retries):
            self.on_event("retry", {})
        if out.tagged:
            self.on_event("batch_done", {"n": len(out.tagged), "tags": [t for _, t in out.tagged]})
        for v in out.failed:
            self.on_event("failed", {"key": v.key})
        result.tagged += len(out.tagged)
        result.failed += [v.key for v in out.failed]
        result.requests += out.requests
        result.retries += out.retries
        result.singles += out.singles

    def _batch(self, batch: list[Variable]) -> _Outcome:
        out = _Outcome()
        got = None
        for attempt in range(self.settings.retries + 1):
            out.requests += 1
            try:
                got = self._ask(batch)
                break
            except (ReplyError, ProviderError):
                if attempt < self.settings.retries:
                    out.retries += 1
        alone = batch if got is None else [v for i, v in enumerate(batch) if i not in got]
        if got is not None:
            out.tagged += [(v, got[i]) for i, v in enumerate(batch) if i in got]
        for v in alone:
            out.singles += 1
            out.requests += 1
            try:
                one = self._ask([v])
            except (ReplyError, ProviderError):
                one = {}
            if 0 in one:
                out.tagged.append((v, one[0]))
            else:
                out.failed.append(v)
        return out

    def _ask(self, batch: list[Variable]) -> dict[int, Tags]:
        text = self.provider.complete(build_messages(self.scheme, batch), self._schema)
        return parse_reply(text, self.scheme, len(batch))
