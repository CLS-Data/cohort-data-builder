# Implementation Plan: The Topic Tagger as a Python API

**Branch**: `006-tagger-api` | **Date**: 2026-11-17 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/006-tagger-api/spec.md`

## Summary

A small public API so other code can tag text or variables in one call:
`from topic_tagger import tag`. It is built on what the command line already does, not
beside it:

- **Settings:** the same resolution of `[run]` settings (call, else file, else default)
  and the same checks. These move out of `cli._settle` into a shared
  `run_settings.settle`.
- **Tagging:** the same `Runner`, so batching, retries, the tier walk and refusals behave
  identically. It is given an in-memory record sink instead of `TagStore`.
- **Schemes:** the same scheme loading. `parse_scheme(text)` is split out of
  `load_scheme(path)`, so TOML text works and hashes the same.

Inputs (text, `Variable`, or a `variables.jsonl`-style dict) are keyed internally by
position. Results come back in input order with tags, paths and failures. The API never
writes files, prints, prompts or exits. Problems are exceptions, and cloud models need
`allow_remote=True`.

## Technical Context

**Language/Version**: Python 3.12 (the tagger's own project, `tools/topic-tagger/`)

**Primary Dependencies**: Existing only: pydantic, langchain-core, openai, rich. No new
dependencies.

**Storage**: None. The API keeps results in memory. The CLI's output folder is unchanged.

**Testing**: pytest. The new `tests/test_api.py` uses provider objects (scripted chat and
decision fakes), so no network or local port is needed. An equivalence test runs the CLI
and the API over the fixture variables with the same scripted replies and compares the
tags (SC-002). A `capsys` and `tmp_path` check across the API tests asserts no output and
no files (SC-003).

**Target Platform**: Any machine with Python 3.12+. Used from notebooks, scripts and
pipelines.

**Project Type**: Library API added to an existing CLI tool (a standalone Python project in
the repo).

**Performance Goals**: The same requests per input as the CLI. Constructing a `Tagger`
makes no network request. Checking the host costs one request per tagger.

**Constraints**:
- CLI behaviour and output unchanged (FR-016).
- No files, output or prompts from the API (FR-011).
- Nothing sent to a cloud model without consent (FR-012).
- The tool stays self-contained (feature 002).

**Scale/Scope**: Calls of 1 to 10⁴ inputs; larger, resumable jobs stay with the CLI.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | How |
|---|---|---|
| I. Test-driven | Pass | Every story starts with failing tests in `tests/test_api.py`, plus `test_scheme.py` (`parse_scheme`) and `test_run_settings.py` (`settle`). Fakes are provider objects, so the tests are deterministic and need no network. |
| II. Documented code | Pass | Google-style docstrings on every public name, with the contract in `contracts/api.md`. The README gains "Using it from Python" (FR-017). |
| III. Static GitHub Pages | Pass, not affected | Offline maintainer tool. Nothing changes in `site/` or `scripts/topics.py`. |
| IV. Simplicity | Pass | One new module (`api.py`). The runner, settings and scheme loading are reused, not copied (R2, R4, R5). No new dependency, no async variant, no partial results after a refusal. |

Re-checked after Phase 1 design: still passes. Nothing goes into Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/006-tagger-api/
├── spec.md
├── plan.md              # This file
├── research.md          # Phase 0: decisions R1–R9
├── data-model.md        # Phase 1: Input, Tag, Result, Results, Tagger
├── quickstart.md        # Phase 1: validation scenarios
├── contracts/
│   └── api.md           # the public Python API
├── checklists/requirements.md
└── tasks.md             # Phase 2 (/speckit-tasks)
```

### Source Code

```text
tools/topic-tagger/
├── src/topic_tagger/
│   ├── __init__.py       # CHANGED: re-exports and __all__; version 0.2.0
│   ├── api.py            # NEW: Tagger, tag, classify, Result, Results, Tag, RemoteModelError,
│   │                     #   the in-memory record sink, input conversion
│   ├── scheme.py         # CHANGED: parse_scheme(text, source) split out of load_scheme
│   ├── run_settings.py   # CHANGED: settle(given, scheme, label) with the CLI's checks
│   ├── variables.py      # CHANGED: variable_from_dict, the public name for the line parser
│   ├── runner.py         # CHANGED: store typed as a RecordSink protocol
│   └── cli.py            # CHANGED: _settle calls run_settings.settle; output unchanged
├── tests/
│   ├── test_api.py       # NEW: US1–US4, errors, no side effects, CLI equivalence
│   ├── test_scheme.py    # extended: parse_scheme, same hash as load_scheme
│   └── test_run_settings.py  # extended: settle's checks and notes
├── pyproject.toml        # CHANGED: version 0.2.0
└── README.md             # CHANGED: "Using it from Python"
```

**Structure Decision**: The work stays inside `tools/topic-tagger/`. `api.py` is the only
new module and the only one callers need. Shared logic stays where it is and is reused.

## Delivery

The branch is based on `005-configurable-classifier` (PR #51), since the API depends on
`[run]`, `[questions]` and tiers. The PR targets `005-configurable-classifier` until #48
and #51 merge.

## Complexity Tracking

None.
