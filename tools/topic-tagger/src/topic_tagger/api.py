"""Tagging from Python: text or variables in, tags out, in memory (feature 006).

The command line reads a ``variables.jsonl`` file and writes an output folder. This module
does the same tagging for code: it takes text, ``Variable`` objects or ``variables.jsonl``-style
dicts, and returns the tags. It writes no files and never prints, prompts or exits.
Problems are raised as exceptions.

Settings are resolved as on the command line: an argument given here, else the scheme's
``[run]`` table, else the default. Requests are made by the same ``Runner``, so batching,
retries, the tier walk and refusals behave exactly as they do there.

    from topic_tagger import tag
    results = tag(["Do you smoke?"], "my-scheme.toml")
    results[0].topics  # the leaf ids it was tagged with, strongest first
"""

from __future__ import annotations

import dataclasses
import os
from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass
from typing import Any, overload

from topic_tagger.clock import SystemClock
from topic_tagger.providers import ProviderError, get_provider
from topic_tagger.run_settings import DECISION, KEYS, settle
from topic_tagger.runner import Runner, Settings
from topic_tagger.scheme import Scheme, bundled_scheme_text, load_scheme, parse_scheme
from topic_tagger.tiered import DecisionDecider
from topic_tagger.variables import Variable, variable_from_dict

#: What an input may be: text, a variable, or one ``variables.jsonl`` line as a dict.
Input = str | Variable | dict

#: The model label stored when a provider object is given and nothing names its model.
CUSTOM_MODEL = "custom"


class RemoteModelError(ProviderError):
    """The model is in the cloud, and the caller has not allowed metadata to leave.

    Pass ``allow_remote=True`` to allow it: the equivalent of the command line's ``--yes``.
    """


@dataclass(frozen=True)
class Tag:
    """One topic given to an input.

    Attributes:
        topic: The leaf's id in the scheme.
        label: The leaf's label.
        confidence: From 0 to 1.
    """

    topic: str
    label: str
    confidence: float


@dataclass(frozen=True)
class Result:
    """What one input was tagged with.

    Attributes:
        input: What the caller passed, unchanged.
        tags: Its topics, strongest first; empty if it failed.
        path: Tiered tagging: the groups followed, as ``(id, confidence)``; None if flat.
        failed: True when no tags were obtained after the retries.
        error: For a failed input, the last error message of the call; otherwise empty.
        method: ``flat`` or ``tiered``.
        model: ``provider:model``, as stored by the command line.
        scheme_hash: The hash of the scheme that tagged it.
    """

    input: Any
    tags: list[Tag]
    path: list[tuple[str, float]] | None
    failed: bool
    error: str
    method: str
    model: str
    scheme_hash: str

    @property
    def topics(self) -> list[str]:
        """The topic ids, strongest first."""
        return [t.topic for t in self.tags]

    def to_dict(self) -> dict:
        """The result as a ``tags.jsonl`` record, without file, variable and time.

        Returns:
            ``topics``, ``scheme``, ``model``, ``method``, ``path`` (tiered only),
            ``failed`` and ``error``.
        """
        d = {
            "topics": [[t.topic, t.confidence] for t in self.tags],
            "scheme": self.scheme_hash,
            "model": self.model,
            "method": self.method,
        }
        if self.path is not None:
            d["path"] = [[g, c] for g, c in self.path]
        return {**d, "failed": self.failed, "error": self.error}


class Results(Sequence[Result]):
    """A call's results, in input order, with what the call used.

    Attributes:
        settings: The resolved ``provider``, ``model``, ``method``, ``descend_at``,
            ``max_follow`` and ``keep_at``.
        sources: Where each setting came from: ``call``, ``file`` or ``default``.
        notes: What the command line would have printed, such as a setting ignored.
        requests_by_tier: Requests sent at each tier.
        retries: Requests retried.
        scheme_name: The scheme's name.
        scheme_hash: The scheme's hash.
    """

    def __init__(
        self,
        results: list[Result],
        *,
        settings: dict,
        sources: dict,
        notes: list[str],
        scheme: Scheme,
        requests_by_tier: list[int] | None = None,
        retries: int = 0,
    ):
        self._results = results
        self.settings = settings
        self.sources = sources
        self.notes = notes
        self.requests_by_tier = requests_by_tier or []
        self.retries = retries
        self.scheme_name = scheme.name
        self.scheme_hash = scheme.hash

    @overload
    def __getitem__(self, i: int) -> Result: ...
    @overload
    def __getitem__(self, i: slice) -> list[Result]: ...
    def __getitem__(self, i):
        """The result at ``i`` (or a list, for a slice)."""
        return self._results[i]

    def __len__(self) -> int:
        """How many results: one per input."""
        return len(self._results)

    def __iter__(self) -> Iterator[Result]:
        """The results, in input order."""
        return iter(self._results)

    @property
    def failed(self) -> list[Result]:
        """The results that got no tags."""
        return [r for r in self._results if r.failed]

    def __repr__(self) -> str:
        """A short summary."""
        return f"<Results: {len(self)} inputs, {len(self.failed)} failed>"


