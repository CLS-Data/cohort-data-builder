---

description: "Task list for Cohort Data Builder"
---

# Tasks: Cohort Data Builder

**Input**: Design documents from `/specs/001-cohort-data-builder/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/site-data.md,
contracts/download-project.md, quickstart.md

**Tests**: REQUIRED. Constitution Principle I (TDD, non-negotiable): every test task in a
phase MUST be written, run and seen to FAIL before the implementation tasks after it. Do not
weaken a test to make it pass.

**Behavioural reference**: `PoC/` is the reference for anything a task does not state. When a
task says "port from PoC/…", re-implement that behaviour test-first in the new module layout.
Do not copy code that has no failing test asking for it.

**Documentation (Principle II)**: every exported JS function gets a JSDoc comment (purpose,
`@param`, `@returns`, `@throws`). Every Python module, class and public function gets a
Google-style docstring (ruff `D` enforces this outside `test_*.py`).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on an incomplete task)
- **[Story]**: User story from spec.md (US1–US5)

## Path Conventions

Static site in `site/` (core logic `site/js/core/`, DOM code `site/js/ui/`, supplied data
`site/data/`, download templates `site/templates/`); tests in `tests/` split by runner:
`tests/js/` (node --test), `tests/python/{data,generated,e2e}/` (pytest), shared fixtures in
`tests/fixtures/`.

---

## Phase 0: Version Control (GitHub protocol)

**Purpose**: Make the constitution's merge gates (tests, lint, review confirming test-first)
enforceable before any code is written. See the Version control note in plan.md.

**Protocol for every later task**:

- Work happens on the integration branch `001-cohort-data-builder`, in one short-lived
  branch per phase or story (e.g. `001-setup`, `001-foundation`, `001-us1-search`), each
  merged into the integration branch by pull request once its checkpoint is green.
- Conventional Commits. Commit each failing test first (`test(us1): …`), then the code that
  passes it (`feat(us1): …` / `fix(…)`), so the history shows test-first.
- The integration branch reaches `main` by pull request after the P1 MVP (end of Phase 5)
  and again at the end of the feature; both use squash merge.

- [x] T001 Create the root `.gitignore` ignoring `PoC/` (separate local reference repository, never committed), `.DS_Store`, `.claude/settings.local.json`, `.claude/.cc-writes/`, `**/.Rhistory`, and commit the Spec Kit setup on `main` as the initial history: `.specify/` (minus its own ignores), `.claude/skills/speckit-*` (except the deprecated `speckit-taskstoissues`), `specs/001-cohort-data-builder/`, and `.gitignore`
- [x] T002 Create the integration branch `001-cohort-data-builder` from `main`, and push `main` and the branch to `origin` (`CLS-Data/cohort-data-builder`)
- [x] T003 [P] Write `.github/pull_request_template.md` with sections: **Summary** (what changed and why, 1–3 lines); **Tasks** (IDs covered, e.g. T032–T037); **How to review** (required by the constitution), pre-filled with HTML-comment prompts and this skeleton: "**Time needed:** ~N min", then numbered steps — 1. check out (`git fetch && git switch <branch>`), 2. run the relevant tests with the exact command and expected result, 3. try it (exact serve command, URL, what to click, what you should see), 4. read closely (the files that carry the logic) vs. skim (wiring, fixtures), 5. test-first check (each `test(…)` commit precedes its `feat(…)`/`fix(…)` commit) — then "**Out of scope:**"; and a **Checklist**: failing tests committed before implementation, JSDoc / docstrings on every new export, README / `docs/data-format.md` updated if behaviour or data format changed, CI green, no study data added
- [x] T004 [P] Write `.github/dependabot.yml`: weekly updates for `github-actions` (root), `uv` (root) and `npm` (root), each grouped into one pull request per ecosystem, targeting `001-cohort-data-builder` until the feature merges, then `main`
- [x] T005 [P] Write `CONTRIBUTING.md`: the branching model, the pull-request description rules (every PR fills in *How to review* with concrete numbered steps; placeholder text fails the `pr-description` check), Conventional Commit types (`test`, `feat`, `fix`, `refactor`, `docs`, `ci`, `chore`) with the test-commit-first rule, how to open a pull request, the required checks, squash merging, and releases (`vX.Y.Z` tags with GitHub Releases; `v0.1.0` at the P1 MVP)
- [ ] T006 Configure branch protection on `main` (manual, needs a `CLS-Data` organisation admin): require a pull request with at least 1 approval, dismiss stale approvals, require the `ci` and `pr-description` status checks to pass and the branch to be up to date, require linear history (squash merge only), block force pushes and deletion; apply the same rules except the approval count to `001-cohort-data-builder`. Record the settings in `CONTRIBUTING.md`
- [x] T007 Create `CLAUDE.md` at the repository root (read by Claude Code every session): one-paragraph project summary linking `specs/001-cohort-data-builder/spec.md` and `plan.md` and the constitution; setup, test and lint commands; the Phase 0 protocol (branch names, Conventional Commits, failing-test commit before implementation commit, one PR per phase or story); and the rule: "When opening a pull request, always fill in the template's *How to review* section with concrete numbered steps a reviewer can follow without other context: exact checkout and test commands with expected results, what to open or click and what should happen, which files need close reading and which are routine, and what is out of scope. Never leave template prompts or placeholders. Keep it under about 15 lines."

**Checkpoint**: Branch exists on GitHub; protection on (`ci` and `pr-description` required); the first pull request (Phase 1)
cannot merge without green `ci`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Toolchain, layout, initial supplied data and CI.

- [x] T008 Create the directory layout from plan.md: `site/js/core/`, `site/js/ui/`, `site/templates/`, `site/data/`, `tests/js/`, `tests/fixtures/`, `tests/python/data/`, `tests/python/generated/`, `tests/python/e2e/`, `docs/`, `.github/workflows/`
- [x] T009 Create `pyproject.toml` as a non-packaged uv project (`[tool.uv] package = false`, `requires-python = ">=3.12"`) with a `dev` dependency group pinned to exact versions: `pytest`, `pytest-playwright`, `axe-playwright-python`, `ruff`, `pandas`, `pyreadstat`; add `[tool.ruff]` (line-length 100, target py312, `extend-exclude = ["PoC", "site/templates", ".venv", "node_modules"]`), `[tool.ruff.lint]` select `["E","F","W","I","B","UP","SIM","D"]` with `pydocstyle.convention = "google"` and per-file-ignores `"tests/**/test_*.py" = ["D"]`, `"tests/**/conftest.py" = ["D"]`; add `[tool.pytest.ini_options]` with `testpaths = ["tests/python"]` and markers `e2e`, `needs_r`; write `.python-version` containing `3.12`; run `uv lock` and commit `uv.lock`
- [x] T010 [P] Create `package.json` (private, no runtime deps) with `@biomejs/biome` as the only devDependency at an exact version and scripts `"lint": "biome ci site/js tests/js"`, `"test": "node --test tests/js/"`; create `biome.json` (formatter indent 2 spaces, lineWidth 100; linter recommended rules; files include `site/js/**` and `tests/js/**`); run `npm install` to create `package-lock.json`
- [x] T011 [P] Extend the root `.gitignore` (from T001) with `.venv/`, `node_modules/`, `__pycache__/`, `.pytest_cache/`, `.ruff_cache/`, `test-results/`, `.DS_Store`
- [x] T012 [P] Copy the initial supplied data from `PoC/site/data/` to `site/data/`: `datasets.json`, `bcs70/` and `next_steps/` (each with `manifest.json`, `index.json`, `dict/*.json`); do NOT copy `PoC/site/data/templates.json`
- [x] T013 [P] Copy the download templates unchanged from `PoC/templates/` to `site/templates/` (`r/load_data.R`, `r/merge.R`, `python/load_data.py`, `python/merge.py`, `python/requirements.txt`, `README.md`, `data-README.md`, `project.Rproj`); later tasks change them only under failing tests
- [x] T014 [P] Create `.github/workflows/ci.yml` (on push and pull_request, plus `workflow_call` so Pages can reuse it), one job on ubuntu-latest: checkout; `astral-sh/setup-uv`; `actions/setup-node` (node 20) + `npm ci`; `r-lib/actions/setup-r` + `Rscript -e 'install.packages("haven", repos="https://cloud.r-project.org")'`; `uv sync --locked`; `uv run playwright install --with-deps chromium`; then in order: `uv run pytest tests/python/data`, `uv run ruff check .`, `uv run ruff format --check .`, `npm run lint`, `npm test`, `uv run pytest --ignore=tests/python/data` with env `CDB_REQUIRE_R=1` (fail rather than skip R tests). Name the job `ci` (the required status check in T006). So CI is green before any feature tests exist, add `tests/python/test_layout.py` (asserts the plan's top-level directories exist) and `tests/js/layout.test.mjs` (asserts `site/js/core` exists) in the same commit. Pin every action to a full commit SHA with the version in a trailing comment
- [x] T015 [P] Create `.github/workflows/pages.yml` (on push to `main` and `workflow_dispatch`): job `checks` uses `./.github/workflows/ci.yml`; job `deploy` `needs: checks`, permissions `pages: write`, `id-token: write`, environment `github-pages`, concurrency group `pages` with `cancel-in-progress: false`; steps checkout, `actions/configure-pages`, `actions/upload-pages-artifact` with `path: site`, `actions/deploy-pages`. Pin actions to SHAs
- [x] T016 Write failing tests `tests/python/test_check_pr_body.py` for `.github/scripts/check_pr_body.py` (load it with `importlib` from its path) `problems(body: str | None) -> list[str]`: no `## How to review` heading → one problem; the section (which ends at the next `## ` heading) is empty, holds only HTML comments, or still contains the template's skeleton placeholders (e.g. `~N min`, `<branch>`) → one problem; the section has no numbered step (`1.`) → one problem; a filled-in section with at least one numbered step → no problems; `None` is treated as an empty body
- [x] T017 Implement `.github/scripts/check_pr_body.py` (standard library only, Google-style docstrings; `main()` reads the body from env `PR_BODY`, prints each problem and exits 1, else prints "How to review: OK") to pass T016, and add `.github/workflows/pr-description.yml`: on `pull_request` types `opened`, `edited`, `synchronize`, `reopened`, job `pr-description` running `python3 .github/scripts/check_pr_body.py` with `PR_BODY: ${{ github.event.pull_request.body }}` passed through `env` (never interpolated into the shell script, to avoid injection); pin `actions/checkout` to a SHA

**Checkpoint**: `uv sync`, `npm ci`, `uv run ruff check .` and `npm run lint` run (no code yet).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Test fixtures, test harnesses, data loading, storage and the page shell that
every story needs.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

### Fixtures and harnesses

- [x] T018 Create the fixture cohort `tests/fixtures/data/` in the supplied format of `contracts/site-data.md`: `datasets.json` listing key `mini`; `mini/manifest.json` with identifier `PID`, `wave.list` `[{key:"5y",label:"Age 5"},{key:"10y",label:"Age 10"},{key:"xwave",label:"Cross-sweep files"}]`, levels `["NOMINAL","ORDINAL","SCALE"]`, files `mini_age5` (5y, hasId true), `mini_age10` (10y, hasId true), `mini_grid` (10y, hasId true, several rows per person in tests), `mini_noid` (xwave, hasId false), and a topic scheme with 2 domains (`health`: topics `smoking`, `alcohol`; `housing`: topic `tenure`); `mini/index.json` and `mini/dict/*.json` with about 15 variables including: the identifier in every file except `mini_noid` (spelled `pid` in `mini_age10` to exercise case-insensitive matching); `sex` in both `mini_age5` and `mini_age10` (column clash); a variable with `na.values`, one with an open-ended `na.ranges` entry `[null,-1]`, one with `na.kept` `[[-1,"Dislike"]]`, one with `na.lossy`; a label containing `"`, `\` and a newline; one variable with no label; one SCALE variable with no value labels; one variable with level `-1`; two variables with the identical label (≥10 chars) at different sweeps; topic tags with confidences 0.3, 0.6 and 0.95
- [x] T019 [P] Create `tests/js/helpers.mjs`: `readFixture(path)` (JSON from `tests/fixtures/data/`), `fixtureFetch` (a `fetch`-compatible function serving files from a given root, returning `{ok:false,status:404}` for missing files), and `fakeStorage()` (an in-memory `localStorage` stand-in, plus a variant whose methods throw, for private-browsing cases); JSDoc every export
- [x] T020 [P] Create `tests/python/conftest.py`: fixture `serve` returning a function `serve(root, prefix="")` that starts `http.server.ThreadingHTTPServer` on a free port in a background thread, serving `root` under URL prefix `prefix` (so the site can be served from `/cohort-data-builder/`), and yields the base URL; fixture `site_with_data` returning a function `site_with_data(data_dir)` that copies `site/` to `tmp_path` and replaces its `data/` with `data_dir`; fixture `mini_site` = `site_with_data(tests/fixtures/data)`; register the `e2e` marker on everything under `tests/python/e2e/`
- [x] T021 [P] Create `tests/python/generated/conftest.py`: `has_r()` (Rscript on PATH and `library(haven)` loads), and a `needs_r` marker that skips without R unless env `CDB_REQUIRE_R=1`, in which case missing R fails the test

### Core: text, storage, data loading (tests first)

- [x] T022 [P] Write failing tests `tests/js/text.test.mjs` for `site/js/core/text.js`: `esc()` escapes `& < > " '` and treats null/undefined as `""`; `highlight(text, term)` wraps the first case-insensitive match in `<mark>`, escapes everything else, and returns escaped text when the term is empty or absent; `capitalise()`; `levelName(levels, i)` returns `"Unrecorded"` for `-1` and sentence-cases `NOMINAL` → `Nominal`
- [x] T023 [P] Write failing tests `tests/js/storage.test.mjs` for `site/js/core/storage.js`: `storeKey(name, cohortKey)` returns `cohort-data-builder:<cohortKey>:<name>` and uses `_site` for site-wide settings; `read(storage, key, fallback)` returns `fallback` on a missing key, invalid JSON or a throwing storage; `write(storage, key, value)` returns false and does not throw when storage throws
- [x] T024 [P] Write failing tests `tests/js/data.test.mjs` for `site/js/core/data.js` using `fixtureFetch`: `loadCatalogue(fetch)` returns `datasets` from `data/datasets.json`; `loadCohort(fetch, key)` returns `{manifest, vars}` from `data/<key>/manifest.json` and `data/<key>/index.json`; `loadDict(fetch, key, file, cache)` fetches `data/<key>/dict/<file>.json` once and serves later calls from `cache`; every failure throws an Error whose message contains the URL and HTTP status; all URLs are relative (never start with `/`)
- [x] T025 [P] Implement `site/js/core/text.js` to pass T022 (port `esc`, `highlight`, `capitalise`, `levelName` from `PoC/site/js/state.js`)
- [x] T026 [P] Implement `site/js/core/storage.js` to pass T023
- [x] T027 [P] Implement `site/js/core/data.js` to pass T024 (fetch injected as a parameter so it runs under Node)

### Page shell (tests first)

- [x] T028 Write failing browser tests `tests/python/e2e/test_shell.py` against `mini_site` and the real `site/`: the page loads with title `Cohort Data Builder`, a beta notice with a link to report problems (FR-036), a "Skip to content" link, a cohort picker listing every cohort in `datasets.json`; `#next_steps` in the URL opens Next Steps and changing the picker updates the hash; the last cohort chosen is reopened on a later visit when the URL has no hash; a site whose `data/datasets.json` is missing shows a readable "Could not load the site data" message instead of a blank page; the theme button switches light/dark and the choice survives reload; the cohort's full name and a footer with variable count, file count and sweep count are shown
- [x] T029 Create `site/index.html` (lang `en-GB`, viewport meta, relative `styles.css` and `js/ui/boot.js` module) with the masthead (name, beta pill, cohort `<select>`, Variables/Selection view tabs with a selected-count tally, theme button), beta bar, `<main id="main">` containing the two view sections with the element ids used by `PoC/site/index.html`, and the footer; copy `PoC/site/styles.css` to `site/styles.css` and keep light/dark via `prefers-color-scheme` and `[data-theme]`
- [x] T030 Implement `site/js/ui/state.js` (the single mutable UI state object, fields as in `PoC/site/js/state.js` minus helpers now in core) and `site/js/ui/views.js` (view switching with `aria-current`, `onShow(view, fn)` callbacks)
- [x] T031 Implement `site/js/ui/boot.js` to pass T028: load the catalogue via `core/data.js`, fill the picker, choose the cohort from hash → stored last cohort → first, open it (disable the picker while loading), update `document.title`, subtitle and footer, react to `hashchange`, wire the theme button with `core/storage.js`; on any load failure render the failure message

**Checkpoint**: `npm test` passes; `uv run pytest tests/python/e2e/test_shell.py` passes.

---

## Phase 3: User Story 1 - Find variables in a cohort (Priority: P1) 🎯 MVP

**Goal**: Search a cohort by name or label, filter by sweep, file and level, and open any
variable's details in place.

**Independent Test**: Open BCS70, search "smoke", filter to one sweep, open a result and see
its value labels and file.

### Tests for User Story 1 ⚠️ write first, see them fail

- [x] T032 [P] [US1] Write failing tests `tests/js/search.test.mjs` for `site/js/core/search.js` `filterVariables(vars, manifest, filters)` on the fixture: matches any substring of name or label ignoring case; `filters` = `{query, wave, file, level}` each `null` for "any", `level` may be `-1` (unrecorded); returns `{matches, perWave, perLevel}` where `perWave` has one count per sweep including zeros and is computed after all filters, and `perLevel` ignores the level filter but applies the others; a row with no level counts as `-1`; empty result returns empty `matches`
- [x] T033 [P] [US1] Add failing tests to `tests/js/search.test.mjs` for `page(matches, shown)` (first 200, then +200 per "show more", reporting how many are left) and for `buildLabelIndex(vars)` / `sameLabel(index, row)`: labels normalised by lower-casing, collapsing whitespace and trimming trailing `. : ; ?`; labels shorter than 10 characters are not indexed; a group of more than 40 returns nothing; returns the other rows sorted by sweep then name, at most 10, plus the count not shown
- [x] T034 [P] [US1] Add a failing performance test to `tests/js/search.test.mjs`: 35,000 synthetic rows, query `"smok"` plus a sweep filter completes in under 100 ms (budget well inside SC-002's 0.5 s)
- [x] T035 [P] [US1] Write failing tests `tests/js/details.test.mjs` for `site/js/core/details.js` `describeVariable(entry, file, identifier)` on fixture entries: value labels split into `answers` and `missing`, where missing means the code is in `na.values` or inside an `na.ranges` range (null = open end); answers keep dictionary order and `answers` are truncated to 8 with `more` = the rest; `kept` and `lossy` are passed through as supplied and a missing code also in `lossy` is flagged; the identifier returns `{isIdentifier:true}`; a SCALE variable with no labels returns `note: "continuous"`; facts list file name and description, study number, position, measurement level and type, omitting absent ones
- [x] T036 [US1] Write failing browser tests `tests/python/e2e/test_us1_search.py` covering spec US1 acceptance scenarios 1–7 on `mini_site` (and a smoke run on real BCS70): cohort name, description, counts and per-sweep bars in time order; typing filters with highlighted matches (debounced); clicking a sweep bar filters and clicking again clears; the level dropdown shows counts per option and disables zero-count options; file filter via a variable's "all in this file"; active filters shown as removable chips and one "Clear"; details open in place via the ▸ button with answers before missing codes, "+ N more" expands, "Kept as answers" and ⚠ lossy shown, "Same label" links jump to the other variable; no-match message with "Clear the filters"; an empty sweep is drawn as empty; result count text; "Show 200 more" paging

### Implementation for User Story 1

- [x] T037 [P] [US1] Implement `site/js/core/search.js` to pass T032–T034 (port the filter pass from `runSearch` and the label index from `PoC/site/js/search.js`; no DOM, no global state: everything passed in)
- [x] T038 [P] [US1] Implement `site/js/core/details.js` to pass T035 (port `valuesHtml`/`moreHtml` logic from `PoC/site/js/search.js` as data, not HTML)
- [x] T039 [US1] Implement `site/js/ui/overview.js` per-sweep chart (port `PoC/site/js/spine.js`): one bar per sweep with key, count and `aria-pressed`, empty sweeps marked, title "All variables"/"Matching variables", click toggles the sweep filter
- [x] T040 [US1] Implement `site/js/ui/results.js` (port the list parts of `PoC/site/js/search.js`): search input with ~120 ms debounce; result rows (name, label, sweep, file) with highlight; level `<select>` with counts; filter chips and Clear; result count; paging; ▸ details rendered from `core/details.js`, loading the file dictionary via `core/data.js` on first open; "all in this file"; "Same label" jump (sets the query to the label, clears other filters, opens and scrolls to the row); empty-state message; keyboard focus kept on the toggled control after re-render
- [x] T041 [US1] Wire search into `site/js/ui/boot.js`: reset filters and open rows when the cohort changes, build the label index, render the about line, run the first search; make T036 pass

**Checkpoint**: US1 independently usable (search, filter, details) and all US1 tests green.

---

## Phase 4: User Story 2 - Build a selection (Priority: P1)

**Goal**: Add and remove variables (single, range, all) with the selection visible beside
the results and remembered per cohort.

**Independent Test**: Add five variables from two files, reload, see the same five selected.

### Tests for User Story 2 ⚠️ write first, see them fail

- [ ] T042 [P] [US2] Write failing tests `tests/js/selection.test.mjs` for `site/js/core/selection.js` (functions take and return plain data; a selection is an array of `{name, label, file, wave, column}`): `canSelect(row, file, identifier)` refuses the identifier (ignoring case: "already in every download") and files with `hasId:false` (reason names the file and identifier); `add` returns the new selection or the refusal reason and ignores duplicates by `file:name`; `remove`, `toggle`, `addMany` and `removeMany` return the change count; `rangeBetween(matches, anchorKey, toKey)` returns the selectable rows between the two inclusive and the caller applies add or remove according to the clicked row's state; `selectAllState(matches)` returns `hidden` when there are 0 or more than 500 selectable rows, else `add` or `remove`
- [ ] T043 [P] [US2] Add failing tests to `tests/js/selection.test.mjs` for default output columns: `sanitiseColumn(s)` replaces anything outside `[A-Za-z0-9_.]` with `_` and strips leading non-letters; the default is the sanitised name; if that is taken (case-insensitive, and the identifier counts as taken) use `<name>_<sweep>`, then `<name>_<sweep>_2`, `_3`…; the fixture's two `sex` variables get `sex` and `sex_10y`
- [ ] T044 [P] [US2] Add failing tests to `tests/js/selection.test.mjs` for `restore(saved, vars, manifest)`: drops entries whose `file:name` no longer exists, drops the identifier, keeps a saved column only if it matches `^[A-Za-z][A-Za-z0-9_.]*$` and is not already claimed (ignoring case), otherwise assigns a default; tolerates non-array or garbage input by returning `[]`
- [ ] T045 [US2] Write failing browser tests `tests/python/e2e/test_us2_selection.py` covering spec US2 acceptance scenarios 1–7 on `mini_site`: clicking a row toggles ＋/✓ and updates the selected count and tab tally; Shift-click adds the range (or removes it when the clicked row was selected) and the change is announced in a `role="status"` region; "Select all N" appears only for 1–500 selectable results and flips to "Remove all N"; the identifier row shows ✓ and is not toggleable; `mini_noid` rows are disabled with the reason as the title; reload restores the selection for that cohort only; the selection panel groups by sweep or file, filters by text, shows 200 per group with "Show all", ✕ removes and moves focus to the next ✕, and Clear needs a second click within 4 s; with storage throwing (private browsing) the site still works

### Implementation for User Story 2

- [ ] T046 [US2] Implement `site/js/core/selection.js` to pass T042–T044 (port `put`, `addMany`, `removeMany`, `defaultColumn`, `taken`, `restore` from `PoC/site/js/basket.js`; O(1) membership via a Set keyed `file:name`)
- [ ] T047 [US2] Add selection to `site/js/ui/results.js`: row click toggles, Shift-click range from the last-clicked anchor (anchor reset when the cohort changes), Cmd/Ctrl-click behaves like click, "Select all/Remove all", a status message that clears after 5 s, ＋/✓ marks, disabled rows with reasons; drag a row onto the Selection tab to add it
- [ ] T048 [US2] Implement `site/js/ui/panel.js` (port `PoC/site/js/panel.js`): count, group by sweep/file (choice saved in options), text filter, collapsible groups showing 200 rows until "Show all", ✕ remove with focus handling, two-click Clear, "Review & download →" switching to the Selection view, a panel toggle for mid-width screens with its open state saved
- [ ] T049 [US2] Persist and restore the selection per cohort under `storeKey("selection", key)` and UI options under `storeKey("options","_site")` via `core/storage.js` in `site/js/ui/boot.js`; restore after the cohort loads; make T045 pass

**Checkpoint**: US1 + US2 work together; selection survives reload.

---

## Phase 5: User Story 3 - Download a ready-to-run merge project (Priority: P1)

**Goal**: Review and rename output columns, choose languages, output format and missing-code
handling, and download a zip whose R and Python merge the researcher's data identically.

**Independent Test**: Select variables from a one-row-per-person file and a grid file,
download, run R and Python on fabricated data in every input format, get identical correct
output.

### Tests for User Story 3 ⚠️ write first, see them fail

- [ ] T050 [P] [US3] Write failing tests `tests/js/columns.test.mjs` for `site/js/core/columns.js` `problems(selection, identifier, format)` returning a Map `file:name → message`: invalid unless `^[A-Za-z][A-Za-z0-9_.]*$` ("Must start with a letter and use only letters, digits, _ or ."); two columns equal ignoring case are both flagged ("Two columns would both be called X."); a column equal to the identifier ignoring case is flagged ("…the identifier's name…"); Stata (`dta`): must match `^[A-Za-z_][A-Za-z0-9_]*$` (message suggests the `_` version) and be at most 32 characters; SPSS (`sav`): at most 64 characters and must not end with `.`; CSV adds no rule. Also `fixDots(selection, identifier)` replaces every non-`[A-Za-z0-9_]` with `_` and de-duplicates with `_2`, `_3`…
- [ ] T051 [P] [US3] Write failing tests `tests/js/codegen.test.mjs` for `site/js/core/codegen.js` `buildProject(selection, manifest, dicts, templates, options, today)` (no fetch inside: dictionaries and templates passed in): project name `<key>-merge-<YYYY-MM-DD>`; file list matches `contracts/download-project.md` for R only, Python only and both; every string from the dictionary inside a quoted literal escapes `\` and `"` and turns newlines into spaces (fixture label with `"`, `\`, newline); `SELECTION` grouped by file with `column = "variable"`; `MISSING_CODES` built **only** from supplied `na.values` and `na.ranges` (`NA`/`None` for open ends), never from `kept` or `lossy`, and omitting columns with neither; `MISSING_TO_NA` is `TRUE`/`FALSE` (R) and `True`/`False` (Python) per option; `OUTPUT_FORMAT` is the option; `LABELS` lists the identifier first; `VALUE_LABELS` only for columns whose codes are all whole numbers, first label per code; README fills every placeholder and its missing-codes note matches the option; no `{{` remains in any output file
- [ ] T052 [P] [US3] Add failing tests to `tests/js/codegen.test.mjs` for `codebook()`: header exactly `column,variable,file,wave,label,missing_codes,negative_kept,value_labels,topics`; first row the identifier; `negative_kept` as `code=label` joined by `; `; `value_labels` likewise; `topics` as `Label (0.90)` joined by `; `; RFC 4180 quoting of commas, quotes and newlines
- [ ] T053 [P] [US3] Add a failing test to `tests/js/codegen.test.mjs` that every template in `site/templates/` contains each required placeholder listed in `contracts/download-project.md` (read from disk)
- [ ] T054 [P] [US3] Write failing tests `tests/js/zip.test.mjs` for `site/js/core/zip.js` `zip(entries)` → `Uint8Array`: a store-only zip whose local headers, central directory and end record are valid; CRC-32 of a known string is correct; UTF-8 file names flagged; nested paths preserved; round-trip by parsing the central directory in the test
- [ ] T055 [US3] Create `tests/js/generate_bundle.mjs`, a Node driver used by Python tests: `node tests/js/generate_bundle.mjs <data_dir> <cohort> <out_dir> <missingToNa> <csv|dta|sav> <langs> <file:variable[:column]>...`; it reads the supplied data and `site/templates/` from disk and writes the project files from `core/codegen.js` to `out_dir`
- [ ] T056 [US3] Write failing tests `tests/python/generated/test_generated_scripts.py` (marked `needs_r` where R is used) using `generate_bundle.mjs` on the fixture cohort: fabricate data for `mini_age5`, `mini_age10` and `mini_grid` with pandas and pyreadstat (fixed seed) in each input format `.tab`, `.csv`, `.dta`, `.sav`, placed in nested subfolders of `data/`; the selection MUST include the fixture variable whose label contains `"`, `\` and a newline (FR-028); run `Rscript R/merge.R` and `python python/merge.py` from the project root; assert: `output/merged.<ext>` has the identifier first then columns in selection order, one row per person, a full outer join (people in only one file kept with empty cells); `mini_grid` written to `output/mini_grid_long.<ext>` and not joined; R and Python outputs are identical (values and column order) for every input/output format combination; identifier matched though spelled `pid` in one file, and padded identifier values are trimmed before joining
- [ ] T057 [US3] Add failing tests to `tests/python/generated/test_generated_scripts.py` for the edge behaviour: a missing data file makes both scripts exit non-zero before reading anything and list every missing file; a selected column absent from the data produces a warning and is skipped; with `MISSING_TO_NA` on exactly the supplied `na.values`/`na.ranges` become NA, `kept` codes (e.g. `-1 "Dislike"`) are untouched and non-negative values are untouched (SC-005); with it off every value is as deposited; Stata and SPSS outputs carry the variable labels and whole-number value labels (read back with pyreadstat); editing `OUTPUT_FORMAT`/`MISSING_TO_NA`/`DATA_DIR` at the top of the script changes behaviour without regenerating (FR-026); `uv run ruff check` passes on every rendered `python/*.py`
- [ ] T058 [US3] Write failing browser tests `tests/python/e2e/test_us3_download.py` covering spec US3 acceptance scenarios 1–4 on `mini_site`: the Selection view lists the identifier row first then each column with label, source variable and file, plus "Data files it needs" with descriptions and a UK Data Service link; selecting both `sex` variables yields `sex` and `sex_10y`; renaming on blur/Enter; an invalid, duplicate or identifier-clashing name shows its reason, sets `aria-invalid`, and disables Download; choosing Stata with a dotted name offers "Replace every . with _"; options (languages, output format, missing to NA) persist across reload and Download is disabled with no language; Download produces `mini-merge-<date>.zip` whose entries match `contracts/download-project.md`, and a status line reports its size

### Implementation for User Story 3

- [ ] T059 [P] [US3] Implement `site/js/core/columns.js` to pass T050 (port `NAME_OK`, `FORMAT_RULES`, `problems` and the fix-dots logic from `PoC/site/js/basket.js`)
- [ ] T060 [P] [US3] Implement `site/js/core/zip.js` to pass T054 (port `PoC/site/js/zip.js`)
- [ ] T061 [US3] Implement `site/js/core/codegen.js` to pass T051–T053 (port `PoC/site/js/codegen.js`, with dictionaries, templates and today's date injected instead of fetched)
- [ ] T062 [US3] Make T056–T057 pass by correcting `site/templates/r/load_data.R`, `site/templates/r/merge.R`, `site/templates/python/load_data.py` and `site/templates/python/merge.py` only where a test fails; add docstrings and comments to the Python templates so the rendered project passes `ruff check`
- [ ] T063 [US3] Implement `site/js/ui/review.js`, the Selection view (port `renderList`/`renderDetail`/`download` from `PoC/site/js/basket.js`): the list pane with ✕ remove and drop target, a resizable divider (pointer + arrow keys, width saved), the columns list with rename inputs and problems, data files needed (clicking one filters the Variables view to that file), the options (languages, output format with help text, missing to NA with help text), and Download, which fetches `templates/*` as text on first use (relative URLs), calls `core/codegen.js` and `core/zip.js`, and triggers the browser download; errors shown in the status line; make T058 pass

**Checkpoint**: The P1 MVP is complete: search → select → download, with generated R and
Python proven on fabricated data.

---

## Phase 6: User Story 4 - Browse by topic (Priority: P2)

**Goal**: A topic overview with per-sweep counts, topic filters combined by any/all, and a
confidence threshold.

**Independent Test**: In Next Steps select two topics in "all" mode and see only variables
tagged with both above the threshold.

### Tests for User Story 4 ⚠️ write first, see them fail

- [ ] T064 [P] [US4] Write failing tests `tests/js/topics.test.mjs` for `site/js/core/topics.js`: `flatten(manifest.topics)` gives topics with their domain index; `rowTopics(row, minConf)` returns `[topicIndex, percent]` pairs at or above the threshold, strongest first; `toggle(sel, kind, i, topics)`: selecting a topic replaces its selected domain, and selecting a domain replaces any of its selected topics; `ensure` never deselects; `passes(sel, mode, ts, ds)`: no selection passes everything, `any` needs at least one, `all` needs every item; `tally(rows, …)` gives per-sweep counts per topic and per domain that ignore the sweep and topic filters but respect query, file and level; `shade(count, rowMax, allMax, mode)` returns 0 for 0 and 1–4 otherwise (`row` = linear against the row max, `abs` = `log1p` against the overall max); minConf limited to 30/50/70/90 with default 50
- [ ] T065 [US4] Write failing browser tests `tests/python/e2e/test_us4_topics.py` covering spec US4 acceptance scenarios 1–6 on `mini_site`: the Topics toggle opens domains with per-sweep cells and counts and ▸ to show their topics; clicking a name filters and adds a chip; "any"/"all" appears with two or more items and changes results; changing "Topic tags ≥" changes chips, counts and the filter, and persists; clicking a cell filters to that topic at that sweep and clicking it again releases the sweep; result rows show up to two topic chips and a stripe colour from their strongest domain; details list every topic with its percent, those below the threshold dimmed, and clicking one filters by it; a cohort without `topics` hides all topic UI

### Implementation for User Story 4

- [ ] T066 [US4] Implement `site/js/core/topics.js` to pass T064 (port from `PoC/site/js/topics.js` and `rowTopics` in `PoC/site/js/state.js`) and extend `filterVariables` in `site/js/core/search.js` to accept `{topicSel, topicMode, minConf}` and return the topic tally (add the matching cases to `tests/js/search.test.mjs` first)
- [ ] T067 [US4] Add the topic grid to `site/js/ui/overview.js` (domain rows, expandable topic rows, cells with shade levels and accessible labels, threshold and shade controls shown only when open, saved options) and topic chips, stripe, details topics and the any/all switch to `site/js/ui/results.js`; hide everything when the manifest has no `topics`; make T065 pass

**Checkpoint**: US1–US4 all work independently and together.

---

## Phase 7: User Story 5 - Publish supplied cohort data (Priority: P3)

**Goal**: Supplied data is checked against `contracts/site-data.md` (rules D1–D8) in CI, and a
new cohort appears on the site with no code change.

**Independent Test**: Add a fixture cohort with one deliberate error; the checks report it
with file and location and fail; fix it; the cohort appears on the site.

### Tests for User Story 5 ⚠️ write first, see them fail

- [ ] T068 [P] [US5] Create broken fixture cohorts under `tests/fixtures/broken/`, one folder per rule, each a copy of `tests/fixtures/data/` with exactly one violation: `d1_bad_json` (truncated JSON), `d1_missing_field` (manifest without `identifier`), `d2_count_mismatch` (`datasets.json` count ≠ manifest), `d2_bad_key` (key `Mini`), `d3_unknown_wave` (file `wave` not declared), `d3_duplicate_file`, `d4_index_out_of_range` (file index too large), `d4_odd_topics` (odd-length topic list), `d5_missing_dict` (no `dict/<file>.json`), `d5_unknown_variable` (index row not in its dictionary), `d5_duplicate_variable` (`AGE` and `age` in one file), `d6_bad_values` (value label without `label`), `d6_bad_range` (`[5, 1]`), `d7_unknown_topic`, `d7_confidence` (1.5), `d8_hasid_wrong` (`hasId:true` but no identifier)
- [ ] T069 [US5] Write failing tests `tests/python/data/test_checks.py` for `tests/python/data/checks.py` `check_data(data_dir) -> list[Problem]` (Problem has `path`, `location`, `message`, `__str__` → `<path>[: <location>]: <message>`): the valid fixture and the real `site/data/` give no problems; each broken fixture from T068 gives at least one problem naming the rule's file, and no unrelated ones; several violations are all reported in one run
- [ ] T070 [US5] Write failing test `tests/python/data/test_supplied_data.py` that runs `check_data(Path("site/data"))` and fails listing every problem (one per line) if any exist; this is the CI gate for supplied data (FR-030)
- [ ] T071 [US5] Write a failing browser test in `tests/python/e2e/test_us5_new_cohort.py`: serve `site/` with `data/` containing the real cohorts plus the fixture cohort `mini` added to `datasets.json`; `mini` appears in the picker and is searchable, with no change to any file outside `data/`

### Implementation for User Story 5

- [ ] T072 [US5] Implement `tests/python/data/checks.py` with the standard library only to pass T069–T070, one documented function per rule D1–D8 from `contracts/site-data.md`, collecting every problem rather than stopping at the first; make T071 pass (fix any site code that assumed only the two launch cohorts)
- [ ] T073 [P] [US5] Write `docs/data-format.md` for the data team from `contracts/site-data.md`: every file and field, the meaning of `na` (`values`, `ranges` with null ends, `kept`, `lossy`), which of `na`, `kept`, `lossy` and other fields are optional, and that the site uses it verbatim, topic schemes and tags, the D1–D8 rules and how to run `uv run pytest tests/python/data`, and the steps to add a cohort

**Checkpoint**: All five stories complete; bad data cannot be published.

---

## Phase 8: Polish & Cross-Cutting Concerns

- [ ] T074 [P] Write failing browser test `tests/python/e2e/test_accessibility.py` running axe-core (`axe-playwright-python`) on the Variables view (topics open, a row expanded), the selection panel and the Selection view, in light and dark themes, failing on any `serious` or `critical` violation (SC-009); then fix what it finds in `site/index.html`, `site/styles.css` and `site/js/ui/*.js`
- [ ] T075 [P] Write failing browser test `tests/python/e2e/test_subpath.py` serving `site/` under `/cohort-data-builder/` (fixture `serve(prefix=…)`): the page loads, searches, opens details and downloads a project with no failed requests; a test that no file under `site/` references a URL starting with `/` (other than `//` protocols); and a test that `site/` contains no `.tab`, `.dta`, `.sav` or `.csv` files (FR-003); fix any absolute URL
- [ ] T076 [P] Write failing browser test `tests/python/e2e/test_responsive.py` at 375×812: no horizontal page scroll, the filter bar, results, panel toggle and Selection view are usable; adjust `site/styles.css`
- [ ] T077 [P] Write browser test `tests/python/e2e/test_performance.py` on real BCS70: with Playwright network throttling at about 20 Mbps down / 20 ms latency, the first cohort view is interactive within 3 s (SC-007) and typing a query updates results within 0.5 s (SC-002)
- [ ] T078 [P] Write `README.md`: what the tool does and that it holds no study data; using it; repository layout; setup (`uv sync`, `uv run playwright install chromium`, `npm ci`); running locally (`uv run python -m http.server -d site 8000`); running every check (as in `quickstart.md`); adding supplied data (link `docs/data-format.md`); deploying (Settings → Pages → Source → GitHub Actions)
- [ ] T079 Review every exported function in `site/js/**/*.js` for a complete JSDoc comment and every non-obvious branch for a comment explaining why (Principle II); run `uv run ruff check .`, `uv run ruff format --check .` and `npm run lint` and fix all findings
- [ ] T080 Run every step of `specs/001-cohort-data-builder/quickstart.md` and record any mismatch as a fix in the relevant file
- [ ] T081 Open the pull request from `001-cohort-data-builder` to `main` (template from T003 filled in), confirm `ci` passes on GitHub with no skipped R tests, get the review, squash merge, and confirm `pages.yml` deploys and the published site works under `https://<user>.github.io/<repo>/`
- [ ] T082 Tag the merge commit on `main` `v0.1.0` and publish a GitHub Release summarising the stories delivered (the MVP may instead be released at the end of Phase 5 via an earlier integration-to-`main` pull request, per `CONTRIBUTING.md`)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Version control (Phase 0)**: none; blocks everything (all later work goes through pull requests).
- **Setup (Phase 1)**: depends on Phase 0.
- **Foundational (Phase 2)**: depends on Setup; blocks all stories.
- **US1 (Phase 3)**: depends on Foundational.
- **US2 (Phase 4)**: depends on Foundational; its UI tasks (T047, T049) extend
  `site/js/ui/results.js` and `boot.js` from US1, so do US1 first.
