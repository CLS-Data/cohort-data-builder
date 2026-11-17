# Research: The Topic Tagger as a Python API

Decisions for [plan.md](plan.md). Each one gives the decision, why, and what else was
considered.

## R1. One new module, re-exported from the package

- **Decision**: Add `src/topic_tagger/api.py` with `Tagger`, `tag`, `classify`, `Result`,
  `Results`, `Tag` and `RemoteModelError`. Also re-export these from `topic_tagger`, with
  `__all__`:
  - `Variable`, `Scheme`, `load_scheme`, `parse_scheme`;
  - `SchemeError`, `ProviderError`, `OptionLimitError`.
- **Rationale**: One import line (`from topic_tagger import tag`) meets SC-001. Everything a
  caller may need is listed in `__all__`. Every other module stays internal, so it can
  change (FR-015).
- **Alternatives**:
  - Make the existing modules public as they are. They mix CLI concerns (files, locks,
    display) with tagging, and would freeze their internals.
  - A separate package. The tool must stay one self-contained project (feature 002).

## R2. Tag through the existing `Runner`, with records kept in memory

- **Decision**: `Tagger.tag` builds a `Runner` per call, as `cli._run` does, but gives it an
  in-memory record sink instead of a `TagStore`. The sink is a class in `api.py` with one
  method, `append(records)`. `Runner`'s `store` parameter is typed as a small `RecordSink`
  protocol (`append` only), which `TagStore` already satisfies.
- **Rationale**: The runner already does the following, for both model kinds and both
  methods:
  - batching;
  - parallel workers;
  - the retry ladder;
  - singles;
  - walking the tree;
  - stopping on `OptionLimitError`.

  Reusing it is what makes the API's tags equal the command line's (FR-014, SC-002), with
  no second copy of that logic (Principle IV).
- **Alternatives**: Call `tiered.walk` directly. That covers tiered tagging and decision
  models, but flat chat tagging goes through `Runner._batch` and its retry ladder, which
  would have to be copied.

## R3. Inputs keyed by position

- **Decision**: Each input becomes an internal `Variable` whose `file` is its position in the
  call (`"0"`, `"1"`, …):
  - a `Variable` keeps its name, label and value labels;
  - a `variables.jsonl`-style dict is read with the same parser as the file
    (`variables._parse`, exposed as `variable_from_dict`);
  - a string becomes `Variable(name="", label=text)`.

  Records and failures come back keyed `file/variable`, and are mapped back to positions.
  Each `Result` holds the caller's original input.
- **Rationale**:
  - The prompts and decision states send only `name`, `label` and `values`
    (`prompt.py:146`, `tiered._state`), never `file`, so the model sees exactly what the
    command line would send (US1 scenario 2).
  - Positions make keys unique, so duplicate inputs are tagged separately and stay in
    order (edge cases).
- **Alternatives**:
  - Keep the caller's `file`. Duplicate keys would collide in the runner's `paths`.
  - Reject duplicates. That is surprising for plain text.
  - Send text as the name. The label is what models weigh most, and an empty name says
    there is nothing more.

## R4. Settings resolved and checked in one place, shared with the CLI

- **Decision**: Move the checks in `cli._settle` into `run_settings.settle(given, scheme)`.
  It returns `Resolved` (values, sources, notes) or raises `ValueError` with today's
  wording. The checks it performs:
  - ranges;
  - `--keep-at` needing a decision model;
  - tiered-only options with flat;
  - a one-tier taxonomy forcing flat, with its note.

  `cli._settle` calls `settle`, prints the notes and turns `ValueError` into exit 2, as
  now. `Tagger` passes its keyword arguments as `given`. Messages keep the command line's
  option names (for example `--keep-at needs --provider ollama-decision`); the API
  docstrings map those names to its keyword arguments.
- **Rationale**: One source of truth for precedence and checks (FR-006), and the CLI's
  output stays the same (FR-016), which the existing CLI tests check.
- **Alternatives**:
  - Duplicate the checks in `api.py`. They would drift apart.
  - Reword the messages per caller. That needs a parameter for wording alone, for little
    gain.

## R5. Schemes from a path, text, an object, or the bundled one

- **Decision**: Split `load_scheme(path)` into reading the file and
  `parse_scheme(text, source)`. `source` names the scheme in error messages: the path, or
  `<text>`. The hash is computed in `parse_scheme`, so text and a file with the same content
  hash the same (FR-004). `Tagger(scheme=...)` accepts:
  - a `Scheme`;
  - a path (`str` or `os.PathLike`);
  - `None`, meaning the bundled scheme.

  TOML text goes through `parse_scheme(text)` first.
- **Rationale**: A string that is sometimes a path and sometimes TOML is ambiguous. One
  explicit function keeps `scheme=` meaning one thing.
- **Alternatives**: Guess from the string (a newline or `=` means TOML). Brittle, and a
  wrong guess gives a confusing "cannot read" error.

## R6. Provider objects as well as names

- **Decision**: `provider=` takes a name (`"ollama"`, `"ollama-decision"`) or an object:
  - an object with `decide` is a decision model (it gets a `DecisionDecider`);
  - otherwise it must have `complete` (a chat model).

  For settings it counts as `ollama-decision` or `ollama` respectively, with source `call`.
  `model=` is then only the label stored with the tags (default `"custom"`).
- **Rationale**: Tests of calling code need a fake, and other hosts can be plugged in
  without registering them (FR-008). The existing protocols already describe what is
  needed.
- **Alternatives**: Name-only providers, plus a registry the caller adds to. That is more
  machinery for the same thing.

## R7. Errors and side effects

- **Decision**:
  - The API never prints, prompts or exits.
  - Notes are returned in `Results.notes` (and on `Tagger.notes`).
  - Exceptions:
    - `SchemeError` for a bad scheme;
    - `ValueError` for a bad setting;
    - `TypeError` for an input that is not text, a `Variable` or a dict;
    - `ProviderError` for an unreachable host or a missing model;
    - `OptionLimitError` for a refusal (raised, not returned, with `question` and
      `advice` filled in by the walk);
    - `RemoteModelError(ProviderError)` when `provider.is_remote()` and `allow_remote`
      is not `True`.
  - Variables that fail after retries are results with `failed=True` and `error`.
- **Rationale**:
  - A library must not take over the process (FR-011).
  - Remote consent mirrors `--yes`, so metadata never leaves the machine by accident
    (FR-012).
  - Per-variable failures are normal outcomes, as on the command line, not exceptions.
- **Alternatives**:
  - Return partial results after a refusal. The spec leaves it out; the exception says
    which question was refused, and the same call fails the same way again.
  - Use `warnings` for notes. Notes are information, not warnings, and callers would have
    to filter them.

## R8. When the host is checked

- **Decision**: `Tagger` checks the host lazily, once, before the first request of the
  first non-empty call (FR-013). `Tagger(..., check=False)` skips the check, for callers
  who know the host is there.
- **Rationale**:
  - Making a tagger (for example at import time in a pipeline) needs no network.
  - An empty call costs nothing.
  - Repeated calls do not re-check.
- **Alternatives**: Check in the constructor. That makes a tagger unusable offline even for
  `settings` or a dry inspection.

## R9. Version

- **Decision**: 0.1.0 → 0.2.0 in `pyproject.toml` and `__init__.__version__`.
- **Rationale**: This is the first release with a public Python API.
