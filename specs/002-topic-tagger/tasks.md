---
description: "Task list for the topic tagger"
---

# Tasks: Topic Tagger

**Input**: Design documents from `specs/002-topic-tagger/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/cli.md,
contracts/formats.md, quickstart.md

**Tests**: Required. Constitution Principle I is non-negotiable. Each story's test tasks come
first:
1. Write the tests, run them and see them fail.
2. Commit them as `test(…)`.
3. Implement until they pass, and commit as `feat(…)` or `fix(…)`.

The tool's tests never touch the network or Ollama. They use the stand-in provider (T008),
the fake HTTP server (T009) and the fake clock (T008).

**Paths**:
- `tools/topic-tagger/` is abbreviated `TT/`. Its source is `TT/src/topic_tagger/` and its
  tests are `TT/tests/`.
- The site-side code is in `scripts/` and `tests/python/topics/`.

**Commands**:

| Where | Command |
|---|---|
| Tool, from `TT/` | `uv run pytest` and `uv run ruff check . && uv run ruff format --check .` |
| Site, from the repository root | `uv run pytest tests/python/data tests/python/topics` |

**Format**: `[ID] [P?] [Story] Description`. `[P]` means the task can run in parallel, with
different files and no unfinished dependency.

## Phase 0: Version control

Follow `CONTRIBUTING.md`:
- **Integration branch:** `002-topic-tagger`, already on GitHub with the spec, plan and
  design.
- **Phase branches:** each phase below gets its own short branch off it, named
  `002-setup`, `002-foundation`, `002-us1-tag` and so on.
- **Pull requests:** one per phase, into `002-topic-tagger`, with a filled *How to review*,
  squash-merged.
- **Release:** when the feature is done, one integration pull request goes from
  `002-topic-tagger` to `main`, followed by the release `v0.2.0`.

- [ ] T001 Push `002-topic-tagger` to GitHub. Ask the user to add `002-topic-tagger` to the `release-branch` ruleset, or to a new matching rule (pull request required, linear history), and to make `ci`, `pr-description` and, once T005 exists, `topic-tagger` required checks on it and on `main-protection`.
- [x] T002 Supersede 001 FR-029 for topic tagging only: in `specs/001-cohort-data-builder/spec.md`, add a note under FR-029 that points to `specs/002-topic-tagger/spec.md`. Update `CLAUDE.md` so it names spec 002 beside 001 and gives the tool's commands (the table above).

**Checkpoint**: the integration branch is protected, and the docs say which spec governs
which area.

---

## Phase 1: Setup (branch `002-setup`)

- [ ] T003 Create `TT/pyproject.toml`:
  - project `topic-tagger`, `requires-python = ">=3.12"`;
  - dependencies `openai`, `pydantic>=2` and `rich`, at the latest releases at least two
    weeks old, pinned with `>=` and locked by `uv.lock`;
  - a `[dependency-groups] dev` group with `pytest` and `ruff`;
  - `[project.scripts] topic-tagger = "topic_tagger.cli:main"`;
  - hatchling build with a `src/` layout;
  - ruff with `line-length = 100`, rules `E,F,I,UP,B,D` and Google pydocstyle (the same rules
    as the root);
  - pytest with `testpaths = ["tests"]`.

  Create `TT/src/topic_tagger/__init__.py` (a module docstring and `__version__ = "0.1.0"`),
  `TT/src/topic_tagger/__main__.py` (calls `cli.main()`), and a `TT/src/topic_tagger/cli.py`
  stub whose `main()` returns 0. Run `uv lock` in `TT/`.
- [ ] T004 [P] In the root `pyproject.toml`, add `"tools"` to ruff's `extend-exclude`. Add `TT/.gitignore` with `.venv/`, `__pycache__/` and `.pytest_cache/`.
- [ ] T005 [P] Add `.github/workflows/topic-tagger.yml`:
  - triggers: every `push` and `pull_request`, with no `paths` filter. A required check
    that never runs stays "pending" for ever and blocks the merge;
  - a first step (`actions/checkout` with `fetch-depth: 0`, then `git diff --name-only`
    against the pull request's base, or against the previous commit on a push) decides
    whether anything under `tools/topic-tagger/` or this workflow file changed. When nothing
    did, it prints "topic-tagger unchanged: nothing to test" and the remaining steps are
    skipped with `if:`, so the job still reports success;
  - one job, `topic-tagger`, on `ubuntu-latest`, with `working-directory: tools/topic-tagger`;
  - steps: `actions/checkout` and `astral-sh/setup-uv`, pinned to SHAs as in `ci.yml`, then
    `uv sync --locked`, `uv run ruff check .`, `uv run ruff format --check .` and
    `uv run pytest`.
- [ ] T006 [P] Write a skeleton `TT/README.md`: what the tool does, install (`uv sync` in this folder, or `uv tool install .`), and a one-line usage. The rest is filled in later phases.

**Checkpoint**: `uv run pytest` in `TT/` reports no tests and exits cleanly. The root CI is
unchanged and green.

---

## Phase 2: Foundation (branch `002-foundation`)

These block every story.

### Fixtures and test harness

- [ ] T007 [P] Create `TT/tests/fixtures/`:
  - `variables.jsonl`: 60 fictional variables across 3 files (`alpha`, `beta`, `gamma`) and
    2 sweeps (`0y`, `5y`). It includes one `identifier: true` row (`PID`), one row with no
    label, one with 200 value labels, and one with no sweep. No real study data.
  - `scheme_small.toml`: 3 domains and 8 topics, including `identifiers` and `other`, with
    `identifier_topic` and `fallback_topic` set.
- [ ] T008 Create `TT/tests/conftest.py` with:
  - `StubProvider`: implements the `Provider` protocol (T011). It is built from a function
    `(messages, schema) -> str`, or from a queue of replies or exceptions. It records every
    call.
  - `FakeClock`: has `now()` and `advance(s)`.
  - fixtures `fixtures_dir`, `small_scheme` and `variables_path`.

### Core modules (tests first)

- [ ] T009 [P] Write `TT/tests/test_variables.py` (tests fail first). `read_variables(path)`:
  - returns `Variable(file, variable, label, values, sweep, identifier)` records in file
    order;
  - ignores blank lines;
  - treats a missing `label`, `values` or `sweep` as absent;
  - raises `InputError` that lists every duplicate `file/variable` key, ignoring case, with
    line numbers;
  - raises `InputError` naming the line on bad JSON, or on an empty `file` or `variable`.

  `Variable.key` is `"file/variable"`.
- [ ] T010 [P] Write `TT/tests/test_scheme.py`, loading only (validation is in US3). Tests:
  - `load_scheme(path)` returns a `Scheme` with `name`, `version`, `guidance`,
    `identifier_topic`, `fallback_topic` and `domains`;
  - `scheme.topic_ids` is in order;
  - `scheme.topic_number(id)` counts from 0 across the whole scheme;
  - `scheme.domain_of(topic_id)`;
  - `scheme.hash` is 12 hex characters, stable for the same content, and changes when any
    description or the guidance changes;
  - `scheme.to_json()` has the shape in contracts/formats.md `scheme.json`;
  - loading the bundled scheme with `load_scheme(None)` works.
- [ ] T011 Implement `TT/src/topic_tagger/variables.py` to pass T009.
- [ ] T012 Implement `TT/src/topic_tagger/scheme.py` to pass T010:
  - `tomllib` and dataclasses;
  - hash is `sha256(json.dumps(content, sort_keys=True, separators=(",", ":")))`, first 12
    characters;
  - `load_scheme(None)` reads `importlib.resources.files("topic_tagger") / "schemes/closer.toml"`.
- [ ] T013 [P] Create `TT/src/topic_tagger/schemes/closer.toml` by converting `PoC/schema/topics.yaml` once, by hand or with a one-off script that is not committed:
  - all 15 domains and about 100 topics, with their descriptions, `closer`, `cessda` and
    `added`;
  - the guidance text;
  - `identifier_topic = "identifiers"` and `fallback_topic = "other"`.

  Keep the explanatory header comment, rewritten for TOML. Add a test to
  `TT/tests/test_scheme.py` that it loads, with 15 domains and more than 90 topics.
- [ ] T014 Write `TT/tests/test_provider.py` (tests fail first) against a local fake server:
  `http.server` on a free port in a thread, serving `/v1/models` and `/v1/chat/completions`
  with scripted responses. `OpenAICompatProvider(base_url, model, api_key, timeout)` should:
  - `.check()`: pass when the model is listed; raise `ProviderError("model … is not
    installed; run: ollama pull …")` when it is not; raise `ProviderError("… is not reachable
    at …")` when the connection is refused;
  - `.complete(messages, schema)`: send `response_format={"type": "json_schema",
    "json_schema": {"name": "tags", "schema": schema, "strict": true}}` and return the
    content string;
  - raise `ProviderError` after the timeout;
  - take the API key from the `api_key` argument, defaulting to `"ollama"`;
  - `is_remote()`: follow R8, so host `localhost`, `127.0.0.1` or `::1` is local, and a model
    name ending in `-cloud` is remote.

  `get_provider("ollama", …)` returns it. An unknown name raises `ProviderError`, listing the
  known providers.
- [ ] T015 Implement `TT/src/topic_tagger/providers/__init__.py` (the `Provider` Protocol with `complete`, `check` and `is_remote`; `ProviderError`; `get_provider`) and `TT/src/topic_tagger/providers/openai_compat.py` (using `openai.OpenAI(base_url=…, api_key=…, timeout=…, max_retries=0)`) to pass T014.

**Checkpoint**: foundation tests pass; `topic-tagger` runs (it does nothing yet).

---

## Phase 3: User Story 1 - Tag a cohort's variables (P1) 🎯 MVP (branch `002-us1-tag`)

**Goal**: tag every variable with scheme topics and confidences from 0 to 1, and write the
output folder.

**Independent test**: `TT/tests/test_cli.py::test_tags_every_variable` runs `tag` on the
fixtures with a stand-in provider. Every input variable then has a record, every topic is in
the scheme, and every confidence is from 0 to 1.

### Tests for User Story 1 ⚠️ write first, see them fail

- [ ] T016 [P] [US1] `TT/tests/test_prompt.py`. `build_messages(scheme, batch)` returns `[system, user]`:
  - **System message:** contains the guidance, every topic as `id: label — description`
    under its domain label, and the reply rules. The rules include "if nothing fits, use
    `<fallback_topic>` with a low confidence", naming the scheme's `fallback_topic`. A test
    with a different `fallback_topic` shows the name comes from the scheme.
  - **User message:** one JSON line per variable with `id` (the position in the batch, 0…n-1),
    `name`, `label` and `values`. `values` holds at most 30 entries, followed by `"… and N
    more"` when it is cut.

  `reply_schema(scheme)` gives a JSON schema whose `topic` is an `enum` of exactly
  `scheme.topic_ids` and whose `confidence` has `minimum` 0 and `maximum` 1.
- [ ] T017 [P] [US1] `TT/tests/test_reply.py`. `parse_reply(text, scheme, batch_size)` returns `{batch id: [(topic, confidence), …]}`. It must:
  - reject invalid JSON, an unknown topic, a confidence outside 0–1, or an id outside the
    batch, raising `ReplyError`;
  - merge duplicate topics, keeping the highest confidence;
  - round confidences to 2 decimal places;
  - sort tags strongest first, with ties in scheme order;
  - leave out ids that have no tags, so the caller treats them as missing.
- [ ] T018 [P] [US1] `TT/tests/test_store.py` (writing only; resuming is in US2). `TagStore(out_dir)`:
  - creates the folder;
  - `.write_scheme(scheme)` writes `scheme.json`;
  - `.append(records)` appends one JSON line per record to `tags.jsonl` and flushes;
  - each record has `file`, `variable`, `topics`, `scheme`, `model` and `tagged`, with
    `tagged` in ISO UTC from the injected clock.
- [ ] T019 [US1] `TT/tests/test_runner.py`. `Runner(scheme, provider, store, settings, clock, on_event)`:
  - **Batches:** with batch size 20, sends 3 batches for 60 variables.
  - **Identifier:** tags the identifier row by rule, with `[[identifier_topic, 1.0]]` and
    `model: "rule"`, and never sends it.
  - **Retries:** retries a batch that raised `ReplyError` or `ProviderError` up to `retries`
    times.
  - **One at a time:** then sends each of its variables on its own. A variable whose single
    reply also fails is recorded as failed.
  - **Missing variables:** sends variables a reply left out on their own.
  - **No label:** a variable with no label that gets a valid reply naming `other` is stored
    with it.
  - **Events:** emits `batch_done(n, tags)`, `retry` and `failed(key)` events.
  - **Workers:** with `workers=2`, never has more than 2 calls in flight.
- [ ] T020 [US1] `TT/tests/test_cli.py`. Tests:
  - **Tags everything:** `test_tags_every_variable`, as above.
  - **Exit 2:** `tag` on a missing input file.
  - **Exit 3:** when `provider.check()` fails, with the message on stderr and no `complete`
    call.
  - **Dry run:** `--dry-run` prints the system message and the first batch's user message to
    stdout, makes no `complete` call, exits 0, and works when `check()` would fail.
  - **Remote model:** with a remote model and no `--yes` while stdin is not a terminal, it
    exits 2 with the R8 message and sends nothing. With `--yes`, it proceeds.
  - **Exit 1:** when some variables fail, with the failed keys listed on stderr.

  The tests inject the provider through `cli.main(argv, provider_factory=…)`.

### Implementation for User Story 1

- [ ] T021 [P] [US1] Implement `TT/src/topic_tagger/prompt.py` to pass T016.
- [ ] T022 [P] [US1] Implement `TT/src/topic_tagger/reply.py` to pass T017: a pydantic model is built from the scheme with `Literal[*topic_ids]` and `confidence: float = Field(ge=0, le=1)`, and `reply_schema` is that model's `model_json_schema()`.
- [ ] T023 [P] [US1] Implement the writing part of `TT/src/topic_tagger/store.py` to pass T018.
- [ ] T024 [US1] Implement `TT/src/topic_tagger/runner.py` to pass T019: a `concurrent.futures.ThreadPoolExecutor(max_workers=workers)`, with the retry ladder as in the plan's design notes. Records are appended to the store from the main thread as futures complete.
- [ ] T025 [US1] Implement the `tag` command in `TT/src/topic_tagger/cli.py` to pass T020:
  - `argparse`, with every option and default in contracts/cli.md;
  - the exit codes as listed there;
  - `TOPIC_TAGGER_BASE_URL` and `TOPIC_TAGGER_API_KEY` read from the environment;
  - a remote-model prompt that uses `input()` only when stdin is a terminal.

  For now, end with a one-line plain summary on stdout; the live display comes in US4.
- [ ] T026 [US1] Add a "Tag a cohort" section to `TT/README.md`: prerequisites (Ollama, `ollama pull gpt-oss:20b`), the `tag` command, the dry run, the exit codes, and the privacy note about remote and `-cloud` models.

**Checkpoint**: on a machine with Ollama, `uv run topic-tagger tag tests/fixtures/variables.jsonl --out /tmp/x` tags all 60 variables.

---

## Phase 4: User Story 2 - Stop and carry on (P1) (branch `002-us2-resume`)

**Goal**: runs resume. Out-of-date tags are redone, and `--retag`, `--files`, `--limit`,
the lock and Ctrl-C all work.

**Independent test**: `test_cli.py::test_resume_after_interrupt`. The stand-in provider
calls `runner.request_stop()` on its 2nd call; a real Ctrl-C reaches the same method through
the CLI's SIGINT handler. The run exits 130. A second run sends only the
untagged variables, and the final `tags.jsonl` equals that of an uninterrupted run.

### Tests for User Story 2 ⚠️ write first, see them fail

- [ ] T027 [P] [US2] Add to `TT/tests/test_store.py`:
  - **States:** `.load()` reads existing records, the last line for each key wins, and a
    truncated final line is ignored. `.state(key, scheme_hash)` returns `missing`, `stale` or
    `current`.
  - **Compact:** `.compact()` rewrites `tags.jsonl` sorted by `(file, variable)`, one line
    per key, through a temporary file and `os.replace`.
  - **Lock:** `.lock()` creates `.lock` containing the process id. A second `.lock()` while
    that process is alive raises `LockedError`. A lock whose process id is not running raises
    `StaleLockError`, unless called with `force=True`. `.unlock()` removes the lock.
- [ ] T028 [US2] Add to `TT/tests/test_cli.py`:
  - **Resume:** `test_resume_after_interrupt`, as above.
  - **Scheme change:** after a description is changed in a copy of the scheme, every
    variable is re-sent.
  - **`--retag`:** re-sends current variables.
  - **`--files beta`:** sends only `beta` variables.
  - **`--limit 5`:** sends 5.
  - **Lock:** a run whose output folder holds a live lock exits 4.
  - **Ctrl-C:** after an interrupt, `run.json` has `status: "stopped"`, and the lock is gone.
  - **Signal path:** during a run, `signal.raise_signal(signal.SIGINT)` from the main thread
    calls `request_stop()`, and a second SIGINT exits at once. Skipped on Windows.

### Implementation for User Story 2

- [ ] T029 [US2] Implement loading, states, compacting and locking in `TT/src/topic_tagger/store.py` to pass T027. Use `os.kill(pid, 0)` to check whether a process is alive, falling back on Windows to treating the lock as live, so the user must pass `--force`.
- [ ] T030 [US2] Update `TT/src/topic_tagger/runner.py` and `TT/src/topic_tagger/cli.py` to pass T028:
  - **Selecting:** pick variables by state, `--retag`, `--files` and `--limit`.
  - **Lock:** take it before any request and release it in `finally`.
  - **Stopping:** `Runner.request_stop()` sets a `threading.Event`, and workers take no new
    batches once it is set. Python delivers Ctrl-C only to the main thread, so the CLI
    installs a SIGINT handler there that calls `request_stop()`. Never rely on
    `KeyboardInterrupt` raised inside a worker.
  - **First Ctrl-C** (or `request_stop()`): workers take no new batches, wait up to `timeout`
    for the batches in flight, compact, write `run.json` (status, settings, counts and
    failed), and exit 130.
  - **Second Ctrl-C:** exit at once.
- [ ] T031 [US2] Add a "Stopping and resuming" section to `TT/README.md`: what is redone and when, plus `--retag`, `--files`, `--limit` and `--force`.

**Checkpoint**: stopping and restarting a real run repeats only the batches that were in
flight.

---

## Phase 5: User Story 3 - Control the topics and instructions (P1) (branch `002-us3-scheme`)

**Goal**: the maintainer edits one TOML file. The tool validates it and lists every mistake.

**Independent test**: `test_cli.py::test_check_scheme_lists_every_mistake`. A scheme with a
duplicate id, a bad id, an empty domain and a missing description gives exit 2, with all
four problems and their locations on stderr.

### Tests for User Story 3 ⚠️ write first, see them fail

- [ ] T032 [P] [US3] Add to `TT/tests/test_scheme.py`: `validate(raw)` returns a list of `SchemeProblem(location, message)`, and `load_scheme` raises `SchemeError(problems)` when that list is not empty. It must find:
  - an id that does not match `^[a-z][a-z0-9_]*$`, at e.g. `domains[1].topics[0].id`;
  - an id used twice anywhere in the scheme, naming both locations;
  - a domain with no topics;
  - a missing or empty `label` or `description` on a domain or topic;
  - a missing `name`, `version` or `guidance`;
  - `identifier_topic` or `fallback_topic` not naming a topic in the scheme;
  - invalid TOML, with its line number.

  Every problem is reported, not only the first.
- [ ] T033 [US3] Add to `TT/tests/test_cli.py`:
  - **`check-scheme`:** exits 0 and prints "N domains, M topics, hash …" for the bundled
    scheme.
  - **Mistakes:** `test_check_scheme_lists_every_mistake`, as above.
  - **`init-scheme PATH`:** writes a copy of the bundled scheme, and refuses to overwrite an
    existing file (exit 2).
  - **Edits reach the prompt:** after the guidance and a topic description are edited,
    `tag --dry-run --scheme PATH` shows the new text.
  - **Bad scheme:** `tag` with an invalid scheme exits 2 before any request.

### Implementation for User Story 3

- [ ] T034 [US3] Implement `validate` in `TT/src/topic_tagger/scheme.py`, and call it from `load_scheme`, to pass T032.
- [ ] T035 [US3] Implement `check-scheme` and `init-scheme` in `TT/src/topic_tagger/cli.py` to pass T033.
- [ ] T036 [US3] Add an "Editing the topics and instructions" section to `TT/README.md`:
  - the file layout, with an annotated excerpt;
  - which edits make tags out of date (all of them);
  - "rename an id only if you mean to retag";
  - keeping several schemes, and choosing one with `--scheme`.

**Checkpoint**: a maintainer can change the scheme and guidance without touching code
(SC-005).

---

## Phase 6: User Story 4 - Watch a run (P2) (branch `002-us4-display`)

**Goal**: a live display updates at least once a second. When there is no live terminal, it
writes plain progress lines instead.

**Independent test**: `test_display.py`. Feeding the display events and advancing the fake
clock gives a render that contains each figure. The plain mode writes one line per 10
seconds.

### Tests for User Story 4 ⚠️ write first, see them fail

- [ ] T037 [P] [US4] `TT/tests/test_display.py`. `RunView(total, todo, scheme, clock)` is updated by runner events.
  - **`.snapshot()`** returns `done`, `left`, `percent`, `elapsed`, `eta`, `per_minute`
    (over the last 60 s), `failed`, `retries`, `top_domains` (the leading 5, with counts) and
    `top_topics` (the leading 10).
  - **The live view** (`rich.console.Console(record=True, width=100)`) contains those values,
    and refreshes at 4 per second.
  - **Plain mode** writes a line every 10 seconds to stderr, in the form
    `[00:01:40] 120/600 (20%) 72/min eta 00:06:40 failed 0 retries 1`.
- [ ] T038 [US4] Add to `TT/tests/test_cli.py`: with stderr not a terminal, or with `--plain`, the run writes plain lines and no ANSI escape codes. The final summary's counts equal the number of records in `tags.jsonl` (SC-004).

### Implementation for User Story 4

- [ ] T039 [US4] Implement `TT/src/topic_tagger/display.py` to pass T037:
  - a `rich.live.Live` holding a `Progress` (bar, percent, elapsed, remaining, rate) and two
    `Table`s (leading topic areas and leading topics);
  - a footer with failed and retried counts.
- [ ] T040 [US4] Wire `RunView` into `TT/src/topic_tagger/cli.py` and `TT/src/topic_tagger/runner.py` to pass T038. Mode selection: `--plain`, or `not sys.stderr.isatty()`, gives plain mode. Add a screenshot description and the plain format to `TT/README.md`.

**Checkpoint**: a real run shows progress, speed, remaining time and leading topics live.

---

## Phase 7: User Story 5 - Review the final topic statistics (P2) (branch `002-us5-report`)

**Goal**: an end-of-run summary in the terminal, a `run.json` with `stats`, and a
self-contained `report.html`.

**Independent test**: `test_stats.py`. A hand-built set of 10 records with known topics gives
exactly the expected value for every statistic. `test_report.py` checks that the report
contains each section and makes no external references.

### Tests for User Story 5 ⚠️ write first, see them fail

- [ ] T041 [P] [US5] `TT/tests/test_stats.py`. `compute_stats(records, variables, scheme, run)` is checked against 10 hand-built records, with every field in data-model.md *Run statistics* verified:
  - `per_topic` includes the zeros;
  - `per_domain` counts each variable once per domain;
  - `unused`;
  - `confidence_histogram`, with 10 bins and 1.0 in the last;
  - `below_default`, the share of variables whose strongest tag is under 0.5;
  - `mean_topics`;
  - `per_file` with tagged and failed;
  - `domain_by_sweep`, left empty when there are no sweeps;
  - `speed`.
- [ ] T042 [P] [US5] `TT/tests/test_svg.py`. `bars(items)`, `histogram(bins)`, `heat_grid(rows, cols, values)` and `line(points)` each return an `<svg>` string that:
  - has a `viewBox` and a `<title>`;
  - has one `<rect>` per bar or bin, or one cell per grid entry;
  - labels each value as text;
  - colours only through `var(--…)` CSS variables;
  - handles empty input with a "No data" text instead of failing.
- [ ] T043 [P] [US5] `TT/tests/test_report.py`. `render_report(run, stats, scheme)` returns HTML that:
  - contains the eight sections of contracts/formats.md `report.html`, in order;
  - names the date, model, scheme name and hash;
  - has no `<script`, `src="http`, `href="http` or `@import`;
  - has a `@media (prefers-color-scheme: dark)` block;
  - escapes the variable names it lists, so `<b>` in a label appears as text.
- [ ] T044 [US5] Add to `TT/tests/test_cli.py`:
  - **After a finished run:** the run writes `run.json` with `stats`, writes `report.html`,
    and prints a summary containing tagged, failed, run time, speed, mean topics, share below
    50%, the 10 leading topics, and the unused count.
  - **After Ctrl-C:** the report is written too.
  - **`report DIR`:** rebuilds `report.html` from an existing folder (exit 0).

### Implementation for User Story 5

- [ ] T045 [P] [US5] Implement `TT/src/topic_tagger/stats.py` to pass T041. The runner records a `timeline` entry every 10 seconds from the clock.
- [ ] T046 [P] [US5] Implement `TT/src/topic_tagger/svg.py` to pass T042. Load the `dataviz` skill first, and follow its colour and mark guidance.
- [ ] T047 [US5] Implement `TT/src/topic_tagger/report.py` to pass T043. Use `html.escape` for all text, and inline CSS with light and dark tokens.
- [ ] T048 [US5] Wire the statistics, `run.json`, the summary and the report into `TT/src/topic_tagger/cli.py`, and add the `report` command, to pass T044. Add a "Reading the report" section to `TT/README.md`.

**Checkpoint**: after a real run, `report.html` opens offline and its numbers match the
terminal summary.

---

## Phase 8: User Story 6 - Publish the tags on the site (P2) (branch `002-us6-publish`)

**Goal**: `scripts/topics.py export` and `merge` connect the tool to `site/data`.

**Independent test**: `tests/python/topics/test_merge.py::test_round_trip`:
1. Take the `mini` fixture with its topics removed.
2. Export it.
3. Hand-write a `tags.jsonl` and `scheme.json` for it, as the tool would produce them.
4. Merge.

The site's data checks then report no problems, and the topic fields match the expected
values.

### Tests for User Story 6 ⚠️ write first, see them fail

- [ ] T049 [US6] Move `tests/python/data/checks.py` to `scripts/checks.py` with `git mv`. Add `pythonpath = ["scripts"]` to `[tool.pytest.ini_options]` in the root `pyproject.toml`, and keep `from checks import …` working in `tests/python/data/test_checks.py` and `test_supplied_data.py`. Run `uv run pytest tests/python/data`: it is green, with no behaviour change. Commit as `refactor(data): move the data checks to scripts/`.
- [ ] T050 [P] [US6] `tests/python/topics/test_export.py`. `export(cohort_dir, out)` on the `mini` fixture writes one line per index row, in index order, each with `file`, `variable`, `label` and `values` (`[value, label]` pairs from the dictionary). It also:
  - sets `sweep` to the file's `wave`;
  - sets `identifier: true` only on the manifest `identifier`, matched ignoring case;
  - reads no `topics` field.

  The CLI exits 0, and exits 2 on a folder with no manifest.
- [ ] T051 [P] [US6] `tests/python/topics/test_merge.py`. Tests:
  - **Round trip:** `test_round_trip`, as above.
  - **Manifest:** `manifest.topics` has `name`, `version`, `hash` and `domains`, with no
    `guidance`, `identifier_topic` or `fallback_topic`.
  - **Dictionaries:** `topics` is `[[id, conf], …]`, strongest first.
  - **Index:** element 5 is `[number, round(conf*100), …]`, strongest first. Untagged rows
    have exactly 5 elements.
  - **Reports without stopping:** records for unknown variables, variables with no record,
    and stale records whose scheme hash differs are each reported. Stale records are skipped.
  - **Nothing else changes:** with the topic fields removed, each file parses to the same
    JSON as before the merge. A second merge of the same tags leaves every file unchanged,
    byte for byte.
  - **Exit codes:** 1 when the checks find problems, for example after a hand-corrupted
    `scheme.json`; 2 on bad input.
- [ ] T052 [P] [US6] `tests/python/topics/test_independence.py`: `scripts/topics.py` does not import from `tools` or `topic_tagger`, and no file under `site/` refers to `tools/`.

### Implementation for User Story 6

- [ ] T053 [US6] Implement `scripts/topics.py` (standard library, Google-style docstrings, `argparse` subcommands `export` and `merge`) to pass T050 to T052. Write JSON with `separators=(",", ":")` and `ensure_ascii=False`, matching the existing files. Each file goes to a temporary file and is then replaced. The merge ends by calling `checks.check_data`.
- [ ] T054 [US6] Add an "Adding topics" section to `docs/data-format.md`: data arriving without topics, then export, the tool, merge, and the checks, with the three commands. Link to `tools/topic-tagger/README.md`.

**Checkpoint**: a cohort without topics can be published with topics in three commands
(SC-008).

---

## Phase 9: Polish (branch `002-polish`)

- [ ] T055 [P] `TT/tests/test_independence.py`. No module under `TT/src` imports anything outside the standard library, `openai`, `pydantic`, `rich` and `topic_tagger`. No source or test file refers to a path outside `TT/`, such as `../`, `site/` or `PoC`. A test copies `TT/` (without `.venv`) to a temporary folder and runs `uv run --offline pytest -q -k "not independence"` there; that test is skipped when `uv` is missing (SC-006).
- [ ] T056 [P] Write `TT/docs/formats.md` from `specs/002-topic-tagger/contracts/formats.md`, as the tool's own copy that stands alone without the specs. Complete `TT/README.md`:
  - a quick start that can be done in 15 minutes (SC-001);
  - every option;
  - adding a provider: implement `Provider`, register it in `get_provider`;
  - the licence, the same as the repository's;
  - "using this outside Cohort Data Builder".
- [ ] T057 [P] Update the root `README.md`: a "Topic tagging" paragraph linking `tools/topic-tagger/README.md` and `docs/data-format.md#adding-topics`.
- [ ] T058 Speed check in `TT/tests/test_speed.py`. Mark it `@pytest.mark.slow` and leave it out of the default run (`addopts = "-m 'not slow'"` and a registered `slow` marker in `TT/pyproject.toml`), because timings depend on the machine (Constitution I). T059 runs it with `uv run pytest -m slow`. It checks that loading a generated `tags.jsonl` of 35,000 records takes under 2 s, and the stand-in provider's overhead for 1,000 variables in batches of 20 is under 1 s.
- [ ] T059 Run `specs/002-topic-tagger/quickstart.md` sections 1–6 by hand, including a real Ollama run on the fixtures and on one real cohort exported from `site/data`. Record the results (model, speed, leading topics, share below 50%) in the integration pull request.
- [ ] T060 Integration pull request from `002-topic-tagger` to `main`. After the merge, tag `v0.2.0` and publish a GitHub Release whose notes name the tool and the processing script.

---

## Dependencies & Execution Order

| Phase | Depends on |
|---|---|
| 0 | Nothing. |
| 1 (Setup) | Phase 0. |
| 2 (Foundation) | Phase 1. Blocks all stories. |
| 3 (US1) | Phase 2. This is the MVP. |
| 4 (US2) | US1, because it extends the store, runner and CLI. |
| 5 (US3) | Phase 2 only, for validation and `check-scheme`. Its `tag --dry-run` test needs US1. |
| 6 (US4) | US1, for the runner's events. |
| 7 (US5) | US1, and US2 for `run.json` and the stop path. |
| 8 (US6) | Only the documented formats. It needs no tool code, so it can run alongside Phases 2–7, using hand-written fixtures. |
| 9 (Polish) | Every story. |

Within each story: tests, then the red commit, then the implementation, then the green
commit, then the README section.

### Parallel opportunities

- **Phase 2:** T007, T009, T010 and T013 are in different files.
- **US1:** the tests T016, T017 and T018 in parallel, then the implementations T021, T022
  and T023 in parallel.
- **US5:** T041, T042 and T043 in parallel, then T045 and T046.
- **US6:** the whole phase alongside US2–US5.

## Implementation Strategy

1. **MVP:** Phases 0–3. This tags a cohort end to end with a plain summary.
2. **Then US2, then US3.** Together with US1, these finish the three P1 stories. At that
   point the tool can be used on a real 32,000-variable cohort.
3. **Then US4 and US5**, the visuals and statistics.
4. **US6 at any point after Phase 2.**
5. **Each phase is one pull request into `002-topic-tagger`.** The integration pull request
   to `main` comes after Polish.
