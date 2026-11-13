---

description: "Task list for feature 003: updates from user testing"
---

# Tasks: Updates from user testing

**Input**: Design documents from `/specs/003-user-testing-updates/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Required. The constitution (Principle I) makes test-first non-negotiable: every
test task is written, run and seen to fail, and committed as `test(…)` before the
implementation task that follows it is started.

**Organization**: One phase per user story, in priority order. Each story is its own short
branch off `003-user-testing-updates` (see plan.md) with one pull request.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1–US4)

## Path Conventions

Static site in `site/`; Node tests in `tests/js/`; browser tests in `tests/python/e2e/`;
generated-script tests in `tests/python/generated/`. Fixture cohort `mini` is served by
the `mini` / `mini_site` fixtures.

---

## Phase 1: Setup

**Purpose**: Things the stories need from outside the code.

- [x] T001a Amend `.specify/memory/constitution.md` with the licensed-tools exception to Principle I (v1.2.0, Sync Impact Report, Last Amended 2026-11-13); commit `docs(constitution): licensed-tools exception to tests in CI`.
- [x] T001 Create the `tag-suggestion` label in the GitHub repository (colour of your choice, description "A user's suggestion to change a variable's topic tags") with `gh label create tag-suggestion --description "…"`; record in the US4 pull request that it exists.

---

## Phase 2: Foundational

**Purpose**: None. The four stories touch separate code paths; US2 builds on US1's markup,
which is shown as a dependency below rather than a shared phase.

---

## Phase 3: User Story 1 - One list of selected variables (Priority: P1) 🎯 MVP

**Goal**: The Selection tab lists each selected variable once, with rename and remove in
that one list (contracts/selection-view.md, Structure).

**Independent Test**: Select 3 variables, open Selection: 3 variable rows in
`#basket-cols`, each with an output-column input and a "Remove <name>" button; no
`#basket-list`, no "Resize the list" separator.

### Tests for User Story 1

- [x] T002 [US1] In `tests/python/e2e/test_us3_download.py`, replace `test_selection_list_removes_and_divider_resizes` with `test_one_list_renames_and_removes`: pick `smoke5` and `alc10`, open Selection; assert `#basket-list` has count 0 and no `separator` named "Resize the list" exists; assert `#basket-cols li` has 3 items (identifier + 2); click the button named "Remove smoke5" → `#basket-cols li` has 2, `#basket-tally` reads `1`, and on the Variables tab the `smoke5` row is no longer selected (`aria-pressed="false"` on its row button).
- [x] T003 [US1] In the same file, add `test_dropping_a_variable_anywhere_on_selection_adds_it`: open Selection, then in `page.evaluate` build a `DataTransfer`, set `DRAG_MIME` (`"application/x-cohort-data-builder-variable"`, from `site/js/ui/state.js`) to the `alc10` key `mini_age10:alc10`, and dispatch `dragenter`, `dragover` and `drop` events carrying it on `section.view[data-view="basket"]` (not a pane) → `#basket-cols` gains `alc10`.
- [x] T004 [US1] Update every other selector in `tests/python/e2e/test_us3_download.py` that relies on `#basket-list` to use `#basket-cols`; run `uv run pytest tests/python/e2e/test_us3_download.py` and see T002/T003 fail; commit `test(selection): one list with rename and remove`.

### Implementation for User Story 1

- [x] T005 [US1] In `site/index.html`, remove the Selection view's left pane (`#basket-drop` with `#basket-list`, the `finder` block) and the `.grip` separator, leaving `#basket-detail` as the view's only pane.
- [x] T006 [US1] In `site/js/ui/review.js`: delete `renderList()` and the grip/resize code (the `grip` handlers and its stored width); give the columns `ol` the id `basket-cols`; add to `colRow()` a remove button `<button class="add is-in basket-x" data-remove="<key>" aria-label="Remove <name>" title="Remove">` before the input, reusing the existing `data-remove` click handling (move the listener from `#basket-list` to `#basket-detail`); move the drop handlers from `#basket-drop` to `section.view[data-view="basket"]`. Update the module's top comment, which describes two panes.
- [x] T007 [US1] In `site/styles.css`, remove the `.grip`, `body.is-resizing` and two-pane Selection rules that no longer apply; style `.col-row .basket-x` to sit at the row's start, at least 28×28px, and keep the identifier row aligned with an empty slot of the same width.
- [x] T008 [US1] Run `uv run pytest tests/python/e2e` and `npm run lint`; fix regressions (including `test_accessibility.py` and `test_responsive.py` on the Selection view); commit `feat(selection): one list with rename and remove`; tick T002–T008.

