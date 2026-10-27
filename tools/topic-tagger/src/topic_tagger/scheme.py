"""The topic scheme: topic areas (domains), their topics, and the model's guidance.

It is read from a TOML file the maintainer edits (see docs/formats.md). The tool ships one,
``schemes/closer.toml``, used when no file is given.
"""

from __future__ import annotations

import hashlib
import json
import tomllib
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path


class SchemeError(Exception):
    """The scheme file cannot be used."""


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
        if path is None:
            text = (resources.files("topic_tagger") / "schemes" / "closer.toml").read_text(
                encoding="utf-8"
            )
        else:
            text = Path(path).read_text(encoding="utf-8")
        raw = tomllib.loads(text)
    except OSError as e:
        raise SchemeError(f"cannot read {path}: {e.strerror}") from e
    except tomllib.TOMLDecodeError as e:
        raise SchemeError(f"{path}: not valid TOML: {e}") from e

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
