---

description: "Task list for feature 007: search several cohorts at once"
---

# Tasks: Search several cohorts at once

**Input**: Design documents from `/specs/007-multi-cohort-search/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Required. The constitution (Principle I) makes test-first non-negotiable: every
test task is written, run and seen to fail, and committed as `test(…)` before the
implementation task that follows it is started. Implementation commits are `feat(…)` /
`fix(…)`. Every new exported JavaScript function gets JSDoc; every Python function a
Google-style docstring.

**Organization**: Setup and Foundational on branch `007-foundation`; then one phase and one
short branch per user story off `007-multi-cohort-search` (plan.md), one pull request each,
squash-merged. Tick tasks here as they are done.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to (US1–US5)

## Path Conventions

Static site in `site/`; Node tests in `tests/js/`; browser tests in `tests/python/e2e/`
(fixtures `serve`, `mini_site`, `mini` in `tests/python/conftest.py` and
`tests/python/e2e/conftest.py`); data checks in `scripts/checks.py` with tests in
`tests/python/data/test_checks.py`; generated-script tests in `tests/python/generated/`.
Fixture data in `tests/fixtures/data/`. **All fixture values are invented; never copy
values from `site/data/` or any real data into a fixture.**

---

## Phase 1: Setup

**Purpose**: Branch, real sweep keys, second fixture cohort.

- [x] T001 Create branch `007-multi-cohort-search` from `main` and push it; then branch `007-foundation` from it. Commit `specs/007-multi-cohort-search/` and `.specify/feature.json` on `007-multi-cohort-search` first (`docs(007): spec, plan and tasks`). Leave the untracked `my-scheme.toml` alone.
- [X] T002 Ask the user to run the command in `specs/007-multi-cohort-search/quickstart.md` §0 (the assistant cannot read `site/data/`) and record its output under a new "Sweep keys of the real cohorts" heading in `specs/007-multi-cohort-search/research.md` R1, listing per cohort which sweeps have neither `age` nor a `<n>y`/`<n>m` key. If any do, the user (or data team) adds `age` to those sweeps in `site/data/<key>/manifest.json` per `contracts/sweep-ages.md` in its own commit after T009; the assistant does not edit `site/data/`.
- [X] T002a Add `scripts/sweep_ages.py` (tests first, in `tests/python/test_sweep_age_labels.py`): reads each sweep's age from its `label` — the CLS metadata's `sweep-year-age` text, built into labels such as `Sweep 6.1: age 44/45, 2002/04` — and writes `age` (and `ageRange` when a span, e.g. `44/45` → `age: 44, ageRange: [44, 45]`) into `site/data/<key>/manifest.json`. Months (`age 9 months` → 0.75) and `birth` (→ 0) are read; years such as `2002/04` are never taken for ages; an existing `age` is kept; a label with no age (e.g. `xwave`) is left and listed. Dry run by default, `--write` to write; then runs the data checks (exit 0 done, 1 checks failed, 2 bad input). Standard library only. A person runs it on `site/data` (research R1); the assistant does not.
- [x] T003 Create fictional fixture cohort `tests/fixtures/data/mini2/` (`manifest.json`, `index.json`, `dict/<file>.json`) conforming to `specs/001-cohort-data-builder/contracts/site-data.md`: key `mini2`, name `Mini2`, fullName `Second Mini Test Cohort`, identifier `CID`, `wave.term` `"wave"`, sweeps `{"key":"3y","label":"Age 3"}`, `{"key":"w2","label":"Wave 2","age":7}`, `{"key":"11y","label":"Age 11"}`, `{"key":"extra","label":"Linked records"}` (no age, not age-shaped); four files with `hasId: true` (`mini2_age3`, `mini2_w2`, `mini2_age11`, and `mini2_links` on sweep `extra`), each with `CID`, `sex` (same name and label as in `mini`) and 2–3 invented variables incl. one whose label contains "smok" in `mini2_age11`; a `topics` scheme with `version: 2` and one domain `health` (same id as `mini`'s) holding two topics: `smoking` (same id and label as in `mini`'s scheme) and `vaping` (not in `mini`'s scheme). Tag only the "smok" variable in `mini2_age11` (`smoking`, 0.9) and one other variable (`vaping`, 0.8); every other row is untagged; `counts` matching. Add `mini2` after `mini` in `tests/fixtures/data/datasets.json` with correct `variables` and `files`.
- [x] T003a Create fictional fixture cohort `tests/fixtures/data/mini3/`: key `mini3`, name `Mini3`, identifier `KID`, one sweep `{"key":"16y","label":"Age 16"}`, one file `mini3_age16` (`hasId: true`) with `KID`, `sex` and one invented variable, **no `topics`** anywhere; `counts` matching. Add it after `mini2` in `tests/fixtures/data/datasets.json`.
- [x] T004 Run `uv run pytest tests/python/data && npm test && uv run pytest tests/python/e2e`; fix any existing test that assumed the catalogue holds one cohort (e.g. a count of `#dataset` options or footer totals) so the suite is green with `mini2` and `mini3` listed. Commit `test(fixtures): fictional cohorts mini2 and mini3`.