**Checkpoint**: US1 complete and shippable on its own (branch `003-us1-one-list`).

---

## Phase 4: User Story 2 - Download always in reach (Priority: P1)

**Goal**: The download options and button stay in view while the list scrolls
(contracts/selection-view.md, Layout rules). **Depends on US1** (single-pane markup).

**Independent Test**: With 80 variables selected at 1366×768, `#basket-download` is in the
viewport without scrolling the page; scrolling the list leaves it in place. At 390×844 the
download button is visible at the bottom and the page has no horizontal scroll.

### Tests for User Story 2

- [x] T009 [P] [US2] Add `tests/python/e2e/test_selection_layout.py`. Serve the real site data (the same `serve` + real-data setup as `test_real_large_group_shows_200_until_show_all` in `tests/python/e2e/test_us2_selection.py`), choose BCS70, search `smok`, and press **Select all** (≥ 80 results; assert the count first): at viewport 1366×768, open Selection; assert `#basket-download` bounding box lies within the viewport, `document.documentElement.scrollHeight <= innerHeight + 1`, and that scrolling the list container (`#basket-scroll`) by 2000px leaves `#basket-download`'s `y` unchanged; and with a column renamed to `1bad`, `#basket-download` is disabled and `#basket-download-area` shows "1 column name needs changing" with a button that, when clicked, scrolls `#basket-cols` so the problem row is in view and focuses its input.
- [x] T010 [P] [US2] In the same file: at 390×844 with 30 variables selected, assert `#basket-download` is visible in the viewport on first load of Selection, `scrollWidth <= 390`, and that clicking the button named "Download options" reveals the R checkbox, then axe reports no serious or critical problems with the options open; at 1366×768 the "Download options" toggle is hidden and the options are visible. Run, see T009/T010 fail, commit `test(selection): download stays in view`.

### Implementation for User Story 2

- [x] T011 [US2] In `site/js/ui/review.js` `renderDetail()`, split the output into two containers: `#basket-scroll` (head, warnings, "Data files it needs" `#basket-files` first, then "Columns" `#basket-cols`) and `#basket-download-area` (a `<button class="link-btn" id="dl-toggle" aria-expanded="false" aria-controls="dl-options">Download options</button>`, `#dl-options` holding `optionsHtml(...)`, then the download button `#basket-download` and `#basket-status`). Keep `#basket-download-area` outside `#basket-scroll` so it is not re-rendered when only columns change; wire `#dl-toggle` to toggle `aria-expanded` and `hidden` on `#dl-options`. When download is blocked, `#basket-download-area` shows the reason beside the button ("N column name(s) need changing", or "Choose at least one language") and, for column problems, a `link-btn` "Show" that scrolls to and focuses the first problem input.
- [x] T012 [US2] In `site/styles.css`, add the Selection layout: `@media (min-width: 1024px) and (min-height: 700px)` → when the basket view is current, the body is `height: 100dvh` like the Variables rule at `body:has(.view[data-view="search"].is-current)`; the view is a column flex; `#basket-scroll` is `flex: 1; min-height: 0; overflow-y: auto`; `#basket-download-area` sits below it with a top border, `background: var(--paper-2)` and `box-shadow: var(--shadow)`; `#dl-toggle` is hidden and `#dl-options` always shown. Otherwise → `#basket-download-area { position: sticky; bottom: 0 }`, `#dl-options` hidden until toggled, no horizontal overflow at 390px.
- [x] T013 [US2] Run `uv run pytest tests/python/e2e` and `npm run lint`; check axe in light and dark on the Selection view; commit `feat(selection): keep the download in view`; tick T009–T013.

**Checkpoint**: US1 + US2 make the Selection tab fix complete (branch `003-us2-download-in-view`).

---

## Phase 5: User Story 3 - Stata code (Priority: P2)

**Goal**: Stata as a third code language producing the same data as R/Python
(contracts/stata-project.md; research R3, R4).

**Independent Test**: `npm test` passes the Stata codegen tests; with Stata installed,
`uv run pytest tests/python/generated -k stata` runs the do-file on the fixture data and
its output equals the R output.

### Tests for User Story 3

