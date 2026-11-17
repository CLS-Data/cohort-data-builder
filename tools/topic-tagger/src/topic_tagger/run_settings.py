"""How a run classifies, and where each setting came from (feature 005).

A scheme file may carry a ``[run]`` table: the provider (the kind of model), the model, the
method and the thresholds. The command line overrides it for one run, and anything set by
neither takes its default. ``resolve`` returns the values and, for ``run.json``, each one's
source: ``cli``, ``file`` or ``default``.

Only classification settings belong here. Where the host is, keys, workers, retries and
output paths stay on the command line, so a shared scheme carries no secrets and nothing
specific to one machine.
"""

from __future__ import annotations

from dataclasses import dataclass, field, fields
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from topic_tagger.scheme import Scheme

#: The providers a ``[run]`` table may name.
PROVIDERS = ("ollama", "ollama-decision")
#: The tagging methods.
METHODS = ("flat", "tiered")
#: The provider whose models answer choice questions with probabilities.
DECISION = "ollama-decision"

DEFAULTS = {"provider": "ollama", "model": "gpt-oss:20b", "descend_at": 0.5, "max_follow": 3}
DEFAULT_KEEP_AT = 0.3


@dataclass(frozen=True)
class RunSettings:
    """The ``[run]`` table of a scheme file; a setting left out is None.

    Attributes:
        provider: ``ollama`` (chat models) or ``ollama-decision`` (decision models).
        model: The model's name on the host.
        method: ``flat`` or ``tiered``.
        descend_at: Tiered: the confidence a group needs to be followed (0 to 1).
        max_follow: Tiered: most groups followed per variable at each question; 0 for no cap.
        keep_at: Decision models: the probability a leaf needs to be kept (0 to 1).
    """

    provider: str | None = None
    model: str | None = None
    method: str | None = None
    descend_at: float | None = None
    max_follow: int | None = None
    keep_at: float | None = None


#: The keys a ``[run]`` table may have.
KEYS = tuple(f.name for f in fields(RunSettings))


@dataclass
class Resolved:
    """The settings a run uses.

    Attributes:
        values: Every setting's value; ``keep_at`` is None for a chat model.
        sources: ``{setting: "cli" | "file" | "default"}`` for each setting that applies.
        notes: Things to tell the user, such as a file setting that does not apply.
    """

    values: dict
    sources: dict[str, str]
    notes: list[str] = field(default_factory=list)


def resolve(cli: dict, file: RunSettings | None) -> Resolved:
    """Take each setting from the command line, else the scheme's ``[run]``, else the default.

    Args:
        cli: ``{setting: value or None}`` from the command line, with every key in ``KEYS``.
        file: The scheme's ``[run]`` table, or None.

    Returns:
        The values, their sources and any notes.
    """
    file = file or RunSettings()
    values: dict = {}
    sources: dict[str, str] = {}
    notes: list[str] = []

    def pick(key: str, default) -> None:
        if cli.get(key) is not None:
            values[key], sources[key] = cli[key], "cli"
        elif getattr(file, key) is not None:
            values[key], sources[key] = getattr(file, key), "file"
        else:
            values[key], sources[key] = default, "default"

    for key in ("provider", "model"):
        pick(key, DEFAULTS[key])
    decision = values["provider"] == DECISION
    # The method's default depends on the provider chosen, wherever that came from.
    pick("method", "tiered" if decision else "flat")
    for key in ("descend_at", "max_follow"):
        pick(key, DEFAULTS[key])
    if decision:
        pick("keep_at", DEFAULT_KEEP_AT)
    else:
        values["keep_at"] = None
        if cli.get("keep_at") is None and file.keep_at is not None:
            notes.append("keep_at in the scheme applies to decision models only; ignored.")
    return Resolved(values, sources, notes)


def settle(given: dict, scheme: Scheme, label: str = "cli") -> Resolved:
    """Settle a run's settings and check them, as the command line and the API both do.

    Each setting is the one given, else the scheme's ``[run]``, else the default
    (``resolve``). Then the given values are checked, and a one-tier taxonomy asked to tag
    tiered tags flat instead. Messages name the command-line options (``--keep-at``); the
    API's keyword arguments have the same names with underscores.

    Args:
        given: ``{setting: value or None}`` with every key in ``KEYS``.
        scheme: The loaded scheme; its ``[run]`` and number of tiers are used.
        label: The source recorded for a given setting: ``cli`` or ``call``.

    Returns:
        The values, their sources and any notes to show the user.

    Raises:
        ValueError: If a given value is out of range or does not fit the others.
    """
    for key in ("descend_at", "keep_at"):
        if given.get(key) is not None and not 0 <= given[key] <= 1:
            raise ValueError(f"--{key.replace('_', '-')} must be between 0 and 1")
    if given.get("max_follow") is not None and given["max_follow"] < 0:
        raise ValueError("--max-follow must be 0 (no cap) or more")
    settled = resolve(given, scheme.run)
    values, sources = settled.values, settled.sources
    if given.get("keep_at") is not None and values["provider"] != DECISION:
        raise ValueError("--keep-at needs --provider ollama-decision")
    tiered_options = [k for k in ("descend_at", "max_follow") if sources[k] == "cli"]
    if values["method"] == "flat" and tiered_options:
        raise ValueError("--descend-at and --max-follow need --method tiered")
    if values["method"] == "tiered" and scheme.tiers == 1:
        settled.notes.append("This taxonomy has one tier: tagging flat.")
        values["method"] = "flat"
    if values["method"] == "flat":  # the tiered settings do not apply, so are not recorded
        for key in ("descend_at", "max_follow"):
            sources.pop(key)
    settled.sources = {k: (label if v == "cli" else v) for k, v in sources.items()}
    return settled


def validate_run(raw, problem) -> RunSettings | None:
    """Check a parsed ``[run]`` table, reporting each mistake through ``problem``.

    Args:
        raw: The table as parsed from TOML.
        problem: Called as ``problem(location, message)`` for each mistake.

    Returns:
        The settings, or None if the table is not a table.
    """
    if not isinstance(raw, dict):
        problem("run", "must be a table")
        return None
    for key in raw:
        if key not in KEYS:
            problem(f"run.{key}", f"unknown setting; known: {', '.join(KEYS)}")
    if "provider" in raw and raw["provider"] not in PROVIDERS:
        problem("run.provider", "must be ollama or ollama-decision")
    if "model" in raw and (not isinstance(raw["model"], str) or not raw["model"].strip()):
        problem("run.model", "missing or empty")
    if "method" in raw and raw["method"] not in METHODS:
        problem("run.method", "must be flat or tiered")
    for key in ("descend_at", "keep_at"):
        value = raw.get(key)
        if key in raw and (
            isinstance(value, bool) or not isinstance(value, int | float) or not 0 <= value <= 1
        ):
            problem(f"run.{key}", "must be between 0 and 1")
    value = raw.get("max_follow")
    if "max_follow" in raw and (isinstance(value, bool) or not isinstance(value, int) or value < 0):
        problem("run.max_follow", "must be a whole number, 0 (no cap) or more")
    return RunSettings(**{k: raw[k] for k in KEYS if k in raw})
