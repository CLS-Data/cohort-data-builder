# Implementation Plan: A configurable classification pipeline for the Topic Tagger

**Branch**: `005-configurable-classifier` | **Date**: 2026-11-16 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/005-configurable-classifier/spec.md`

## Summary

The scheme file becomes the whole pipeline. It holds:
- a taxonomy of one to three tiers;
- the guidance;
- optional wording for each tier's question;
- an optional `[run]` section: provider, model, method and thresholds.

**The tree:** the loader turns both file forms into one category tree:
- the new nested `categories` form;
- the 004 `domains`/`topics` form, which keeps its hash.

`Scheme` keeps its current views (`topics`, `domains`, `domain_of`), now derived from the
tree, so prompts, statistics and reports need no rewrite.

**The walk:** tiered tagging already walks a tree of any height (`tiered.walk`). This
feature makes three changes:
- builds deeper trees;
- treats only the fallback as an exit;
- uses the walk for flat tagging with a decision model, over a one-tier tree of every leaf.

**The option limit:** the decision provider stops checking 2–26 options. When Ollama refuses
a question because it has too many options, the provider raises `OptionLimitError`. The
runner then:
- stops the run at once;
- keeps what was stored;
- records why it stopped;
- exits with a new status, 5.

**Settings:** each one comes from the command line if given, else the file, else the
default. `run.json` records where each came from.

## Technical Context

**Language/Version**: Python 3.12 (the tagger's own project, `tools/topic-tagger/`)

**Primary Dependencies**: Existing only: pydantic, langchain-core, openai, rich. The file is
read with `tomllib`, and `/v1/systemone` is called with `urllib` (both standard library). No
new dependencies.

**Storage**: Files in the output folder, as in 004:
- `tags.jsonl`: records gain nothing new; `path` can now hold two entries for three tiers.
- `scheme.json`: gains a `categories` tree, and keeps a derived `domains` list.
- `run.json`: gains `settings_source`, `tiers` and `stop_reason`.

**Testing**: pytest with scripted fake models and the existing local fake server (no Ollama
needed). New fixtures:
- one-, two- and three-tier taxonomies, the three-tier one uneven;
- a scheme with `[run]` and `[questions]`;
- a fake decision host that refuses too many options with a 400.

**Target Platform**: A maintainer's machine (macOS, Linux, Windows), offline apart from the
model host.

**Project Type**: CLI tool (a standalone Python project inside the repo)

**Performance Goals**: No change per request.
- Decision flat: 1 request per variable.
- Decision tiered: 1 + (groups followed) per variable, at each tier below the first.
- LLM: per batch, as in 004.

**Constraints**:
- Existing 004 scheme files and output folders keep working, and keep their hashes
  (FR-004, SC-003).
- No built-in option limit (FR-009).
- No change to `scripts/topics.py` or the site.

**Scale/Scope**: Taxonomies of up to 3 tiers and a few hundred categories. Runs of 10⁴–10⁵
variables, as in 004.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | How |
|---|---|---|
| I. Test-driven | Pass | Every change starts with a failing test (see quickstart and tasks). The fakes cover the decision host's refusal, so no network is needed and tests stay deterministic. |
| II. Documented code | Pass | Docstrings on every new module, class and function. `README.md`, `docs/formats.md` and the bundled example schemes are updated in the same change (FR-022). |
| III. Static GitHub Pages | Pass, not affected | The tagger is an offline maintainer tool, as in 002/004. Nothing is added to `site/`. `scheme.json` keeps its `domains` view, so `scripts/topics.py` merges as before. |
| IV. Simplicity | Pass | No new dependency. One tree replaces the domain/topic special case, and the 004 views are derived from it rather than kept beside it. The walk is reused for decision-flat instead of writing a second path. |

Re-checked after Phase 1 design: still passes. Nothing goes into Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/005-configurable-classifier/
├── plan.md              # This file
├── research.md          # Phase 0: decisions R1–R10
├── data-model.md        # Phase 1: taxonomy, run settings, records
├── quickstart.md        # Phase 1: validation scenarios
├── contracts/
│   ├── cli.md           # options, precedence, exit status 5, check-scheme output
│   └── formats.md       # the scheme file (both forms), scheme.json, run.json changes
└── tasks.md             # Phase 2 (/speckit-tasks)
```

### Source Code

```text
tools/topic-tagger/
├── src/topic_tagger/
│   ├── scheme.py           # CHANGED: Category tree, both forms, [questions], [run], depth ≤ 3
│   ├── run_settings.py     # NEW: RunSettings; precedence CLI > file > default, with sources
│   ├── tiered.py           # CHANGED: build_tree for any depth, flat_tree, exits = fallback only,
│   │                       #   tier questions, OptionLimitError passes through the walk;
│   │                       #   choice_problems removed
│   ├── prompt.py           # CHANGED: flat prompt groups leaves by path; tier question line
│   ├── providers/
│   │   ├── __init__.py     # CHANGED: OptionLimitError(ProviderError)
│   │   └── ollama_decision.py  # CHANGED: no 2–26 check; reads the host's error body
│   ├── runner.py           # CHANGED: decision-flat through walk; stop on OptionLimitError
│   ├── cli.py              # CHANGED: settings from the file; --max-follow; exit 5;
│   │                       #   check-scheme sizes; dry run shows every tier
│   ├── display.py, stats.py, report.py   # CHANGED only if a test shows the derived views fall short
│   └── schemes/
│       ├── closer.toml     # unchanged (004 form)
│       ├── example-1-tier.toml   # NEW
│       └── example-3-tier.toml   # NEW (uneven, with [questions] and [run])
├── tests/
│   ├── fixtures/scheme_1tier.toml, scheme_3tier.toml, scheme_run.toml   # NEW
│   ├── test_scheme.py, test_tiered.py, test_runner.py, test_cli.py,
│   │   test_decision_provider.py, test_prompt.py   # extended
│   └── test_run_settings.py # NEW
├── README.md               # CHANGED
└── docs/formats.md         # CHANGED
```

**Structure Decision**: All the work is inside `tools/topic-tagger/`, which stays
self-contained (feature 002's rule). The only new module is `run_settings.py`, kept apart so
that precedence can be tested without the CLI.

## Complexity Tracking

None.
