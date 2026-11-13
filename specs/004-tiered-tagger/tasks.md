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

- [ ] T001 Add `/adhoc/` to the root `.gitignore`, with the comment "Ad hoc development work and local data: never committed". Check that `git status` no longer lists `adhoc/`.
- [ ] T002 Maintainer (needs the network, so it runs outside Claude's sandbox): run `ollama --version` (needs 0.40.6 or later), `ollama signin`, then `ollama pull clef:cloud`. Check that `curl -s localhost:11434/v1/models` lists `clef:cloud`, and note the Ollama version in `specs/004-tiered-tagger/research.md` § R10.
- [ ] T003 [P] Write the labelled set:
  - `adhoc/tiered/variables.jsonl`: 80 fictional variables, in the tagger input format of `tools/topic-tagger/docs/formats.md` (`file`, `variable`, `label`, `values`). Spread them over every area of `tools/topic-tagger/src/topic_tagger/schemes/closer.toml`, about 5 per area. Include 15 that span two areas (e.g. "Mother smoked during pregnancy") and 3 that fit nothing.
  - `adhoc/tiered/expected.json`: `{"<file>/<variable>": ["topic_id", …]}`, using only topic ids from `closer.toml`.
  - `adhoc/tiered/README.md`: what the set is, and that it is fictional.

---

## Phase 2: Foundational (blocks US1 and US4)

**Purpose**: Generalise the reply check and the prompt from "the scheme's topics" to "a
node's options", add the `Node` tree, and pin the flat behaviour so it cannot change.

- [ ] T004 [P] Write the failing tests:
  - `tests/test_reply.py`: `parse_options_reply(text, option_ids, batch_size, order)` accepts only the given ids, rejects any other with `ReplyError`, and sorts strongest first with ties in `order`. The existing `parse_reply(text, scheme, n)` returns exactly what it returned before, for the existing cases.
  - `tests/test_tiered.py`: `build_tree(scheme)` gives a root whose children are the domains in order, whose children are the topics. `node.is_leaf` holds for topics. `tree.find(id)` returns the node. A 3-level hand-built tree is accepted by the same `Node` type.
- [ ] T005 [P] Write the failing tests in `tests/test_prompt.py`:
  - `build_option_messages(guidance, node, batch, show_children_of_options=True)` lists exactly `node.children` (id, label, description). With `show_children_of_options`, each option is followed by its children's labels, comma-separated (R2).
  - Its reply format instructions name only those ids.
  - `build_messages(scheme, batch)` (flat) is byte-for-byte unchanged on the fixture (assert against a snapshot taken from the current code before changing it).
- [ ] T006 Implement `parse_options_reply` in `src/topic_tagger/reply.py`, reusing `_model(tuple(option_ids))`, and make `parse_reply` call it. Commit `feat(tagger): reply checks against any set of options`.
- [ ] T007 Implement `Node` (`id`, `label`, `description`, `children: tuple[Node, ...]`, `is_leaf`) and `build_tree(scheme)` in the new `src/topic_tagger/tiered.py`, with Google-style docstrings. Implement `build_option_messages` in `src/topic_tagger/prompt.py`. Keep `build_messages` unchanged. Commit `feat(tagger): a taxonomy tree and prompts over a node's options`.

**Checkpoint**: `uv run pytest` passes, and the flat output is unchanged.

---

## Phase 3: User Story 1, tag tier by tier (P1) 🎯 MVP

**Goal**: `--method tiered` walks the tree with a chat model (FR-001 to FR-005, FR-008, FR-009).

**Independent Test**: With the stand-in model scripted per request, the tier-1 requests list
only areas, the tier-2 requests list only one area's topics, and the stored tags come from
the followed areas.

- [ ] T008 [US1] Write the failing tests in `tests/test_tiered.py`, using a scripted chat stand-in that answers according to the option ids in each request's system message:
  - (a) A batch of 4 gives 1 tier-1 request and then one request per distinct followed area.
  - (b) An area is followed when its confidence is ≥ `descend_at` (default 0.5), at most `max_areas` (default 3), and the strongest is always followed even when below the threshold.
  - (c) A variable followed into two areas has its leaf tags merged: highest confidence per topic, strongest first, ties in scheme order.
  - (d) The stored confidence is the tier-2 confidence.
  - (e) A node with exactly one child is routed without a request, keeping the parent's confidence, so the bundled `other` area yields topic `other`.
  - (f) A 3-level tree takes 3 tiers of requests.
  - (g) A reply naming an id outside the options is retried, using the runner's existing ladder (retries, then alone, then failed for that group).
  - (h) A variable with tags from one area but a failed second area is stored with the tags it has, while a variable with no tags at all is failed.
  - (i) The walk returns per-variable `path` `[[area, conf], …]` and `requests_by_tier`.
- [ ] T009 [US1] Implement in `src/topic_tagger/tiered.py`:
  - a `Decider` protocol: `decide(node, variables) -> dict[int, list[tuple[str, float]]]`;
  - `ChatDecider(provider, guidance)`, using `build_option_messages` and `parse_options_reply`;
  - `walk(tree, batch, decider, descend_at, max_areas) -> (tags, paths, failed, requests_by_tier)`, a queue of `(node, variables)` groups.

  Comments say *why*: single-child routing, and always following the strongest area.
- [ ] T010 [US1] Write the failing tests in `tests/test_runner.py`: `Settings(method="tiered", descend_at=0.5, max_areas=3)` makes `Runner.run` use the walk for each batch. Stop (`request_stop`) still finishes and stores the batches in flight. `RunResult.requests_by_tier` is summed across batches. `method="flat"` behaves exactly as before.
- [ ] T011 [US1] Implement in `src/topic_tagger/runner.py`: add the `method`, `descend_at` and `max_areas` settings, add `RunResult.requests_by_tier`, and have `_batch` call `walk` when tiered, reusing the ladder via a shared `_with_ladder(ask, variables)` helper so flat and tiered retry alike. Commit.
- [ ] T012 [US1] Write the failing tests in `tests/test_cli.py`:
  - `--method tiered` is accepted, and `--method` defaults to `flat`.
  - `--descend-at 1.5` gives exit 2. So does `--max-areas 0`, and `--descend-at` without `--method tiered`.
  - `--dry-run --method tiered` prints the tier-1 request, `--- tier 2 example (<area label>) ---` and the tier-2 request (contracts/cli.md), and sends nothing.
- [ ] T013 [US1] Implement `--method`, `--descend-at` and `--max-areas`, their validation, and the tiered dry-run in `src/topic_tagger/cli.py`. Pass them into `Settings`. Commit.

**Checkpoint**: A tiered run with the stand-in tags the fixture end to end, and flat is unchanged.

---

## Phase 4: User Story 4, the Clef decision model (P1)

**Goal**: `--provider ollama-decision --model clef:cloud --method tiered` (FR-012 to FR-015).

**Independent Test**: Against a fake `/v1/systemone` server, the requests carry one variable
as `state` and one `noul` question per option, and the tags follow the descend and keep
thresholds.

- [ ] T014 [P] [US4] Write the failing tests in the new `tests/test_decision_provider.py`, with a local fake server in the style of `FakeOllama` that serves `GET /v1/models` and `POST /v1/systemone`:
  - `decide(state, questions)` posts `{"model", "state", "questions"}` and returns `{id: noul}` from `answers`.
  - More than 64 questions are split into several requests and their answers combined.
  - `check()` says `model clef:cloud is not installed; run: ollama pull clef:cloud` when the model is not listed, and names the host when it cannot be reached.
  - A timeout, a non-200 response or a missing answer raises `ProviderError`.
  - `is_remote()` is true for `clef:cloud`, `x-cloud`, and any host other than localhost.
- [ ] T015 [P] [US4] Write a failing test in `tests/test_provider.py`: the chat `ollama` provider's `is_remote()` is true for a model ending `:cloud`, as well as `-cloud` (FR-014, R12).
- [ ] T016 [US4] Implement `OllamaDecisionProvider` in the new `src/topic_tagger/providers/ollama_decision.py`, using `urllib.request` with no client retries and splitting at 64. Register it as `ollama-decision` in `providers/__init__.py`, and document the second provider kind in that module's docstring. Make `remote_suffix` accept both `-cloud` and `:cloud` for both providers. Commit.
- [ ] T017 [US4] Write the failing tests in `tests/test_tiered.py` for `DecisionDecider(provider, keep_at=0.3)`:
  - It asks one request per variable.
  - The `state` is `{"name", "label", "values"}`, with values capped at 30 (`prompt.MAX_VALUES`).
  - Each question has `{"type": "noul", "instructions": "Is this survey variable about <label>? <description>"}`, plus the area's topic labels at tier 1.
  - Areas are returned with their probabilities, for the walk to apply `descend_at`.
  - Leaves are kept when ≥ `keep_at`, else the single strongest leaf is kept.
- [ ] T018 [US4] Implement `DecisionDecider` in `src/topic_tagger/tiered.py`. Commit.
- [ ] T019 [US4] Write the failing tests in `tests/test_cli.py`:
  - `--provider ollama-decision --method flat` gives exit 2 with "a decision model answers one tier at a time: use --method tiered".
  - `--keep-at` without the decision provider gives exit 2.
  - A run against the fake decision server tags the fixture.
  - `--model clef:cloud` without `--yes` asks before sending.
  - `--dry-run` with the decision provider prints the first variable's tier-1 and tier-2 `/v1/systemone` bodies as JSON.
- [ ] T020 [US4] Implement `--keep-at`, the provider and method check, the decider choice and the decision dry-run in `src/topic_tagger/cli.py`. Commit.
- [ ] T021 [US4] Maintainer, outside the sandbox: `uv run topic-tagger tag tests/fixtures/variables.jsonl --out "$TMPDIR/clef" --provider ollama-decision --model clef:cloud --method tiered --yes`. All 60 should be tagged with 0 failed (SC-005). If Clef's real responses differ from the documented shape (`answers.<id>.noul`), first add a failing provider test with the real shape, then fix it.

**Checkpoint**: Clef tags the fixture for real.

---

## Phase 5: User Story 2, see how it decided (P2)

**Goal**: `method` and `path` in records, staleness by method, and per-tier counts (FR-005 to FR-007).

**Independent Test**: After a tiered stand-in run, every record has `method: "tiered"` and a
`path`, and `run.json` has the method and `requests_by_tier`.

- [ ] T022 [P] [US2] Write the failing tests in `tests/test_store.py`:
  - `make_record(..., method="flat")` adds `"method": "flat"`, and `make_record(..., method="tiered", path=[["health", 0.9]])` adds both fields.
  - `state(key, hash, method)` is `current` only when the hash and method both match, and is `stale` when the method differs.
  - A record without `method` counts as `"flat"`.
- [ ] T023 [P] [US2] Write the failing tests in `tests/test_cli.py`:
  - A tiered run's `run.json` has `method`, `descend_at`, `max_areas` and `requests_by_tier` (and `keep_at` with the decision provider).
  - A flat run's `run.json` has `"method": "flat"` and `"requests_by_tier": [requests]`.
  - The summary prints `Requests by tier: 1: <n>, 2: <n>` and `Areas followed per variable: <mean>`.
  - Running tiered over a flat output folder redoes every variable.
- [ ] T024 [US2] Implement these in `src/topic_tagger/store.py`, `src/topic_tagger/runner.py` (pass `method` and `path` to `make_record`) and `src/topic_tagger/cli.py` (`_run_record`, `_summary`, and pass `method` to `state`). Check that `report.html` still builds from a tiered folder (`tests/test_report.py` passes). Commit.

---

## Phase 6: User Story 3, compare the methods ad hoc (P2)

**Goal**: One command tags the labelled set three ways and prints the comparison (SC-001, SC-004).

**Independent Test**: The scoring runs on finished output folders with no model.

- [ ] T025 [US3] Write `adhoc/tiered/compare.py` (not committed). It runs `topic-tagger tag` (via `sys.executable -m topic_tagger`) three times on `adhoc/tiered/variables.jsonl`, into `adhoc/tiered/runs/<name>-<YYYYMMDD-HHMM>/`:
  - `flat-gptoss`: `--method flat --model gpt-oss:20b-cloud`;
  - `tiered-gptoss`: `--method tiered --model gpt-oss:20b-cloud`;
  - `tiered-clef`: `--provider ollama-decision --model clef:cloud --method tiered`;
  - all three with `--yes --plain`.

  It also supports:
  - `--only NAME,…` to run a subset;
  - `--score-only DIR…` to score existing folders without running anything;
  - `--variables PATH` to use another file, in which case it prints only the disagreements when there is no `expected.json`.
- [ ] T026 [US3] In `compare.py`, score each run against `adhoc/tiered/expected.json` and print:
  - a table with top-1 hit rate, recall, precision, mean tags per variable, failed, requests (from `run.json`), requests by tier, and seconds;
  - then, per variable where runs disagree, the expected topics and each run's topics with confidences.

  Add a `--self-check` that scores two tiny hand-written folders with known answers and asserts the numbers, so scoring can be trusted without a model.
- [ ] T027 [US3] Maintainer, outside the sandbox: run `uv run --project tools/topic-tagger python adhoc/tiered/compare.py`. Record the table, the date, the model versions and the Ollama version in `specs/004-tiered-tagger/research.md` § "Results". State whether SC-001 is met and whether tiered should become the default. Note anything worth trying next (R2 variant, `choice` instead of `noul`, the thresholds).

---

## Phase 7: Polish & cross-cutting

- [ ] T028 [P] Update `tools/topic-tagger/docs/formats.md`: `method` and `path` in `tags.jsonl`, and `method`, `descend_at`, `max_areas`, `keep_at` and `requests_by_tier` in `run.json`, from `contracts/formats.md`.
- [ ] T029 [P] Update `tools/topic-tagger/README.md`: a "Tiered tagging" section covering how it works, `--method`, `--descend-at`, `--max-areas`, `--keep-at`, and `--provider ollama-decision` with `ollama pull clef:cloud`. Note that cost grows with requests per variable, and that `:cloud` models ask before sending.
- [ ] T030 Run the whole tagger suite and lint. From the repository root, run `uv run pytest` to confirm the site is unaffected (`scripts/topics.py` ignores the new fields). Run `quickstart.md` steps 1–2 locally. Steps 3–6 are T002, T021 and T027.
- [ ] T031 Open the PR `004-tiered-tagger` → `main`. Its "How to review" section covers the offline tests, the dry-run to try, and the Clef run as a maintainer step. Mark the ad hoc comparison and real-data runs as out of scope.

---

## Dependencies & order

- Setup: T001 first. T002 can happen any time before T021. T003 is needed only by Phase 6.
- Foundational (T004–T007) blocks US1 and US4.
- **US1 (T008–T013)** comes before US4's decider work (T017–T020), which plugs into the walk. The US4 provider tasks (T014–T016) can run alongside US1.
- **US2 (T022–T024)** comes after US1. It can run alongside US4.
- **US3 (T025–T027)** comes after US1, US4 and US2, since it reads `run.json`'s `requests_by_tier`.
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