- **US3 (Phase 5)**: core tasks (T050–T057, T059–T062) depend only on Foundational and can
  run in parallel with US1/US2; the review UI (T058, T063) needs US2's selection.
- **US4 (Phase 6)**: depends on US1 (extends `search.js`, `overview.js`, `results.js`).
- **US5 (Phase 7)**: depends only on Foundational (checks are independent of the UI); T071
  needs the shell from Phase 2.
- **Polish (Phase 8)**: after the stories it exercises.

### Within Each Story

Tests first, run and failing → core modules → UI modules → the story's browser tests green.

### Parallel Opportunities

- Setup: T010–T015 in parallel after T008–T009.
- Foundational: T019–T021 together; T022–T024 together, then T025–T027 together.
- US1: T032–T035 together; T037 and T038 together.
- US2: T042–T044 are one file, so sequential; they can run alongside US3 core tests.
- US3: T050–T054 together; T059 and T060 together.
- US5: T068 alongside any story; T073 alongside T072.
- Polish: T074–T078 together.

---

## Parallel Example: User Story 1

```text
Together (tests, all failing):
  T032/T033/T034 tests/js/search.test.mjs   (one author, one file)
  T035           tests/js/details.test.mjs

Then together:
  T037 site/js/core/search.js
  T038 site/js/core/details.js
```

## Parallel Example: User Story 3 core

```text
Together: T050 columns.test.mjs · T051–T053 codegen.test.mjs · T054 zip.test.mjs
Then:     T059 columns.js · T060 zip.js   (parallel) → T061 codegen.js → T055–T057 → T062
```

---

## Implementation Strategy

### MVP First

1. Phase 1 Setup → Phase 2 Foundational.
2. US1 (search) → validate on its own: this is already a useful dictionary browser.
3. US2 + US3 → the full P1 MVP: search, select, download. Validate with quickstart §2–3.
4. Pull request from `001-cohort-data-builder` to `main`, tag `v0.1.0`, deploy (CI and Pages are in place from Setup).

### Incremental Delivery

- Then US4 (topics), then US5 (data checks and data-team docs), then Polish.
- Each story ends at a checkpoint with all of its tests green and CI passing.

### Notes

- Never mark a task done with failing or skipped tests (R tests must not skip in CI).
- Follow the Phase 0 protocol: failing test commit, then implementation commit; one pull request per phase or story.
- `PoC/` is a git-ignored local reference: no new code imports from it, and nothing from it is committed except the copied data (T012) and templates (T013).