- [x] T014 [P] [US3] In `tests/js/codegen.test.mjs`, add: `build({ languages: ["stata"] })` produces exactly the common files plus `stata/load_data.do` and `stata/merge.do`; `["r","python","stata"]` produces all; the README for Stata only says "written in Stata" and contains `do stata/merge.do`; `merge.do` contains `local OUTPUT_FORMAT "dta"` / `local MISSING_TO_NA 1` / `local IDENTIFIER "PID"` for the matching options; each file's block lists source names and output columns in the same order; a label containing `"`, `` ` `` , `$` and a newline is written as a Stata compound-quoted string (`` `"…"' ``) with the newline replaced by a space and `$`/`` ` `` unable to expand; missing-code values and ranges become `replace <col> = . if inlist(<col>, …)` and `inrange(<col>, lo, hi)` lines, an open low end as `<col> <= hi`, an open high end as `<col> >= lo` (and `!missing(<col>)` guards); no `{{…}}` placeholder remains.
- [x] T015 [P] [US3] In `tests/js/columns.test.mjs`, add: `problems(selection, id, "csv", ["stata"])` reports the Stata name rule (e.g. a column `a.b` or 33 characters) exactly as `format "dta"` does today; with languages `["r"]` and format `csv` it does not. (Adds a 4th `languages` parameter, defaulting to `[]`.)
- [x] T016 [P] [US3] In `tests/python/generated/conftest.py`, add a `needs_stata` marker and a `stata_binary()` helper: `CDB_STATA` env var, else the first existing of `stata-mp`, `stata-se`, `stata` on `PATH`, else `/Applications/Stata*/Stata*.app/Contents/MacOS/stata-*` (glob); skip marked tests when none (no "require" flag: Stata cannot run in CI). Register the marker in `pyproject.toml` beside `needs_r`.
- [x] T017 [US3] In `tests/python/generated/test_generated_scripts.py`, add `needs_stata` tests mirroring the R/Python ones: `test_stata_agrees_with_r` (parametrised over input formats `tab, csv, dta, sav` and outputs `csv, dta`; generate with `--languages r,stata` via `tests/js/generate_bundle.mjs`, run `stata -b do stata/merge.do` in the project folder, compare `output/merged.*` with R's after sorting by `PID`, as `test_r_and_python_agree_for_every_format` does); `test_stata_writes_the_grid_apart` (`mini_grid` → `output/mini_grid_long.*`); `test_stata_missing_to_na` (on/off); `test_stata_missing_file_stops`; `test_stata_sav_output_writes_dta_with_a_note`. Run `npm test` and `uv run pytest tests/python/generated -k stata` and see them fail (Stata ones skip if Stata is absent); commit `test(stata): Stata code matches R and Python`.

### Implementation for User Story 3

- [x] T018 [P] [US3] Create `site/templates/stata/load_data.do`: programs (`program define`) to index `DATA_DIR` recursively and find a file by name with any of `.tab .csv .dta .sav`; read by extension (`use`, `import delimited` with `delimiters(tab)` for `.tab`, `import spss`), keeping only the identifier and wanted variables and warning about absent ones; find the identifier case-insensitively and `strtrim` it; apply missing codes; write output by format (`export delimited`, `save`; `sav` → `save` as `.dta` and `display` a note). Comment each program for a Stata reader. Behaviour per contracts/stata-project.md, Behaviour 1–6.
- [x] T019 [P] [US3] Create `site/templates/stata/merge.do` with the settings block (`DATA_DIR`, `OUTPUT_DIR`, `OUTPUT_FORMAT`, `MISSING_TO_NA`, `IDENTIFIER`), `{{selection}}`, `{{missing_codes}}`, `{{labels}}` and `{{value_labels}}` placeholders, and the merge: check all files first (`exit 601` listing the missing), per file read → rename → missing codes → `duplicates drop` → if not `isid` write `<file>_long` and continue, else `tempfile`; then successive `merge 1:1` keeping all, `drop _merge`, labels, write `merged`. Header comment says how to run it (contract, "How it is run").
- [x] T020 [US3] In `site/js/core/codegen.js`: add `stataSelection`, `stataCodes`, `stataLabels`, `stataValueLabels` writers (compound-quoted strings, newline → space); in `buildProject` add the `stata` branch writing `stata/load_data.do` and `stata/merge.do` with `missing_to_na` `1`/`0`; make `runSteps`, `contents` and the `languages` README sentence handle any combination of R, Python and Stata; update the JSDoc of `buildProject` (options.languages now `("r"|"python"|"stata")[]`).
- [x] T021 [US3] In `site/templates/README.md`, make the run steps and contents placeholders cover Stata (filled by T020); state Stata 16+ and that Stata cannot write `.sav`.
- [x] T021a [US3] In `README.md`, add "Stata" to what the download contains and how to run it (`do stata/merge.do`, Stata 16+, no `.sav` output from Stata); in `specs/001-cohort-data-builder/contracts/download-project.md`, add the two `stata/` files to the layout and link `specs/003-user-testing-updates/contracts/stata-project.md`.
- [x] T022 [US3] In `site/js/core/columns.js`, add the `languages` parameter to `problems()` (JSDoc updated): apply the `dta` rule when `format === "dta"` or `languages.includes("stata")`. Pass `state.options.languages` from `currentProblems()` in `site/js/ui/review.js`.
- [x] T023 [US3] In `site/js/ui/review.js`: add `stata/load_data.do` and `stata/merge.do` to `TEMPLATE_FILES`; add a Stata checkbox `<label><input type="checkbox" data-lang="stata"> Stata (do-file)</label>` after Python in `optionsHtml()`, so it is not mistaken for the "Stata (.dta)" format; make the button label list the chosen languages (`Download R + Stata do-file`); keep "no language → button disabled". In `site/js/ui/selected.js` line ~60, accept `"stata"` in stored `languages` (unknown values still dropped, data-model.md).
- [x] T024 [US3] Add an e2e test then make it pass, in `tests/python/e2e/test_us3_download.py`: `test_stata_option_adds_do_files_to_the_zip` (tick Stata, untick R and Python, download, the zip lists `stata/merge.do` and `stata/load_data.do` and no `R/`), and extend `test_options_persist_and_no_language_disables_download` to include Stata; add an assertion that options stored before this feature (seed storage with `{languages:["r"]}`, reload) load with only R ticked. Commit test first, then fix.
- [x] T025 [US3] Run `npm test`, `uv run pytest`, and locally `uv run pytest tests/python/generated -k stata` with Stata; all pass; commit `feat(stata): Stata do-files in the download`; tick T014–T025. The pull request's "How to review" requires the reviewer to run `uv run pytest tests/python/generated -k stata` with Stata and report the result (constitution I, licensed-tools exception).

**Checkpoint**: Stata users get working code (branch `003-us3-stata`).

---

## Phase 6: User Story 4 - Suggest a better topic tag (Priority: P3)

**Goal**: A link in a variable's details opens a pre-filled GitHub issue form
(contracts/tag-suggestion.md; research R5, R6).

**Independent Test**: Open `smoke5`'s details: a link "Suggest a tag change" has
`target="_blank"` and an `href` starting
`https://github.com/CLS-Data/cohort-data-builder/issues/new?template=tag-suggestion.yml`
with `variable=smoke5`, `cohort=Mini`, the file and current tags.

