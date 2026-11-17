"""The scheme: a taxonomy of one to three tiers, and the model's guidance.

It is read from a TOML file the maintainer edits (see docs/formats.md), in either of two
forms: nested ``[[categories]]`` (feature 005), or ``[[domains]]`` holding
``[[domains.topics]]`` (002/004), which is a two-tier taxonomy. Both load into one
``Category`` tree. Everything the model
is told about topics comes from that file; the code depends on no particular scheme. An
example scheme is bundled (``schemes/closer.toml``) and used when no file is given.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import tomllib
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path

from topic_tagger.run_settings import RunSettings, validate_run

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
    """One topic: what a variable can be tagged with (a leaf of the taxonomy)."""

    id: str
    label: str
    description: str


@dataclass(frozen=True)
class Domain:
    """A topic area: a tier-1 category and every leaf beneath it.

    The taxonomy itself is the ``Category`` tree; domains are a view of it, kept for the
    statistics, the report and ``scheme.json``. A tier-1 leaf is a domain of itself.
    """

    id: str
    label: str
    description: str
    topics: tuple[Topic, ...]


@dataclass(frozen=True)
class Category:
    """One entry in the taxonomy: a group (with children) or a leaf (without).

    Attributes:
        id: Unique across the whole taxonomy; ``""`` for the root.
        label: Its label.
        description: Its description; may be empty.
        children: The categories one tier down, in file order; empty for a leaf.
    """

    id: str
    label: str
    description: str = ""
    children: tuple[Category, ...] = ()

    @property
    def is_leaf(self) -> bool:
        """True for a category a variable can be tagged with."""
        return not self.children


@dataclass(frozen=True)
class Scheme:
    """A loaded taxonomy of one to three tiers.

    Attributes:
        name: The scheme's name.
        version: The maintainer's own version number.
        guidance: The instructions given to the model.
        fallback_topic: The leaf for variables that fit nothing else.
        root: The taxonomy: a nameless root whose children are the tier-1 categories.
        hash: 12 hex characters identifying the content; any edit changes it, except to
            the ``[run]`` table.
        run: The ``[run]`` table: how to classify, unless the command line says otherwise.
        questions: The ``[questions]`` table: ``{"flat" | "tier1".. : question}``, where
            ``{group}`` stands for the label of the group whose children are offered.
    """

    name: str
    version: int
    guidance: str
    fallback_topic: str
    root: Category
    hash: str
    run: RunSettings | None = None
    questions: dict[str, str] = field(default_factory=dict)
    _leaves: dict[str, Topic] = field(default_factory=dict, repr=False, compare=False)
    _number: dict[str, int] = field(default_factory=dict, repr=False, compare=False)
    _domain: dict[str, Domain] = field(default_factory=dict, repr=False, compare=False)
    _path: dict[str, list[str]] = field(default_factory=dict, repr=False, compare=False)
    _domains: list[Domain] = field(default_factory=list, repr=False, compare=False)

    def __post_init__(self) -> None:
        """Index the leaves, their paths and their tier-1 categories."""

        def visit(c: Category, path: list[str]) -> None:
            if c.is_leaf:
                self._leaves[c.id] = Topic(c.id, c.label, c.description)
                self._number[c.id] = len(self._number)
                self._path[c.id] = path
                return
            for child in c.children:
                visit(child, [*path, c.id])

        for top in self.root.children:
            before = len(self._leaves)
            visit(top, [])
            leaves = tuple(list(self._leaves.values())[before:])
            domain = Domain(top.id, top.label, top.description, leaves)
            self._domains.append(domain)
            for t in leaves:
                self._domain[t.id] = domain

    @property
    def tiers(self) -> int:
        """How many tiers deep the taxonomy is: 1 to 3."""
        return _height(self.root)

    @property
    def topic_ids(self) -> list[str]:
        """Every leaf id, in file order."""
        return list(self._number)

    @property
    def topics(self) -> list[Topic]:
        """Every leaf, in file order."""
        return list(self._leaves.values())

    @property
    def domains(self) -> list[Domain]:
        """One per tier-1 category, holding every leaf beneath it."""
        return list(self._domains)

    def topic_number(self, topic_id: str) -> int:
        """The leaf's position across the whole taxonomy, counting from 0."""
        return self._number[topic_id]

    def domain_of(self, topic_id: str) -> Domain:
        """The domain (tier-1 category) a leaf belongs to."""
        return self._domain[topic_id]

    def path_of(self, topic_id: str) -> list[str]:
        """The groups above a leaf, from tier 1 down to its parent; empty at tier 1."""
        return list(self._path[topic_id])

    def to_json(self) -> dict:
        """The scheme as written to ``scheme.json``.

        ``domains`` is kept, as written by 004, for readers that know only two levels;
        ``categories`` is the taxonomy itself.
        """
        return {
            "name": self.name,
            "version": self.version,
            "hash": self.hash,
            "guidance": self.guidance,
            "fallback_topic": self.fallback_topic,
            "tiers": self.tiers,
            "questions": self.questions,
            "categories": [_category_json(c) for c in self.root.children],
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


def _height(c: Category) -> int:
    return 0 if c.is_leaf else 1 + max(_height(x) for x in c.children)


def _category_json(c: Category) -> dict:
    out = {"id": c.id, "label": c.label, "description": c.description}
    if c.children:
        out["categories"] = [_category_json(x) for x in c.children]
    return out


def _category_from(raw: dict) -> Category:
    """A category, and those under it, from parsed TOML or ``scheme.json``."""
    return Category(
        raw["id"],
        raw["label"],
        raw.get("description", "") or "",
        tuple(_category_from(x) for x in raw.get("categories", [])),
    )


def _root(raw: dict) -> Category:
    """The taxonomy from either form: nested ``categories``, or 004 ``domains``/``topics``."""
    if "categories" in raw:
        children = tuple(_category_from(c) for c in raw["categories"])
    else:
        children = tuple(
            Category(
                d["id"],
                d["label"],
                d.get("description", ""),
                tuple(Category(t["id"], t["label"], t["description"]) for t in d["topics"]),
            )
            for d in raw["domains"]
        )
    return Category("", raw["name"], "", children)


def scheme_from_json(data: dict) -> Scheme:
    """Rebuild a scheme from the ``scheme.json`` written beside the tags.

    Reads ``categories`` when present, and ``domains`` otherwise (folders written by 004).

    Args:
        data: The parsed ``scheme.json``.

    Returns:
        The scheme, with the hash it was saved with.
    """
    return Scheme(
        name=data["name"],
        version=data["version"],
        guidance=data["guidance"],
        fallback_topic=data["fallback_topic"],
        root=_root(data),
        hash=data["hash"],
        questions=data.get("questions", {}),
    )


def bundled_scheme_text() -> str:
    """The text of the bundled example scheme, ``schemes/closer.toml``."""
    return (resources.files("topic_tagger") / "schemes" / "closer.toml").read_text(encoding="utf-8")


def load_scheme(path: str | os.PathLike) -> Scheme:
    """Load a scheme file.

    Args:
        path: The TOML file.

    Returns:
        The scheme.

    Raises:
        SchemeError: If the file cannot be read or parsed, or breaks a rule.
    """
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError as e:
        raise SchemeError(f"cannot read {path}: {e.strerror}") from e
    return parse_scheme(text, str(path))


def parse_scheme(text: str, source: str = "<text>") -> Scheme:
    """Load a scheme from its TOML text, with the same checks and hash as a file.

    Args:
        text: The scheme, as TOML.
        source: What to call it in error messages: a path, or ``<text>``.

    Returns:
        The scheme.

    Raises:
        SchemeError: If the text is not TOML or breaks a rule; the message starts with
            ``source``.
    """
    try:
        raw = tomllib.loads(text)
    except tomllib.TOMLDecodeError as e:
        raise SchemeError(f"{source}: not valid TOML: {e}") from e
    problems = validate(raw)
    if problems:
        raise SchemeError(f"{source} has {len(problems)} problem(s):", problems)

    # The hash is over the parsed content, so comments and layout do not change it. It leaves
    # out [run]: a model or threshold is how a run is made, not what the tags mean, so
    # changing one should not redo every tag (the method is stored with each tag instead).
    content = {k: v for k, v in raw.items() if k != "run"}
    canonical = json.dumps(content, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return Scheme(
        name=raw["name"],
        version=raw["version"],
        guidance=raw["guidance"].strip(),
        fallback_topic=raw["fallback_topic"],
        root=_root(raw),
        hash=hashlib.sha256(canonical.encode()).hexdigest()[:12],
        run=RunSettings(**raw["run"]) if "run" in raw else None,
        questions=dict(raw.get("questions", {})),
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

    if "run" in raw:
        validate_run(raw["run"], problem)
    if "questions" in raw:
        _validate_questions(raw, problem)

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

    if "categories" in raw:
        if "domains" in raw:
            problem("categories", "use categories (nested) or domains (004 form), not both")
        _validate_nested(raw, problem, text, ident)
        return problems

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

    if raw.get("fallback_topic") not in topic_ids:
        problem("fallback_topic", f"{raw.get('fallback_topic')!r} is not a topic in this scheme")
    return problems


#: The deepest a taxonomy may be.
MAX_TIERS = 3


def _validate_questions(raw: dict, problem) -> None:
    """Check ``[questions]``: ``flat``, and ``tier1`` up to the taxonomy's depth."""
    questions = raw["questions"]
    if not isinstance(questions, dict):
        problem("questions", "must be a table")
        return
    depth = min(_raw_depth(raw["categories"]), MAX_TIERS) if "categories" in raw else 2
    known = ["flat"] + [f"tier{i}" for i in range(1, depth + 1)]
    for key, value in questions.items():
        if key not in known:
            problem(f"questions.{key}", f"unknown; this taxonomy takes: {', '.join(known)}")
        elif not isinstance(value, str) or not value.strip():
            problem(f"questions.{key}", "missing or empty")


def _raw_depth(items) -> int:
    """How many tiers a nested ``categories`` list has, as parsed (before it is checked)."""
    if not isinstance(items, list) or not items:
        return 1
    below = [
        _raw_depth(c["categories"]) for c in items if isinstance(c, dict) and "categories" in c
    ]
    return 1 + max(below, default=0)


def _validate_nested(raw: dict, problem, text, ident) -> None:
    """Check the nested form: ids, labels, groups, depth, leaves and the fallback."""
    leaves: list[str] = []
    groups: set[str] = set()

    def visit(items, at: str, tier: int) -> None:
        for i, c in enumerate(items):
            here = f"{at}[{i}]"
            if not isinstance(c, dict):
                problem(here, "must be a table")
                continue
            if tier > MAX_TIERS:
                problem(here, f"too deep: a taxonomy has at most {MAX_TIERS} tiers")
                continue
            cid = ident(c, f"{here}.")
            text(c, "label", f"{here}.")
            if "description" in c and not isinstance(c["description"], str):
                problem(f"{here}.description", "must be text")
            if "categories" not in c:
                if cid:
                    leaves.append(cid)
                continue
            children = c["categories"]
            if not isinstance(children, list) or not children:
                problem(f"{here}.categories", "this group has no categories")
                continue
            if cid:
                groups.add(cid)
            visit(children, f"{here}.categories", tier + 1)

    top = raw["categories"]
    if not isinstance(top, list) or not top:
        problem("categories", "there are no categories")
        return
    visit(top, "categories", 1)
    if len(leaves) < 2:
        problem(
            "categories",
            "a taxonomy needs at least two leaves (categories with no others under them)",
        )
    fallback = raw.get("fallback_topic")
    if fallback in groups:
        problem("fallback_topic", f"{fallback!r} is a group, not a leaf")
    elif fallback not in leaves:
        problem("fallback_topic", f"{fallback!r} is not a leaf in this scheme")
