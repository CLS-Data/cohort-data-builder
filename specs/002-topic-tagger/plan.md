# Implementation Plan: Topic Tagger

**Branch**: `002-topic-tagger` | **Date**: 2026-10-27 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/002-topic-tagger/spec.md`

## Summary

The tagger is a standalone Python command-line tool, `topic-tagger`, in
`tools/topic-tagger/`:
- It reads a simple `variables.jsonl`.
- It asks a model which topics each variable belongs to, using the
  maintainer's TOML scheme and guidance. The model is served by Ollama through its
  OpenAI-compatible API, called with the official `openai` SDK behind a one-method `Provider`
  interface, so other hosts can be added later.
- It writes resumable `tags.jsonl`, `scheme.json`, `run.json` and a self-contained HTML
  report.
- It shows a live `rich` display while running.

A standard-library processing script, `scripts/topics.py`, in the site's part of the
repository, exports a cohort from `site/data` and merges the tags back. The tool's design
ports the PoC tagger (`PoC/enrich/`) without LangChain or YAML.

## Technical Context

**Language/Version**: Python 3.12, for both the tool and the processing script.

**Primary Dependencies**:
- Tool: `openai` (the model client; it brings in `httpx` and `pydantic`), `pydantic`
  (validating replies) and `rich` (the live display).
- Dev: `pytest`, `ruff`.
- Processing script: standard library only.

**Storage**: Files only: JSONL, JSON, TOML and HTML (see [contracts/formats.md](contracts/formats.md)).

**Testing**: pytest.
- The tool's tests use a stand-in `Provider` with scripted replies, plus a local fake HTTP
  server for the `openai` provider and the pre-flight check. They need no network access and
  no Ollama.
- The processing script's tests use fictional cohort fixtures.

**Target Platform**: The maintainer's macOS, Linux or Windows machine, with Ollama
installed. The tests also run on CI (ubuntu-latest).

**Project Type**: A command-line tool (its own package), plus a repository script.

**Performance Goals**:
- The live display updates at least once a second (SC-004).
- Tagging speed is set by the model. The tool adds less than 5% overhead per request.
- Loading 32,000 tag records takes under 2 seconds.

**Constraints**:
- No study data, only metadata (FR-004).
- An interrupted run loses at most the batches in flight (FR-012).
- No import between the tool and the site, in either direction (FR-023, FR-028).
- An API key is read only from the environment.

**Scale/Scope**: Up to about 35,000 variables per cohort, about 100 topics, and one
maintainer at a time.

## Constitution Check

*GATE: checked before Phase 0 research, and again after Phase 1 design.*

| Principle | Status | How |
|---|---|---|
| I. Test-driven development | Pass | Every module is test-first. The tests are deterministic: a stand-in model and a local fake server, no real network or Ollama. Times are injected through a clock. Both test suites run in CI on every push and pull request. |
| II. Documented code | Pass | Google-style docstrings throughout. The tool has its own `README.md` (install, use, scheme editing, formats). The formats are documented in `tools/topic-tagger/docs/formats.md`, from contracts/formats.md. The site's `docs/data-format.md` gets a "Adding topics" section, and the root README links to the tool. |
| III. Static GitHub Pages deployment | Pass (not affected) | Neither the tool nor the script ships with the site or runs in the browser. The site still only reads static files. The Pages build does not include `tools/` or `scripts/`. |
| IV. Simplicity | Pass, with notes | Three runtime dependencies, each needed (R1, R3, R4): `openai` for the model protocol and future hosts, `pydantic` for one definition of schema and validation, `rich` for the live display the spec asks for. Charts are hand-written SVG instead of a plotting library (R5). The scheme is TOML, read by the standard library, instead of YAML (R2). The `Provider` interface is the one new abstraction, recorded below. |
| Quality gates | Pass | `ci` gains the processing script's tests. A new `topic-tagger` workflow runs the tool's lint and tests. Every pull request has a "How to review" section. |

**After design**: still passes. The design adds no runtime code to the site and no
dependency to the site's tooling. The site-side change is `scripts/topics.py`, and moving
the standard-library data checks from `tests/python/data/checks.py` to `scripts/checks.py`
so the merge can run them. Its tests keep importing them; only the import path changes.

## Project Structure

### Documentation (this feature)

```text
specs/002-topic-tagger/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── cli.md
│   └── formats.md
└── tasks.md             (made by /speckit-tasks)
```

### Source Code

```text
tools/topic-tagger/                  self-contained: copy it anywhere and it works
├── pyproject.toml                   package topic-tagger, command topic-tagger, own ruff/pytest settings
├── uv.lock
├── README.md                        install, quick start, scheme editing, options, privacy
├── docs/formats.md                  the file formats (contracts/formats.md)
├── src/topic_tagger/
│   ├── __init__.py
│   ├── __main__.py                  python -m topic_tagger
│   ├── cli.py                       argparse: tag, check-scheme, init-scheme, report; exit codes
│   ├── scheme.py                    load and validate scheme.toml; hash; topic numbers
│   ├── variables.py                 read variables.jsonl; keys; duplicate check
│   ├── prompt.py                    build the messages and the reply's JSON schema
│   ├── reply.py                     pydantic reply model from the scheme; clean tags
│   ├── providers/
│   │   ├── __init__.py              Provider protocol and get_provider(name)
│   │   └── openai_compat.py         OpenAI-compatible chat (Ollama now); pre-flight /v1/models
│   ├── store.py                     tags.jsonl append, load, states, compact; lock file
│   ├── runner.py                    batches, thread pool, retries, singles; events to the display
│   ├── display.py                   rich live view, or plain progress lines
│   ├── stats.py                     run statistics from the current records
│   ├── report.py                    report.html, with charts from svg.py
│   ├── svg.py                       bars, histogram, heat grid, line, as inline SVG
│   └── schemes/closer.toml          the bundled scheme (converted from the PoC)
└── tests/
    ├── conftest.py                  stand-in provider, fake clock, fixture paths
    ├── fixtures/                    variables.jsonl (about 60 fictional variables), small schemes
    ├── test_scheme.py  test_variables.py  test_prompt.py  test_reply.py
    ├── test_provider.py             against a local fake HTTP server
    ├── test_store.py  test_runner.py  test_display.py
    ├── test_stats.py  test_svg.py  test_report.py
    ├── test_cli.py                  end to end with the stand-in provider
    └── test_independence.py         nothing outside tools/topic-tagger is imported or read