### Tests for User Story 4

- [x] T026 [P] [US4] Create `tests/js/feedback.test.mjs` for `tagSuggestionUrl(entry, file, manifest)` from `site/js/core/feedback.js`: base URL and `template=tag-suggestion.yml`; `title` is `Tag suggestion: <variable> (<cohort>)`; `cohort`, `variable`, `file`, `label` and `current` are set and URL-encoded (test a label with `&`, `#`, `+`, `"`, non-ASCII); `current` is `Smoking (90%); Pregnancy (60%)` using topic labels from `manifest.topics`, and `none` when the entry has no topics; `label` is cut to 300 characters with `…`; a URL that would exceed 8,000 characters is cut (current tags first, then label) to ≤ 8,000 while keeping cohort, variable and file whole.
- [x] T027 [P] [US4] In `tests/python/e2e/test_us4_topics.py`, add `test_details_offer_a_tag_suggestion_link`: open `smoke5`'s details; the link named "Suggest a tag change" has `target="_blank"`, `rel` containing `noopener`, and an `href` whose query has `variable=smoke5` and `cohort=Mini`; a variable with no topics (e.g. `nolab5`) shows "Suggest a tag" instead; clicking the link (Playwright `expect_popup`) opens a new page and leaves the builder's search text and `#basket-tally` unchanged. Also add `tests/python/test_issue_template.py` asserting `.github/ISSUE_TEMPLATE/tag-suggestion.yml` parses as YAML with `labels: ["tag-suggestion"]` and field ids `cohort, variable, file, label, current, suggested, why`, `suggested` required. Run, see them fail, commit `test(tags): suggest a tag change`.

### Implementation for User Story 4