---

## Phase 2: Foundational (blocking prerequisites)

**Purpose**: Sweep ages, cohort-choice helpers, cohort-qualified keys, topic filter by id,
multi-cohort state and colour tokens, with the site behaving exactly as today for one
cohort. **No user story starts until this phase is merged.**

### Tests for Foundational ⚠️ write first, see them fail

- [x] T005 [P] Data-check tests in `tests/python/test_sweep_ages.py` (outside `tests/python/data/`, which the assistant's permission settings close) (contract `contracts/sweep-ages.md`): a manifest copy of `mini` with `"age": -1`, `"age": 121`, `"age": "5"` each reports a D3 problem naming the sweep; `"ageRange": [8, 6]` and `"ageRange": [1, 2]` with `"age": 5` report "`ageRange` must contain `age`"/min ≤ max; ages not strictly increasing in list order (`5y` age 10, `10y` age 5) report a problem; a sweep with neither `age` nor an age-shaped key (`mini2`'s `extra`, `mini`'s `xwave`) gives a **warning**, not a problem, and the valid fixture still has no problems.
- [x] T006 [P] `tests/js/ages.test.mjs` for new `site/js/core/ages.js`: `sweepAge({key:"14y"})` → 14; `{key:"9m"}` → 0.75; `{key:"w2", age:7}` → 7 (explicit wins over key); `{key:"xwave"}` → null; `{key:"34/35"}` → null. `ageLabel(0.75)` → `"9m"`, `ageLabel(11)` → `"11"`, `ageLabel(2.5)` → `"2.5"`. `ageAxis([manifestMini])` → columns are mini's sweeps in manifest order (5, 10, then null for `xwave`) labelled by sweep key (single-cohort = today). `ageAxis([mini, mini2])` → columns ages `[3, 5, 7, 10, 11, null]`, one `null` column last; `cells(axis, mini)` → `[null, 0, null, 1, null, 2]` and for mini2 `[0, null, 1, null, 2, 3]` (sweep indices).
- [x] T007 [P] `tests/js/cohorts.test.mjs` for new `site/js/core/cohorts.js` (contract `contracts/cohort-choice.md`): with catalogue keys `["mini","mini2","x"]`: `parseChoice("#mini2+mini", keys)` → `["mini","mini2"]` (catalogue order); `"#mini2+nope"` → `["mini2"]`; `"#nope"` and `""` → `[]`; `formatChoice(["mini2","mini"], keys)` → `"mini+mini2"`; `chooseInitial({hash, stored, storedOld, keys})` follows address → `cohorts` → old `cohort` → first key; `toggleChoice(["mini"], "mini", keys)` → `["mini"]` (last one stays); `toggleChoice(["mini"], "mini2", keys)` → `["mini","mini2"]`; `colourSlot("bcs70", keys)` returns the pinned slot for each known real key (`ncds`, `bcs70`, `next_steps`, `mcs`) and `colourSlot("x", keys)` → `(index of "x") % 6 + 1`.
- [x] T008 [P] Extend `tests/js/selection.test.mjs`, `tests/js/topics.test.mjs` and `tests/js/search.test.mjs`: `cohortKeyOf({cohort:"mini",file:"f",name:"n"})` → `"mini:f:n"` (`keyOf` stays `<file>:<name>`, unique within one cohort's selection); `toItem(row, manifest)` includes `cohort: manifest.key`; `restore(saved, vars, manifest)` adds `cohort` to entries saved without it and `has()` distinguishes `mini:…:sex` from `mini2:…:sex`; topic filter items are `{kind, id}` and `passes`/`filterVariables` give the same matches as today's index form on `mini`; on a manifest without `topics` an active topic filter matches nothing and the result reports `untagged: true`; `searchCohorts([{key:"mini",manifest,vars},{key:"mini2",…}], filters)` returns one `CohortResult` per cohort in the given order, each equal to `filterVariables` for that cohort, with `wave`/`file` filters of `{cohort:"mini2", i:1}` applied to `mini2` only and other cohorts returning **no** matches while a sweep or file filter is set on another cohort; `levelFilter` by name (`"ORDINAL"`) works across cohorts with different `levels` lists. Topic ids match across schemes: with `topicSel = [{kind:"t", id:"smoking"}]`, `searchCohorts` over `mini` and `mini2` returns `smoke5` from `mini` and the smok variable from `mini2`, even though `smoking` has a different index in each scheme; `{id:"vaping"}` returns nothing from `mini`, and `mini` is not reported `untagged`. On `mini3` an active topic filter returns no matches and `untagged: true`.
- [x] T009 Commit the failing tests T005–T008: `test(007): sweep ages, cohort choice, cohort keys, topic ids`.

### Implementation for Foundational

- [x] T010 [P] Add sweep-age checks to D3 in `scripts/checks.py` per `contracts/sweep-ages.md` ("`age`, if present, is a number from 0 to 120"; "`ageRange`, if present, is two numbers, `min ≤ max`, and contains `age` when both exist"; "sweep ages strictly increase in list order"; warning for no age), with `age`/`ageRange` as optional fields in `check_manifest_shape`; make T005 pass.
- [x] T011 [P] Create `site/js/core/ages.js` with `sweepAge`, `ageLabel`, `ageAxis`, `cells` (JSDoc each; research R2: ordinal union of distinct ages, unknown last; one cohort = its sweeps); make T006 pass.
- [x] T012 [P] Create `site/js/core/cohorts.js` with `parseChoice`, `formatChoice`, `chooseInitial`, `toggleChoice`, `colourSlot` and the pinned map (`ncds` 1, `bcs70` 2, `next_steps` 3, `mcs` 4); make T007 pass.
- [x] T013 Change `site/js/core/selection.js` (entries carry `cohort`; `keyOf`, `toItem`, `restore`, `has`), `site/js/core/topics.js` (filter items `{kind, id}`; `idIndex(scheme)` map), and `site/js/core/search.js` (`filterVariables` takes ids and a level name, reports `untagged`; new `searchCohorts`); make T008 pass, keeping every existing Node test green.
- [X] T014 Rework `site/js/ui/state.js` to the data-model shapes: `cohorts: Map`, `chosen: []`, `results: []`, `bundles: Map`, `waveFilter`/`fileFilter` as `{cohort, i}|null`, `topicSel` by id, `levelFilter` by name; keep `state.manifest`/`state.vars` only if needed as "the single chosen cohort" shims, removed by the end of US1.
- [X] T015 Update `site/js/ui/boot.js`, `results.js`, `overview.js`, `panel.js`, `review.js`, `selected.js` to the new state and keys **with one cohort only** (the `<select id="dataset">` still picks one): storage of the selection stays `cohort-data-builder:<key>:selection` without the `cohort` field; `restore` adds it. Run `uv run pytest tests/python/e2e` and `npm test`: all existing tests pass unchanged (FR-005 baseline).
- [X] T016 [P] Add cohort colour tokens to `site/styles.css`: `--coh-1`…`--coh-6` with light values in `:root` and dark values under both `@media (prefers-color-scheme: dark) :root:not([data-theme="light"])` and `:root[data-theme="dark"]`; `[data-coh="1"] { --coh: var(--coh-1) }` … ; `.coh-mark` (vertical bar, 4px × 1em, `background: var(--coh)`) and `.coh-tag` (short-name text with a left border in `var(--coh)`), visibly different from the square `.dom-swatch` (research R9). Choose values distinct from every `--d-*` domain colour and ≥ 3:1 against the page background in both themes.
- [X] T017 Update `specs/001-cohort-data-builder/contracts/site-data.md` and `docs/data-format.md` with `age`/`ageRange` (from `contracts/sweep-ages.md`); update JSDoc of every changed export. Run the full suite and lint; open the `007-foundation` PR with "How to review" (single-cohort site unchanged; new modules; fixture `mini2`).

**Checkpoint**: one-cohort site unchanged; core ready for several cohorts.

---

## Phase 3: User Story 1 - Choose and search several cohorts together (Priority: P1) 🎯 MVP

**Goal**: Toggle cohorts in the header; one search across all chosen; results grouped by
cohort with cohort tags; per-cohort counts; choice in address and storage
(`contracts/cohort-choice.md`, `contracts/variables-view.md` "Filter bar and results").

**Independent Test**: Choose `mini` and `mini2`, search `smok`: two groups, `mini`'s
`smoke5` and `mini2`'s smok variable, each row tagged; the count reads total and one
number per cohort.

### Tests for User Story 1 ⚠️ write first, see them fail

- [ ] T018 [US1] `tests/python/e2e/test_007_choose.py`: first visit to `mini_site` → `.cohorts button[data-cohort="mini"]` `aria-pressed="true"`, `mini2` `false`, no `.v-group` headings, list as today (clarification Q3, FR-005); press `mini2` → both pressed, address hash `#mini+mini2`, two `.v-group` headings in order Mini, Mini2 with counts; reload → same choice; open `serve(mini_site)+"#mini2+mini"` in a new page → both chosen; `#mini2+nope` → only `mini2`; pressing the only pressed button leaves it pressed and it has `aria-disabled="true"` (FR-001–FR-004).
- [ ] T019 [US1] Same file: with both chosen, type `smok` → each group shows only its matches; `#result-count` text contains the total and `Mini` and `Mini2` counts; clicking the `Mini2` count scrolls `#vscroll` to the Mini2 heading; each `.v-row` has a `.coh-tag` with the cohort short name; the two `sex` variables appear as two rows with keys `mini:0:sex` and `mini2:<i>:sex` and selecting one leaves the other unselected (FR-008–FR-010, FR-009a).
- [ ] T020 [US1] Same file: with both chosen, set a file filter on a `mini2` file (from a variable's details "show this file") → chip text contains `Mini2 ·`; `mini` group heading reads "filtered to Mini2 · <file>" with a "Clear filter" button, and clicking it restores `mini` results; set the filter again, then press `mini3` in the header: its heading reads the same; remove `mini2` from the header → the filter chip disappears and `mini` results return (FR-007, edge case). Choose the level "ORDINAL" → both cohorts filtered by it.
- [ ] T021 [US1] Same file: route `**/data/mini2/index.json` to HTTP 500, press `mini2` → its group/overview shows an error naming Mini2 with a "Retry" button, `mini` results still work; unroute and press Retry → `mini2` loads (edge case, research R7). Also: `document.title` is `Mini + Mini2 · Cohort Data Builder`, `#mark-sub` is `Mini + Mini2`, `#foot-counts` sums variables and files and ends `· 2 cohorts` (FR-016).
- [ ] T022 [US1] Update `tests/python/e2e/test_subpath.py` to open `#mini+mini2` under the sub-path and assert both cohorts load; update any test that used `#dataset` to use `.cohorts button[data-cohort=…]`. Commit `test(007-us1): choose and search several cohorts`.

### Implementation for User Story 1

- [ ] T023 [US1] Replace `<select id="dataset">` in `site/index.html` with `<div class="cohorts" role="group" aria-label="Cohorts">` and render one toggle button per catalogue cohort in `site/js/ui/boot.js` (`data-cohort`, `data-coh` from `colourSlot`, `.coh-mark`, short name, `aria-pressed`, `aria-disabled` + title "At least one cohort stays chosen" when it is the only one, `aria-busy` while loading); style and phone-width wrapping in `site/styles.css`.
- [ ] T024 [US1] In `site/js/ui/boot.js`: choose with `chooseInitial` (address, `_site:cohorts`, old `_site:cohort`, first); load each chosen cohort once into `state.cohorts` with status `loading|ready|failed`; on toggle load if needed then search; write the hash with `formatChoice` (`history.replaceState`) and storage `_site:cohorts`; handle `hashchange`; clear a sweep or file filter belonging to a removed cohort; Retry reloads a failed cohort; title, `#mark-sub` and `#foot-counts` per `contracts/cohort-choice.md`.
- [ ] T025 [US1] In `site/js/ui/results.js`: run `searchCohorts` over chosen ready cohorts; render `state.results` concatenated with a `.v-group` heading per cohort (mark, full name, count / "no matches" / "no topic tags") only when more than one cohort is chosen; `.coh-tag` on each row; row keys `<cohort>:<fileIndex>:<name>`; details name the cohort in full; `#result-count` with per-cohort buttons that jump to the group (reuse `jumpTo`, raising `state.shown` as needed); filter chips name the cohort for sweep and file filters; level dropdown is the union of chosen cohorts' level names with summed counts; "Select all" limit 500 across cohorts with per-cohort numbers in the message.
- [ ] T026 [US1] Remove the single-cohort shims from `site/js/ui/state.js` and their uses; ensure `resetForCohort` becomes a reset run only when the choice changes in a way that invalidates filters. Make T018–T022 pass; run the whole suite and lint. Open the `007-us1-choose-search` PR with a filled "How to review" (checkout, `npm test` and `uv run pytest tests/python/e2e/test_007_choose.py` expected green, then quickstart §2 steps 1–4 and 9–11).

**Checkpoint**: several cohorts searchable together (MVP).

---

## Phase 4: User Story 2 - The overview stacks by cohort (Priority: P1)

**Goal**: Description line and sweep row per cohort on one age axis; topic sub-rows per
cohort (`contracts/variables-view.md` "Overview").

**Independent Test**: Choose `mini` and `mini2`: two `#ov-about` lines; two sweep rows whose
columns are ages 3, 5, 7, 10, 11 and "?"; Topics → a domain: each topic has a Mini sub-row
with cells and a Mini2 sub-row; with `mini3` chosen too, a Mini3 sub-row reads "no topic
tags".

### Tests for User Story 2 ⚠️ write first, see them fail

- [ ] T027 [US2] `tests/python/e2e/test_007_overview.py`: one cohort → overview markup as today (one `.ov-total` row, columns = sweep keys, no sub-rows). Two cohorts → `#ov-about` has two lines in catalogue order with `.coh-mark`, full name and counts (FR-011); an axis row labels columns `3, 5, 7, 10, 11, ?`; one sweep row per cohort labelled with short name and total; `mini`'s bars sit in columns 5, 10 and `?` (its `xwave`), `mini2`'s in 3, 7, 11 and `?` (FR-012, FR-012a/b).
- [ ] T028 [US2] Same file: search `zzzz` (no matches) → both rows still present with total `0` (FR-013); click `mini2`'s age-7 bar → list shows only `mini2` wave `w2` and the chip reads `Mini2 · w2` (US2 scenario 4); open Topics and a domain present in `mini` → each topic row has total, a `Mini` sub-row with cells on the same columns and a `Mini2` sub-row with cells (Smoking has a count at age 11); choose `mini3` too, and a `Mini3` sub-row reads "no topic tags"; opening Health with `mini` and `mini2` lists `Vaping` with no `Mini` cells and a `Mini2` count (FR-014, FR-015); click a `Mini` sub-row cell → filter is that topic at that `mini` sweep.
- [ ] T029 [US2] Same file: at 390×800, two cohorts, `#ov-chart` scrolls horizontally inside itself if needed with row labels visible, and `document.documentElement.scrollWidth <= 390` (SC-006). Commit `test(007-us2): stacked overview on an age axis`.

### Implementation for User Story 2

- [ ] T030 [US2] `site/js/ui/overview.js` `renderAbout`: one line per chosen cohort with `.coh-mark`, full name, description, counts; loading and failed states with Retry (shared with T024).
- [ ] T031 [US2] `site/js/ui/overview.js` `renderSpine`: build `ageAxis` from chosen manifests; axis label row (only with ≥ 2 cohorts); one row per cohort (`data-cohort`, `.coh-mark`, short name, total) with a cell per column via `cells`; bar title `<cohort> <sweep key> (age <label>) — n variables`; click sets `waveFilter = {cohort, i}`.
- [ ] T032 [US2] `site/js/ui/overview.js` `renderTopicGrid`: per topic/domain row show the total across cohorts and, with ≥ 2 cohorts, a sub-row per chosen cohort (mark, short name, total, cells on the axis; "no topic tags" for untagged cohorts); "within topic" shading per sub-row, "across topics" one scale; cell click narrows to that topic at that cohort's sweep. Domains and topics are matched by id across cohorts.
- [ ] T033 [US2] `site/styles.css`: axis row, column widths, sub-row indentation, horizontal scroll of `#ov-chart` with sticky row labels, both themes and all text sizes. Make T027–T029 pass; full suite; open `007-us2-overview` PR with a filled "How to review" (quickstart §2 steps 2, 4, 5 and 12; `overview.js` needs close reading).

**Checkpoint**: US1 + US2 work together; overview compares cohorts.

---

## Phase 5: User Story 3 - One selection across cohorts, downloaded together (Priority: P1)

**Goal**: Selection grouped by cohort, kept when a cohort is removed, checked per cohort,
downloaded as one zip with a folder per cohort (`contracts/multi-cohort-download.md`,
`contracts/variables-view.md` "Selected panel and Selection view").

**Independent Test**: Select `mini` `smoke5`, `alc10` and two `mini2` variables; open
Selection: groups Mini (2) and Mini2 (2); download: `cohorts-merge-<date>/README.md`,
`mini-merge-<date>/`, `mini2-merge-<date>/`.

### Tests for User Story 3 ⚠️ write first, see them fail

- [ ] T034 [P] [US3] `tests/js/codegen.test.mjs`: `buildBundle([oneProject], …)` deep-equals `buildProject(…)` (FR-024); `buildBundle([mini, mini2], templates, options, "2026-11-26")` → name `cohorts-merge-2026-11-26`; files are `cohorts-merge-2026-11-26/README.md` plus every file of each `buildProject` result prefixed with `cohorts-merge-2026-11-26/`, byte-identical, mini folder first (SC-005, FR-020); README contains `4 variables from 2 cohorts`, a line per cohort naming its folder, and the sentence that cohorts are not merged with each other (FR-023); `buildBundle([])` throws.
- [ ] T035 [P] [US3] `tests/js/columns.test.mjs`: problems computed per cohort — a `mini` and a `mini2` entry both with column `sex2` give no clash; two `mini` entries with the same column still clash (FR-019). Test new `problemsByCohort(bundles, manifests, format, languages)` in `site/js/core/columns.js`: it takes `Map<cohort, SelectedVariable[]>` and `Map<cohort, manifest>`, returns one `Map` keyed by `keyOf` (`<cohort>:<file>:<name>`), and equals calling `problems()` on each cohort's part with that cohort's identifier. An identifier clash is checked against each cohort's own identifier: a `mini2` column named `PID` is fine, while a `mini2` column named `CID` clashes.
- [ ] T036 [US3] `tests/python/e2e/test_007_selection.py`: with both cohorts chosen, select two variables from each → `#sp-list` and the Selection view show cohort headings `Mini (2)`, `Mini2 (2)` in catalogue order, then sweep groups (FR-018); download button text `Download 4 variables from 2 cohorts` (FR-025); rename a `mini2` column to a `mini` column's name → no problem shown (FR-019); un-press `mini2` → its group remains, marked "not being searched", and still counts in the button (FR-017).
- [ ] T037 [US3] Same file: seed `localStorage` with saved selections for `mini` and `mini2` (old format, no `cohort` field), open with only `#mini` → both groups appear after load (research R6); a saved entry naming a variable absent from `mini2`'s index is dropped. Click download (capture with `page.expect_download`) → zip name `cohorts-merge-<date>.zip`, entries match the contract layout. Commit `test(007-us3): grouped selection and bundle download`.
- [ ] T038 [US3] `tests/python/generated/test_generated_scripts.py`: add `fabricate_mini2()` (fixed seed, invented `CID` values, files `mini2_age3`, `mini2_w2`, `mini2_age11`); extend `tests/js/generate_bundle.mjs` to accept `--bundle` with picks prefixed `<cohort>/<file>:<var>`; test that each cohort folder of a two-cohort bundle, run in R and Python on its fabricated data, produces output identical to that cohort's single-cohort project (SC-005, FR-021), and that the `mini2` output is keyed on `CID` only. Commit with T034–T037 if not already.

### Implementation for User Story 3

- [ ] T039 [US3] Add `site/templates/cohorts-README.md` with placeholders `{{created}}`, `{{count}}`, `{{cohorts}}`, `{{languages}}` and the fixed text from `contracts/multi-cohort-download.md` ("the cohorts are different people and are not merged with each other"; each folder runs on its own; data goes in each folder's `data/`; harmonising is up to the researcher).
- [ ] T040 [US3] Add `buildBundle(projects, templates, options, today)` to `site/js/core/codegen.js` (JSDoc; one project → `buildProject` result; several → prefixed folders in the given order plus README; throws on empty); add `cohorts-README.md` to `TEMPLATE_FILES` in `site/js/ui/review.js` and `tests/js/generate_bundle.mjs`; make T034 and T038 pass.
- [ ] T041 [US3] `site/js/ui/selected.js`: `state.bundles` per cohort; `setSelection(cohort, next)` saves to that cohort's key without the `cohort` field; at boot read every catalogue cohort's saved selection and load unchosen cohorts that have one in the background, then `restore` (research R6).
- [ ] T042 [US3] `site/js/ui/panel.js` and `site/js/ui/review.js`: group by cohort (mark, name, count, "not being searched" when unchosen) then sweep/file; per-cohort problems via `problemsByCohort` from `site/js/core/columns.js` (added in this task, to pass T035), `fixDots` per cohort; download button text per FR-025; `download()` loads dictionaries per cohort (`loadDict(fetch, cohort, file, cache)`), calls `buildBundle` with projects in catalogue order, zips and names the file from its result. Make T035–T037 pass.
- [ ] T043 [US3] Update `specs/001-cohort-data-builder/contracts/download-project.md` (link to the multi-cohort layout) and the "Download" section of `README.md`. Full suite and lint; open `007-us3-selection-download` PR (How to review: unzip and run one folder in R).

**Checkpoint**: US1–US3 deliver search-to-download across cohorts.

---

## Phase 6: User Story 4 - A colour for each cohort (Priority: P2)

**Goal**: Same colour per cohort everywhere, light and dark, always with its name, distinct
from domain markers.

**Independent Test**: Choose both cohorts; the mark colour of Mini is identical in the
header, overview, result tags, Selected panel and Selection view, in both themes.

### Tests for User Story 4 ⚠️ write first, see them fail

- [ ] T044 [US4] `tests/python/e2e/test_007_colour.py`: with both cohorts chosen and a selection from each, collect `getComputedStyle(el).getPropertyValue('--coh')` (or the bar's background colour) for every `[data-cohort="mini"] .coh-mark`/`.coh-tag` in header, overview, results, `#sp-list` and Selection view → one value for Mini and a different one for Mini2; repeat with `data-theme="dark"` → values differ from light but are still one per cohort (FR-026, US4.1); every `.coh-mark` has visible cohort text in the same control or row (FR-027); `.coh-mark` and `.dom-swatch` differ in computed width/height (FR-028).
- [ ] T045 [US4] Extend `tests/python/e2e/test_accessibility.py` to run axe with both cohorts chosen and Topics open, in light and dark themes and at the largest text size: no serious or critical violations (FR-029, SC-006). Add a Python test that reads `site/styles.css`, extracts `--coh-1…6` light and dark values and the page background, and asserts each pair ≥ 3:1 contrast and all six mutually distinct and distinct from every `--d-*` value. Commit `test(007-us4): cohort colours`.

### Implementation for User Story 4

- [ ] T046 [US4] Apply `data-coh`/`data-cohort` and `.coh-mark`/`.coh-tag` wherever a cohort appears that US1–US3 missed (details panel heading, filter chips, tag-suggestion dialog title); adjust token values in `site/styles.css` until T044–T045 pass. Open `007-us4-colour` PR with a filled "How to review" (both themes, largest text; token values in `styles.css` need close reading).

---

## Phase 7: User Story 5 - The tutorial covers several cohorts (Priority: P3)

**Goal**: Tutorial explains choosing several cohorts, shows the colours, demo panels across
two cohorts, multi-cohort download.

**Independent Test**: Open `tutorial/`: intro lists cohorts with `.coh-mark`s and says they
can be searched together; Search/Explore demos show two cohort groups and two sweep rows;
Download step shows a `cohorts-merge-…/` tree.

### Tests for User Story 5 ⚠️ write first, see them fail

- [ ] T047 [US5] Extend `tests/python/e2e/test_tutorial.py`: `#t-cohort-list` items each have a `.coh-mark` whose colour equals the builder's for the same key (same stylesheet); intro text mentions searching cohorts together; the Search demo, typing `smok`, lists rows from two cohorts each with a `.coh-tag`; the Explore demo shows two sweep rows on one age axis; the Download step contains `cohorts-merge-` and two `-merge-` folders; no sideways scroll at 390px. Commit `test(007-us5): tutorial for several cohorts`.

### Implementation for User Story 5

- [ ] T048 [US5] In `site/tutorial/tutorial.js` add a second cohort's demo variables (ask the user to supply 3–4 real NCDS or Next Steps smoking/alcohol variable names, labels, sweeps and value labels from the published dictionaries, since `site/data/` is closed to the assistant; never invent them as if real), give each demo variable a `cohort`, and render cohort groups, tags and two sweep rows on an age axis (reuse `site/js/core/ages.js` if the tutorial can import it; else mirror its rule and note why).
- [ ] T049 [US5] In `site/tutorial/index.html` and `tutorial.css`: intro sentence and cohort list with marks; Select and Download steps describe the grouped selection and the folder-per-cohort zip (tree sketch); Run step says to run each folder on its own and that cohorts are not merged; mention that earlier saved selections of several cohorts now appear together (research R6). Make T047 pass; open `007-us5-tutorial` PR with a filled "How to review" (quickstart §2 step 13; tutorial copy needs close reading).

---

## Phase 8: Polish & Cross-Cutting Concerns

- [ ] T050 [P] `tests/python/e2e/test_performance.py`: with every fixture cohort chosen and the `mini` index replicated to ~115,000 rows in a temp site, a new search redraws in under 1 s; adding a cohort shows its rows in under 3 s on the local server (SC-002, SC-003).
- [ ] T051 [P] `tests/python/e2e/test_responsive.py` and `test_text_size.py`: header cohort group wraps without sideways scroll at 390px with four cohorts (add two more fictional catalogue entries in a temp copy) at every text size.
- [ ] T052 [P] Update `README.md` (what the site does: several cohorts; colours; download layout), `CLAUDE.md` (one line naming feature 007 and its spec folder) and JSDoc of every touched export; check `docs/data-format.md` mentions sweep ages.
- [ ] T053 Run `specs/007-multi-cohort-search/quickstart.md` §1 and §2 by hand on the real site (the user, since `site/data/` is closed to the assistant) and record results in the final PR's "How to review".
- [ ] T054 Merge-readiness: full `uv run pytest`, `npm test`, `npm run lint`, `uv run ruff check . && uv run ruff format --check .`; open the PR from `007-multi-cohort-search` to `main` (do not merge).

---

## Dependencies & Execution Order

- **Setup (T001–T004)** → **Foundational (T005–T017)** → stories.
- **US1 (T018–T026)** depends on Foundational. MVP.
- **US2 (T027–T033)** and **US3 (T034–T043)** depend on US1 (cohort control, multi-cohort
  state, grouped results); independent of each other and can run in parallel.
- **US4 (T044–T046)** after US1–US3 (audits every place a cohort appears).
- **US5 (T047–T049)** after US2 and US3 (demos mirror overview and download).
- **Polish (T050–T054)** last.
- Within each phase: tests → commit failing tests → implementation.
- T002's age edits to `site/data/` (if any) land after T010 so the checks validate them.

## Parallel Opportunities

- Foundational tests T005, T006, T007, T008 (four files); implementation T010, T011, T012,
  T016 (four files).
- US3 tests T034 and T035 (Node, separate files) alongside T036–T038.
- US2 and US3 on separate branches after US1.
- Polish T050, T051, T052.

### Parallel example: Foundational

```text
T005 tests/python/data/test_checks.py   T006 tests/js/ages.test.mjs
T007 tests/js/cohorts.test.mjs          T008 tests/js/{selection,topics,search}.test.mjs
then
T010 scripts/checks.py   T011 site/js/core/ages.js   T012 site/js/core/cohorts.js   T016 site/styles.css
```

## Implementation Strategy

1. **MVP**: Setup + Foundational + US1 → several cohorts searchable together, grouped,
   with addresses that share a choice. Ship and user-test.
2. **Increment**: US2 (compare coverage) and US3 (download across cohorts) in parallel.
3. **Finish**: US4 colour audit, US5 tutorial, Polish.
4. Each story is a PR off `007-multi-cohort-search` with a filled "How to review"; nothing
   is merged by the assistant.