scripts/
├── topics.py                        export / merge (standard library)
└── checks.py                        the site data checks, moved from tests/python/data/

tests/python/topics/
├── test_export.py
├── test_merge.py
└── test_independence.py             scripts/topics.py imports nothing from tools/

.github/workflows/topic-tagger.yml   runs on changes under tools/topic-tagger/
```

**Structure decision**:
- **The tool:** it is one uv project in `tools/topic-tagger/`, with a `src/` layout, so its
  tests run against the installed package rather than loose files.
- **Root config:** the root `pyproject.toml` adds `tools` to ruff's `extend-exclude`. pytest
  already collects only `tests/python`.
- **Imports:** pytest's `pythonpath` gains `scripts`, so the site tests import `checks` and
  `topics` directly.

## Design notes

- **Prompt:** the system message carries the guidance, each topic as `id: label —
  description` grouped by area, and the rules on the reply's shape. The user message carries
  the batch as JSON lines (`id`, `name`, `label`, up to 30 value labels). The ids are short
  batch-local numbers, mapped back after the reply, so the reply cannot get variable names
  wrong.
- **Reply schema:** `{"variables": [{"id": int, "topics": [{"topic": enum, "confidence":
  number 0..1}]}]}`. It is sent as `response_format={"type": "json_schema", ...}`, and
  checked again with the same pydantic model.
- **Retry ladder:** each batch goes through these steps.
  1. The batch is sent.
  2. A failure (a timeout, invalid JSON or a schema error) is retried up to `retries` times.
  3. The batch's variables are then sent one at a time, once each.
  4. Any still failing are recorded as failed.
  5. Variables the reply left out go straight to step 3.
- **Events:** the runner sends simple events (`batch_done`, `retry`, `failed`) to the
  display and the statistics, so the display can be tested without a terminal.
- **Ctrl-C:** stops the workers from taking new batches and waits up to `timeout` for the
  batches in flight. Then it compacts the store, writes `run.json` and the report, and exits
  with code 130. A second Ctrl-C exits at once; the store is still valid because it is
  append-only.
- **Remote check:** before any request, the tool decides whether the model is remote (R8)
  and, if so, asks for confirmation.
- **Pre-flight:** before tagging, the tool fetches `GET {base}/models` and checks that the
  model is in the list.
- **Report:** CSS custom properties with a `prefers-color-scheme` block. The palette follows
  the site's tokens, so it looks like the site. There is no JavaScript; numbers are shown as
  text beside each bar.

## Complexity Tracking

| Addition | Why needed | Simpler alternative rejected because |
|---|---|---|
| `Provider` interface (one method) | The user asked for Ollama now and other hosts later. It is also the seam the stand-in model plugs into for tests (FR-025). | Calling `openai` directly from the runner would hard-wire one protocol, and the tests would need a fake HTTP server everywhere. |
| A second Python project (`tools/topic-tagger/`) with its own lockfile and workflow | FR-023 and FR-024 and SC-006: the tool must be independent and copyable. | Sharing the root project would tie the tool's dependencies and tests to the site's. |
| Moving `checks.py` to `scripts/` | The merge must run the site's data checks (US6, scenario 4). Importing from `tests/` would be fragile. | Duplicating the checks would let the two copies drift apart. |
