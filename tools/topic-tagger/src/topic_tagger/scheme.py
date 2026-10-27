"""The topic scheme: topic areas (domains), their topics, and the model's guidance.

It is read from a TOML file the maintainer edits (see docs/formats.md). The tool ships one,
``schemes/closer.toml``, used when no file is given.
"""

from __future__ import annotations

import hashlib
import json
import re
import tomllib
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path

ID = re.compile(r"^[a-z][a-z0-9_]*$")


@dataclass(frozen=True)
class SchemeProblem:
    """One mistake in a scheme file.

    Attributes:
        location: Where it is, e.g. ``domains[1].topics[0].id`` (counting from 0).
        message: What is wrong.
    """

    location: str
    message: str

    def __str__(self) -> str:
        """``location: message``."""
        return f"{self.location}: {self.message}"


class SchemeError(Exception):
    """The scheme file cannot be used.

    Attributes:
        problems: Every mistake found, empty when the file could not be read at all.
    """

    def __init__(self, message: str, problems: list[SchemeProblem] | None = None):
        self.problems = problems or []
        if self.problems:
            message += "\n  " + "\n  ".join(map(str, self.problems))
        super().__init__(message)


@dataclass(frozen=True)
class Topic:
    """One topic: what a variable can be tagged with."""

    id: str
    label: str
    description: str


@dataclass(frozen=True)
class Domain:
    """A topic area holding related topics."""

    id: str
    label: str
    description: str
    topics: tuple[Topic, ...]


@dataclass(frozen=True)
class Scheme:
    """A loaded topic scheme.

    Attributes:
        name: The scheme's name.
        version: The maintainer's own version number.
        guidance: The instructions given to the model.
        identifier_topic: The topic given to the participant identifier, by rule.
        fallback_topic: The topic for variables that fit nothing else.
        domains: The topic areas, in order.
        hash: 12 hex characters identifying the content; any edit changes it.
    """

    name: str
    version: int
    guidance: str
    identifier_topic: str
    fallback_topic: str
    domains: tuple[Domain, ...]
    hash: str
    _number: dict[str, int] = field(default_factory=dict, repr=False, compare=False)
    _domain: dict[str, Domain] = field(default_factory=dict, repr=False, compare=False)

    def __post_init__(self) -> None:
        """Index the topics by id."""
        for d in self.domains:
            for t in d.topics:
                self._number[t.id] = len(self._number)
                self._domain[t.id] = d

    @property
    def topic_ids(self) -> list[str]:
        """Every topic id, in scheme order."""
        return list(self._number)

    @property
    def topics(self) -> list[Topic]:
        """Every topic, in scheme order."""
        return [t for d in self.domains for t in d.topics]

    def topic_number(self, topic_id: str) -> int:
        """The topic's position across the whole scheme, counting from 0."""
        return self._number[topic_id]

    def domain_of(self, topic_id: str) -> Domain:
        """The domain a topic belongs to."""
        return self._domain[topic_id]

    def to_json(self) -> dict:
        """The scheme as written to ``scheme.json``."""
        return {
            "name": self.name,
            "version": self.version,
            "hash": self.hash,
            "guidance": self.guidance,
            "identifier_topic": self.identifier_topic,
            "fallback_topic": self.fallback_topic,
            "domains": [
                {
                    "id": d.id,
                    "label": d.label,
                    "description": d.description,
                    "topics": [
                        {"id": t.id, "label": t.label, "description": t.description}
                        for t in d.topics
                    ],
                }
                for d in self.domains
            ],
        }


def bundled_scheme_text() -> str:
    """The text of the bundled CLOSER scheme, ``schemes/closer.toml``."""
    return (resources.files("topic_tagger") / "schemes" / "closer.toml").read_text(encoding="utf-8")


def load_scheme(path: Path | None) -> Scheme:
    """Load a scheme file.

    Args:
        path: The TOML file, or None for the bundled CLOSER scheme.

    Returns:
        The scheme.

    Raises:
        SchemeError: If the file cannot be read or parsed.
    """
    try:
        text = bundled_scheme_text() if path is None else Path(path).read_text(encoding="utf-8")
        raw = tomllib.loads(text)
    except OSError as e:
        raise SchemeError(f"cannot read {path}: {e.strerror}") from e
    except tomllib.TOMLDecodeError as e:
        raise SchemeError(f"{path}: not valid TOML: {e}") from e
    problems = validate(raw)
    if problems:
        where = path or "the bundled scheme"
        raise SchemeError(f"{where} has {len(problems)} problem(s):", problems)

    # The hash is over the parsed content, so comments and layout do not change it.
    canonical = json.dumps(raw, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return Scheme(
        name=raw["name"],
        version=raw["version"],
        guidance=raw["guidance"].strip(),
        identifier_topic=raw["identifier_topic"],
        fallback_topic=raw["fallback_topic"],
        domains=tuple(
            Domain(
                id=d["id"],
                label=d["label"],
                description=d.get("description", ""),
                topics=tuple(Topic(t["id"], t["label"], t["description"]) for t in d["topics"]),
            )
            for d in raw["domains"]
        ),
        hash=hashlib.sha256(canonical.encode()).hexdigest()[:12],
    )


def validate(raw: dict) -> list[SchemeProblem]:
    """Find every mistake in a parsed scheme, not only the first.

    Args:
        raw: The scheme file as parsed from TOML.

    Returns:
        The problems, each with its location; empty when the scheme is usable.
    """
    problems: list[SchemeProblem] = []

    def problem(location: str, message: str) -> None:
        problems.append(SchemeProblem(location, message))

    def text(obj: dict, field: str, at: str) -> None:
        value = obj.get(field)
        if not isinstance(value, str) or not value.strip():
            problem(f"{at}{field}", "missing or empty")

    for name in ("name", "guidance"):
        text(raw, name, "")
    if "version" not in raw:
        problem("version", "missing or empty")
    elif not isinstance(raw["version"], int) or isinstance(raw["version"], bool):
        problem("version", "must be a whole number")

    seen: dict[str, str] = {}
    topic_ids: set[str] = set()

    def ident(obj: dict, at: str) -> str | None:
        value = obj.get("id")
        if not isinstance(value, str) or not ID.match(value):
            problem(
                f"{at}id",
                f"{value!r} must be lower-case letters, digits and _, starting with a letter",
            )
            return None
        if value in seen:
            problem(f"{at}id", f"{value!r} is also used at {seen[value]}")
        else:
            seen[value] = f"{at}id"
        return value

    domains = raw.get("domains")
    if not isinstance(domains, list) or not domains:
        problem("domains", "there are no domains")
        domains = []
    for i, d in enumerate(domains):
        at = f"domains[{i}]."
        ident(d, at)
        text(d, "label", at)
        text(d, "description", at)
        topics = d.get("topics")
        if not isinstance(topics, list) or not topics:
            problem(f"{at}topics", "this domain has no topics")
            continue
        for j, t in enumerate(topics):
            tat = f"{at}topics[{j}]."
            tid = ident(t, tat)
            if tid:
                topic_ids.add(tid)
            text(t, "label", tat)
            text(t, "description", tat)

    for name in ("identifier_topic", "fallback_topic"):
        value = raw.get(name)
        if value not in topic_ids:
            problem(name, f"{value!r} is not a topic in this scheme")
    return problems