class _MemorySink:
    """Keeps a run's records in memory, by input position."""

    def __init__(self) -> None:
        self.records: dict[int, dict] = {}

    def append(self, records: list[dict]) -> None:
        for r in records:
            self.records[int(r["file"])] = r


def _to_variable(i: int, item: Input) -> Variable:
    """The variable sent for input ``i``. Its ``file`` is the position, which is never sent."""
    if isinstance(item, str):
        return Variable(file=str(i), variable="", label=item)
    if isinstance(item, Variable):
        return dataclasses.replace(item, file=str(i))
    if isinstance(item, dict):
        try:
            return dataclasses.replace(variable_from_dict(item), file=str(i))
        except ValueError as e:
            raise ValueError(f"input {i}: {e}") from e
    raise TypeError(f"input {i}: expected text, a Variable or a dict, got {type(item).__name__}")


def _load(scheme: Scheme | str | os.PathLike | None) -> Scheme:
    if scheme is None:
        return parse_scheme(bundled_scheme_text(), "closer.toml")
    if isinstance(scheme, Scheme):
        return scheme
    return load_scheme(scheme)


def _kind(provider: Any) -> str:
    """The provider name a provider object counts as, checking it has what is needed."""
    missing = [m for m in ("check", "is_remote") if not callable(getattr(provider, m, None))]
    if not (
        callable(getattr(provider, "decide", None)) or callable(getattr(provider, "complete", None))
    ):
        missing.append("decide or complete")
    if missing:
        raise TypeError(f"the provider object has no {', '.join(missing)}")
    return DECISION if callable(getattr(provider, "decide", None)) else "ollama"