- [x] T028 [P] [US4] Create `site/js/core/feedback.js` exporting `REPOSITORY = "https://github.com/CLS-Data/cohort-data-builder"` (JSDoc: change here in a fork) and `tagSuggestionUrl(entry, file, manifest)` per contracts/tag-suggestion.md, with JSDoc for both; no DOM use.
- [x] T029 [P] [US4] Create `.github/ISSUE_TEMPLATE/tag-suggestion.yml` as an issue form per contracts/tag-suggestion.md (name, description, `title: "Tag suggestion: "`, `labels: ["tag-suggestion"]`, the seven fields with the ids, types and `required` flags listed; a short markdown intro saying tags come from a large language model and suggestions are reviewed by hand).
- [x] T030 [US4] In `site/js/ui/results.js`, after `topicsHtml(entry)` in the details, render `<a class="vm-suggest" href="…" target="_blank" rel="noopener">Suggest a tag change</a>` (or "Suggest a tag" when the entry has no topics) using `tagSuggestionUrl(entry, row file, state.manifest)`; style `.vm-suggest` in `site/styles.css` as a quiet mono link (`font-family: var(--mono); font-size: 11px; color: var(--sea)`), shown on the Topics line or alone.
- [x] T030a [US4] In `README.md`, add a short "Suggesting a tag change" note: where the link is, that it opens a GitHub issue form labelled `tag-suggestion`, and that it needs a GitHub account.
- [x] T031 [US4] Run `npm test`, `uv run pytest`, `npm run lint`; commit `feat(tags): suggest a tag change from a variable's details`; tick T026–T031.

**Checkpoint**: All four stories done (branch `003-us4-tag-suggestion`).

---

## Phase 6b: User Story 5 - Larger text (Priority: P3)

**Goal**: Text follows browser settings, plus a text-size control (FR-016, FR-017).

- [x] T036 [US5] Add `tests/python/test_text_scales.py` (no `font-size: …px` in `site/styles.css` or `site/tutorial/tutorial.css`; viewport meta has no `user-scalable`/`maximum-scale`) and `tests/python/e2e/test_text_size.py` (group "Text size" with "Normal text", "Larger text", "Largest text" buttons using `aria-pressed`; largest = 1.5× body and variable-name size; remembered after reload and on the tutorial; no sideways scroll at 1366px and 390px; axe clean). See them fail; commit `test(a11y): …`.
- [x] T037 [US5] Convert every pixel font size to `rem` (px ÷ 16) in both stylesheets; add `html[data-text="large"] { font-size: 125% }` and `"larger"` 150%; add the control to the header of `site/index.html` and `site/tutorial/index.html`, wired in `site/js/ui/boot.js` and `site/tutorial/tutorial.js`, stored as `cohort-data-builder:_site:text-size`; document in README; run all tests; commit `feat(a11y): …`.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [x] T032 [P] Check `README.md` and the contracts against the merged stories and fix anything the story pull requests missed.
- [x] T033 [P] Update the tutorial so it matches: in `site/tutorial/index.html` and `site/tutorial/tutorial.js`, add Stata to the Step 04 language checkboxes and the zip tree (`stata/merge.do`), add Stata to Step 05's R/Python switch (`do stata/merge.do`), describe the single Selection list and fixed download area in Step 03/04, and mention "Suggest a tag change" in Step 06; first extend `tests/python/e2e/test_tutorial.py` (Stata in the summary and run command) and see it fail.
- [ ] T034 Run the quickstart (`specs/003-user-testing-updates/quickstart.md`) end to end, including the Stata run, and fix anything it shows.
- [ ] T035 Merge `003-user-testing-updates` into `main` by pull request once every story's pull request is merged and CI is green; the "How to review" includes the local Stata run.

---

## Dependencies & Execution Order

- **Setup**: T001a before US3 starts (its Stata test relies on the exception); T001 before US4's pull request is merged (the form's label must exist).
- **US1 (P1)**: no dependencies. MVP.
- **US2 (P1)**: depends on US1 (it lays out US1's single pane).
- **US3 (P2)**: independent of US1/US2 in code paths except `review.js` `optionsHtml()`; if done in parallel with US2, rebase on US2 before T023.
- **US4 (P3)**: independent of all others.
- **Polish (T032–T035)**: after the stories they describe.

Within each story: tests → see them fail → commit `test(…)` → implementation → commit
`feat(…)`.

## Parallel Opportunities

- US4 can be built at any time alongside US1–US3.
- US3's T014, T015, T016 (different test files) in parallel; then T018 and T019 (two new
  templates) in parallel.
- US4's T026 and T027 in parallel; T028 and T029 in parallel.
- US2's T009 and T010 are in one new file: write them together.

### Parallel example: User Story 3

```text
T014 tests/js/codegen.test.mjs        T015 tests/js/columns.test.mjs        T016 tests/python/generated/conftest.py
then
T018 site/templates/stata/load_data.do                                      T019 site/templates/stata/merge.do
```

## Implementation Strategy

1. **MVP**: US1 alone fixes the most-reported confusion; ship it.
2. US2 next (same page, same testers' complaint), then release both.
3. US3 (Stata) as its own release; needs a local Stata run before merge.
4. US4 whenever convenient; create the label (T001) first.
5. Polish: README, tutorial, quickstart run, merge to `main`.
