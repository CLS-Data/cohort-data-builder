# Tasks: Tiered tagging (decision model) for the Topic Tagger

**Input**: `specs/004-tiered-tagger/` (spec.md, plan.md, research.md, data-model.md,
contracts/cli.md, contracts/formats.md, quickstart.md)

**Tests**: Required (constitution I). Within each story, the test task comes first. Run it
and see it fail, then commit it as `test(tagger): …`, then commit the code as
`feat(tagger): …`.

**Where**: All tagger paths are under `tools/topic-tagger/`. Run its tests from there with
`uv run pytest`, and lint with `uv run ruff check . && uv run ruff format --check .`. The
stand-in model is in `tests/conftest.py`, and the fake HTTP host in
`tests/test_provider.py` (`FakeOllama`). Reuse both patterns. Tests must not touch the
network or Ollama.

**Branches**: One short branch per phase off `004-tiered-tagger`, e.g.
`004-foundation`, `004-us1-tiered`, `004-us4-clef`. One PR each, squash-merged. Merge
stacked PRs top-down, or retarget each to `004-tiered-tagger` before merging.

## Format: `[ID] [P?] [Story] Description`

---

## Phase 1: Setup

- [x] T001 Add `/adhoc/` to the root `.gitignore`, with the comment "Ad hoc development work and local data: never committed". Check that `git status` no longer lists `adhoc/`.
- [ ] T002 Maintainer (needs the network, so it runs outside Claude's sandbox): run `ollama --version` (needs 0.40.6 or later), `ollama signin`, then `ollama pull clef:cloud`. Check that `curl -s localhost:11434/v1/models` lists `clef:cloud`, and note the Ollama version in `specs/004-tiered-tagger/research.md` § R10.
- [x] T003 [P] Write the labelled set:
  - `adhoc/tiered/variables.jsonl`: 80 fictional variables, in the tagger input format of `tools/topic-tagger/docs/formats.md` (`file`, `variable`, `label`, `values`). Spread them over every area of `tools/topic-tagger/src/topic_tagger/schemes/closer.toml`, about 5 per area. Include 15 that span two areas (e.g. "Mother smoked during pregnancy") and 3 that fit nothing.
  - `adhoc/tiered/expected.json`: `{"<file>/<variable>": ["topic_id", …]}`, using only topic ids from `closer.toml`.
  - `adhoc/tiered/README.md`: what the set is, and that it is fictional.

---

## Phase 2: Foundational (blocks US1 and US4)

**Purpose**: Generalise the reply check and the prompt from "the scheme's topics" to "a
node's options", add the `Node` tree, and pin the flat behaviour so it cannot change.

- [x] T004 [P] Write the failing tests:
  - `tests/test_reply.py`: `parse_options_reply(text, option_ids, batch_size, order)` accepts only the given ids, rejects any other with `ReplyError`, and sorts strongest first with ties in `order`. The existing `parse_reply(text, scheme, n)` returns exactly what it returned before, for the existing cases.
  - `tests/test_tiered.py`: `build_tree(scheme)` gives a root whose children are the domains in order, whose children are the topics. `node.is_leaf` holds for topics. `tree.find(id)` returns the node. A 3-level hand-built tree is accepted by the same `Node` type.
- [x] T005 [P] Write the failing tests in `tests/test_prompt.py`:
  - `build_option_messages(guidance, node, batch, show_children_of_options=True)` lists exactly `node.children` (id, label, description). With `show_children_of_options`, each option is followed by its children's labels, comma-separated (R2).
  - Its reply format instructions name only those ids.
  - `build_messages(scheme, batch)` (flat) is byte-for-byte unchanged on the fixture (assert against a snapshot taken from the current code before changing it).
- [x] T006 Implement `parse_options_reply` in `src/topic_tagger/reply.py`, reusing `_model(tuple(option_ids))`, and make `parse_reply` call it. Commit `feat(tagger): reply checks against any set of options`.
- [x] T007 Implement `Node` (`id`, `label`, `description`, `children: tuple[Node, ...]`, `is_leaf`) and `build_tree(scheme)` in the new `src/topic_tagger/tiered.py`, with Google-style docstrings. Implement `build_option_messages` in `src/topic_tagger/prompt.py`. Keep `build_messages` unchanged. Commit `feat(tagger): a taxonomy tree and prompts over a node's options`.

**Checkpoint**: `uv run pytest` passes, and the flat output is unchanged.

---

## Phase 3: User Story 1, tag tier by tier (P1) 🎯 MVP

**Goal**: `--method tiered` walks the tree with a chat model (FR-001 to FR-005, FR-008, FR-009).

**Independent Test**: With the stand-in model scripted per request, the tier-1 requests list
only areas, the tier-2 requests list only one area's topics, and the stored tags come from
the followed areas.

- [x] T008 [US1] Write the failing tests in `tests/test_tiered.py`, using a scripted chat stand-in that answers according to the option ids in each request's system message:
  - (a) A batch of 4 gives 1 tier-1 request and then one request per distinct followed area.
  - (b) An area is followed when its confidence is ≥ `descend_at` (default 0.5), at most `max_areas` (default 3, `0` = no cap), and the strongest is always followed even when below the threshold. `path` holds every followed area with its confidence (FR-016).
  - (b2) A one-domain scheme sends no tier-1 request.
  - (c) A variable followed into two areas has its leaf tags merged: highest confidence per topic, strongest first, ties in scheme order.
  - (d) The stored confidence is the tier-2 confidence.
  - (e) A node with exactly one child is routed without a request, keeping the parent's confidence, so the bundled `other` area yields topic `other`.
  - (f) A 3-level tree takes 3 tiers of requests.
  - (g) A reply naming an id outside the options is retried, using the runner's existing ladder (retries, then alone, then failed for that group).
  - (h) A variable with tags from one area but a failed second area is stored with the tags it has, while a variable with no tags at all is failed.
  - (i) The walk returns per-variable `path` `[[area, conf], …]` and `requests_by_tier`.
- [x] T009 [US1] Implement in `src/topic_tagger/tiered.py`:
  - a `Decider` protocol: `decide(node, variables) -> dict[int, list[tuple[str, float]]]`;
  - `ChatDecider(provider, guidance)`, using `build_option_messages` and `parse_options_reply`;
  - `walk(tree, batch, decider, descend_at, max_areas) -> (tags, paths, failed, requests_by_tier)`, a queue of `(node, variables)` groups.

  Comments say *why*: single-child routing, and always following the strongest area.
- [x] T010 [US1] Write the failing tests in `tests/test_runner.py`: `Settings(method="tiered", descend_at=0.5, max_areas=3)` makes `Runner.run` use the walk for each batch. Stop (`request_stop`) still finishes and stores the batches in flight. `RunResult.requests_by_tier` is summed across batches. `method="flat"` behaves exactly as before.
- [x] T011 [US1] Implement in `src/topic_tagger/runner.py`: add the `method`, `descend_at` and `max_areas` settings, add `RunResult.requests_by_tier`, and have `_batch` call `walk` when tiered, reusing the ladder via a shared `_with_ladder(ask, variables)` helper so flat and tiered retry alike. Commit. *(As built: the walk keeps its own ladder in `tiered.py`; see plan.md.)*
- [x] T012 [US1] Write the failing tests in `tests/test_cli.py`:
  - `--method tiered` is accepted, and `--method` defaults to `flat`.
  - `--descend-at 1.5` gives exit 2. So do `--max-areas -1` and `--descend-at` without `--method tiered`. `--max-areas 0` is accepted as no cap.
  - `--dry-run --method tiered` prints the tier-1 request, `--- tier 2 example (<area label>) ---` and the tier-2 request (contracts/cli.md), and sends nothing.
- [x] T013 [US1] Implement `--method`, `--descend-at` and `--max-areas`, their validation, and the tiered dry-run in `src/topic_tagger/cli.py`. Pass them into `Settings`. In the same commit, document them in `README.md` ("Tiered tagging") and add `method` to the `run.json` section of `docs/formats.md` (constitution II: docs change with code). Commit.

**Checkpoint**: A tiered run with the stand-in tags the fixture end to end, and flat is unchanged.

---

## Phase 4: User Story 4, the Clef decision model (P1)

**Goal**: `--provider ollama-decision --model clef:cloud --method tiered` (FR-012 to FR-015).

**Independent Test**: Against a fake `/v1/systemone` server, the requests carry one variable
as `state` and one `noul` question per option, and the tags follow the descend and keep
thresholds.

- [x] T014 [P] [US4] Write the failing tests in the new `tests/test_decision_provider.py`, with a local fake server in the style of `FakeOllama` that serves `GET /v1/models` and `POST /v1/systemone`:
  - `decide(state, questions)` posts `{"model", "state", "questions"}` and returns `{id: noul}` from `answers`.
  - More than 64 questions are split into several requests and their answers combined.
  - `check()` says `model clef:cloud is not installed; run: ollama pull clef:cloud` when the model is not listed, and names the host when it cannot be reached.
  - A timeout, a non-200 response or a missing answer raises `ProviderError`.
  - `is_remote()` is true for `clef:cloud`, `x-cloud`, and any host other than localhost.
- [x] T015 [P] [US4] Write a failing test in `tests/test_provider.py`: the chat `ollama` provider's `is_remote()` is true for a model ending `:cloud`, as well as `-cloud` (FR-014, R12).
- [x] T016 [US4] Implement `OllamaDecisionProvider` in the new `src/topic_tagger/providers/ollama_decision.py`, using `urllib.request` with no client retries and splitting at 64. Register it as `ollama-decision` in `providers/__init__.py`, and document the second provider kind in that module's docstring. Make `remote_suffix` accept both `-cloud` and `:cloud` for both providers. Commit.
- [x] T017 [US4] Write the failing tests in `tests/test_tiered.py` for `DecisionDecider(provider, keep_at=0.3)`:
  - It asks one request per variable.
  - The `state` is `{"name", "label", "values"}`, with values capped at 30 (`prompt.MAX_VALUES`).
  - Each question has `{"type": "noul", "instructions": "Is this survey variable about <label>? <description>"}`, plus the area's topic labels at tier 1.
  - Areas are returned with their probabilities, for the walk to apply `descend_at`.
  - Leaves are kept when ≥ `keep_at`, else the single strongest leaf is kept, and `keep_at=0` keeps every leaf (FR-017).
  - **Flat** with the decider (R14) walks `flat_tree(scheme)`, a root whose children are every topic. With the bundled CLOSER scheme it sends 2 requests per variable (split at 64), and returns the same keep rule.
- [x] T018 [US4] Implement `DecisionDecider` and `flat_tree(scheme)` in `src/topic_tagger/tiered.py`. Commit.
- [x] T019 [US4] Write the failing tests in `tests/test_cli.py`:
  - `--provider ollama-decision --method flat` tags the fixture against the fake server, asking every topic per variable.
  - With `--provider ollama` (chat), `--method flat` still uses the unchanged flat prompt (FR-009).
  - `--keep-at` without the decision provider gives exit 2.
  - A run against the fake decision server tags the fixture.
  - `--model clef:cloud` without `--yes` asks before sending.
  - `--dry-run` with the decision provider prints the first variable's tier-1 and tier-2 `/v1/systemone` bodies as JSON.
- [x] T020 [US4] Implement `--keep-at`, the decider choice (chat or decision, flat or tiered) and the decision dry-run in `src/topic_tagger/cli.py`. In the same commit, document `--provider ollama-decision`, `--keep-at`, `ollama pull clef:cloud` and the request cost (1 + areas per variable tiered, 2 per variable flat) in `README.md`. Commit.
- [ ] T021 [US4] Maintainer, outside the sandbox: `uv run topic-tagger tag tests/fixtures/variables.jsonl --out "$TMPDIR/clef" --provider ollama-decision --model clef:cloud --method tiered --yes`. All 60 should be tagged with 0 failed (SC-005). If Clef's real responses differ from the documented shape (`answers.<id>.noul`), first add a failing provider test with the real shape, then fix it.

**Checkpoint**: Clef tags the fixture for real.

---

## Phase 5: User Story 2, see how it decided (P2)

**Goal**: `method` and `path` in records, staleness by method, and per-tier counts (FR-005 to FR-007).

**Independent Test**: After a tiered stand-in run, every record has `method: "tiered"` and a
`path`, and `run.json` has the method and `requests_by_tier`.

- [x] T022 [P] [US2] Write the failing tests in `tests/test_store.py`:
  - `make_record(..., method="flat")` adds `"method": "flat"`, and `make_record(..., method="tiered", path=[["health", 0.9]])` adds both fields.
  - `state(key, hash, method)` is `current` only when the hash and method both match, and is `stale` when the method differs.
  - A record without `method` counts as `"flat"`.
- [x] T023 [P] [US2] Write the failing tests in `tests/test_cli.py`:
  - A tiered run's `run.json` has `method`, `descend_at`, `max_areas` and `requests_by_tier` (and `keep_at` with the decision provider).
  - A flat run's `run.json` has `"method": "flat"` and `"requests_by_tier": [requests]`.
  - The summary prints `Requests by tier: 1: <n>, 2: <n>` and `Areas followed per variable: <mean>`.
  - Running tiered over a flat output folder redoes every variable.
- [x] T024 [US2] Implement these in `src/topic_tagger/store.py`, `src/topic_tagger/runner.py` (pass `method` and `path` to `make_record`) and `src/topic_tagger/cli.py` (`_run_record`, `_summary`, and pass `method` to `state`). Check that `report.html` still builds from a tiered folder (`tests/test_report.py` passes). In the same commit, update `docs/formats.md` with `method`, `path`, `descend_at`, `max_areas`, `keep_at` and `requests_by_tier`, from `contracts/formats.md`. Commit.

---

## Phase 6: User Story 3, compare the methods ad hoc (P2)

**Goal**: One command tags the labelled set four ways (flat and tiered × Clef and gpt-oss) and prints the comparison, including a threshold sweep (SC-001, SC-002, SC-004, R13).

**Independent Test**: The scoring runs on finished output folders with no model.

- [x] T025 [US3] Write the scoring part of `adhoc/tiered/compare.py` (not committed) first, with a `--self-check` that scores two tiny hand-written folders with known answers and asserts the numbers, so scoring can be trusted without a model. Run the self-check, and see it fail, then pass.
  - **Measures:** top-1 hit rate, recall, precision and mean tags per variable.
  - **Area recall:** the share of expected topics whose area was followed.
  - **Thresholds (R13):** re-scoring at each descend threshold t in `--sweep` (default `0.1,0.2,0.3,0.5,0.7`) and keep threshold k in `--keep-sweep` (default `0.2,0.3,0.5`). It keeps topics whose area had path confidence ≥ t (always the strongest area) and whose confidence is ≥ k, and estimates the requests per variable a run at t would need.
- [x] T026 [US3] Add the runs to `compare.py`. It calls `topic-tagger tag` (via `sys.executable -m topic_tagger`) on `adhoc/tiered/variables.jsonl`, into `adhoc/tiered/runs/<name>-<YYYYMMDD-HHMM>/`:
  - `flat-gptoss`: `--method flat --model gpt-oss:20b-cloud`;
  - `tiered-gptoss`: `--method tiered --model gpt-oss:20b-cloud --descend-at 0.1 --max-areas 0`;
  - `flat-clef`: `--provider ollama-decision --model clef:cloud --method flat --keep-at 0`;
  - `tiered-clef`: `--provider ollama-decision --model clef:cloud --method tiered --descend-at 0.1 --max-areas 0 --keep-at 0`;
  - all four with `--yes --plain --workers 4`.

  It also supports:
  - `--only NAME,…` to run a subset;
  - `--score-only DIR…` to score existing folders without running anything;
  - `--variables PATH` to use another file, in which case it prints only the disagreements when there is no `expected.json`.
  It prints:
  - a table, one row per run (flat runs at each k; tiered runs at each t and k), with the measures above, failed, requests per variable, and seconds;
  - then, per variable where the best flat and best tiered rows disagree, the expected topics and each run's topics with confidences.

  It also supports `--only NAME,…`, `--score-only DIR…` and `--variables PATH`. With `--variables` and no `expected.json`, it prints only the disagreements.
- [ ] T027 [US3] Maintainer, outside the sandbox: run `uv run --project tools/topic-tagger python adhoc/tiered/compare.py`. Record the table, the date, the model versions and the Ollama version in `specs/004-tiered-tagger/research.md` § "Results". Answer SC-001 for each model: does tiered beat flat, and at which descend and keep thresholds? Recommend defaults for `--method`, `--descend-at`, `--max-areas` and `--keep-at`. Note anything worth trying next (R2 variant, `choice` instead of `noul`, the thresholds).

---

## Phase 7: Polish & cross-cutting

- [x] T028 [P] Final pass over `tools/topic-tagger/docs/formats.md` against `contracts/formats.md` and the code: every field documented, examples valid.
- [x] T029 [P] Final pass over `tools/topic-tagger/README.md`: options, the Clef setup, costs, and the `:cloud` confirmation all match `--help`.
- [x] T030 Run the whole tagger suite and lint. From the repository root, run `uv run pytest` to confirm the site is unaffected (`scripts/topics.py` ignores the new fields). Run `quickstart.md` steps 1–2 locally. Steps 3–6 are T002, T021 and T027.
- [ ] T031 Open the PR `004-tiered-tagger` → `main`. Its "How to review" section covers the offline tests, the dry-run to try, and the Clef run as a maintainer step. Mark the ad hoc comparison and real-data runs as out of scope.

---

## Dependencies & order

- Setup: T001 first. T002 can happen any time before T021. T003 is needed only by Phase 6.
- Foundational (T004–T007) blocks US1 and US4.
- **US1 (T008–T013)** comes before US4's decider work (T017–T020), which plugs into the walk. The US4 provider tasks (T014–T016) can run alongside US1.
- **US2 (T022–T024)** comes after US1. It can run alongside US4.
- US3: the T025 scoring and self-check can start once US2 fixes the record shape. T026–T027 come after US1, US4 and US2.
- Polish comes last.

## Parallel examples

- After Phase 2: T008 (US1 tests) ∥ T014 + T015 (US4 provider tests).
- After US1: T017 (US4 decider tests) ∥ T022 + T023 (US2 tests).
- Polish: T028 ∥ T029.

## Implementation strategy

1. **MVP**: Phases 1–3. The tiered method works with chat models, and flat is untouched.
2. Add Clef (Phase 4) and run it for real on the fixture (T021).
3. Add the record fields (Phase 5), then the ad hoc comparison (Phase 6). Its results decide
   whether tiered or Clef becomes a default, in a follow-up.