class Tagger:
    """A scheme, a model and settings, checked once and used for many calls.

    Making a tagger loads the scheme, resolves and checks the settings, and makes the
    provider, without any network request. The host is checked before the first request.

    Args:
        scheme: A ``Scheme``, a path to a scheme file, or None for the bundled scheme. For
            TOML text, pass ``parse_scheme(text)``.
        provider: ``"ollama"`` (chat models), ``"ollama-decision"`` (decision models), or
            an object with ``check()``, ``is_remote()`` and either ``decide`` (a decision
            model) or ``complete`` (a chat model).
        model: The model's name on the host; for a provider object, the label stored.
        method: ``"flat"`` or ``"tiered"``.
        descend_at: Tiered: the confidence a group needs to be followed (0 to 1).
        max_follow: Tiered: most groups followed per question; 0 for no cap.
        keep_at: Decision models: the probability a topic needs to be kept (0 to 1).
        base_url: The host's address.
        api_key: The host's key; defaults to ``TOPIC_TAGGER_API_KEY`` from the environment.
        timeout: Seconds allowed per request.
        batch_size: Variables per chat request.
        workers: Requests in flight at once.
        retries: Retries of a failed request before its variables are asked alone.
        allow_remote: Allow sending metadata to a cloud model.
        check: Check the host before the first request.

    ``provider`` to ``keep_at`` are taken from here if given, else from the scheme's
    ``[run]``, else the defaults. Error messages name them as the command line does
    (``--keep-at`` for ``keep_at``).

    Raises:
        SchemeError: The scheme cannot be read or breaks a rule.
        ValueError: A setting is out of range or does not fit the others.
        TypeError: A provider object lacks a method it needs.
    """

    def __init__(
        self,
        scheme: Scheme | str | os.PathLike | None = None,
        *,
        provider: Any = None,
        model: str | None = None,
        method: str | None = None,
        descend_at: float | None = None,
        max_follow: int | None = None,
        keep_at: float | None = None,
        base_url: str = "http://localhost:11434/v1",
        api_key: str | None = None,
        timeout: float = 120,
        batch_size: int = 20,
        workers: int = 2,
        retries: int = 2,
        allow_remote: bool = False,
        check: bool = True,
    ):
        self.scheme = _load(scheme)
        given_object = provider is not None and not isinstance(provider, str)
        name = _kind(provider) if given_object else provider
        given = {
            "provider": name,
            "model": model,
            "method": method,
            "descend_at": descend_at,
            "max_follow": max_follow,
            "keep_at": keep_at,
        }
        settled = settle({k: given[k] for k in KEYS}, self.scheme, label="call")
        if given_object and settled.sources["model"] == "default":
            settled.values["model"] = CUSTOM_MODEL
        self.settings: dict = settled.values
        self.sources: dict[str, str] = settled.sources
        self.notes: list[str] = settled.notes
        self._batch_size, self._workers, self._retries = batch_size, workers, retries
        self._allow_remote, self._check, self._checked = allow_remote, check, False
        if given_object:
            self._provider = provider
        else:
            self._provider = get_provider(
                self.settings["provider"],
                base_url=base_url,
                model=self.settings["model"],
                timeout=timeout,
                api_key=api_key if api_key is not None else os.environ.get("TOPIC_TAGGER_API_KEY"),
            )

    def tag(self, inputs: Iterable[Input]) -> Results:
        """Tag each input.

        Args:
            inputs: Text, ``Variable`` objects or ``variables.jsonl``-style dicts, mixed freely.

        Returns:
            One result per input, in order. An input still failing after the retries is a
            result with ``failed=True``, not an exception.

        Raises:
            TypeError, ValueError: An input is not one of the forms above, or a bad dict.
            ProviderError: The host cannot be reached or lacks the model.
        """
        items = list(inputs)
        variables = [_to_variable(i, item) for i, item in enumerate(items)]
        s = self.settings
        if not variables:
            return self._results([], None)
        self._check_host()
        settings = Settings(
            batch_size=self._batch_size,
            workers=self._workers,
            retries=self._retries,
            model=f"{s['provider']}:{s['model']}",
            method=s["method"],
            descend_at=s["descend_at"],
            max_follow=s["max_follow"],
        )
        decider = None
        if s["provider"] == DECISION:
            decider = DecisionDecider(self._provider, s["keep_at"], self.scheme.guidance)
        sink = _MemorySink()
        runner = Runner(self.scheme, self._provider, sink, settings, SystemClock(), decider=decider)
        run = runner.run(variables)
        labels = {t.id: t.label for t in self.scheme.topics}
        failed = {int(key.split("/", 1)[0]) for key in run.failed}
        results = []
        for i, item in enumerate(items):
            record = sink.records.get(i)
            tags = [Tag(t, labels[t], c) for t, c in record["topics"]] if record else []
            path = [(g, c) for g, c in record["path"]] if record and "path" in record else None
            missing = i in failed or record is None
            results.append(
                Result(
                    input=item,
                    tags=tags,
                    path=path,
                    failed=missing,
                    error=run.last_error if missing else "",
                    method=s["method"],
                    model=settings.model,
                    scheme_hash=self.scheme.hash,
                )
            )
        return self._results(results, run)

    def classify(self, input: Input) -> Result:
        """Tag one input.

        Args:
            input: Text, a ``Variable``, or a ``variables.jsonl``-style dict.

        Returns:
            Its result.
        """
        return self.tag([input])[0]

    def _check_host(self) -> None:
        if self._check and not self._checked:
            self._provider.check()
            self._checked = True

    def _results(self, results: list[Result], run) -> Results:
        return Results(
            results,
            settings=dict(self.settings),
            sources=dict(self.sources),
            notes=list(self.notes),
            scheme=self.scheme,
            requests_by_tier=run.requests_by_tier if run else [],
            retries=run.retries if run else 0,
        )


def tag(
    inputs: Iterable[Input], scheme: Scheme | str | os.PathLike | None = None, **options
) -> Results:
    """Tag each input with a scheme, in one call.

    The same as ``Tagger(scheme, **options).tag(inputs)``; see ``Tagger`` for the options.

    Args:
        inputs: Text, ``Variable`` objects or ``variables.jsonl``-style dicts, mixed freely.
        scheme: A ``Scheme``, a path to a scheme file, or None for the bundled scheme.
        **options: ``Tagger``'s keyword arguments.

    Returns:
        One result per input, in input order.
    """
    return Tagger(scheme, **options).tag(inputs)


def classify(input: Input, scheme: Scheme | str | os.PathLike | None = None, **options) -> Result:
    """Tag one input with a scheme.

    The same as ``tag([input], scheme, **options)[0]``.

    Args:
        input: Text, a ``Variable``, or a ``variables.jsonl``-style dict.
        scheme: A ``Scheme``, a path to a scheme file, or None for the bundled scheme.
        **options: ``Tagger``'s keyword arguments.

    Returns:
        Its result.
    """
    return Tagger(scheme, **options).classify(input)


__all__ = [
    "CUSTOM_MODEL",
    "Input",
    "RemoteModelError",
    "Result",
    "Results",
    "Tag",
    "Tagger",
    "classify",
    "tag",
]
