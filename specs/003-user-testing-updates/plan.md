# Implementation Plan: Updates from user testing

**Branch**: `003-user-testing-updates` | **Date**: 2026-11-13 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/003-user-testing-updates/spec.md`

## Summary

Four changes from user testing, all in the existing static site:

1. **One list on the Selection tab**: remove the left pane; the column list gains a ✕
   remove button per variable.
2. **Download always in view**: the Selection view gets a fixed-height layout with a
   scrolling list and a pinned download area (sticky bar with folded options on small
   screens).
3. **Stata code**: a third code language. New `site/templates/stata/` do-files, filled by
   `codegen.js` like R and Python, producing the same merged data.
4. **Suggest a tag change**: a link in each variable's details that opens a pre-filled
   GitHub issue form (new `.github/ISSUE_TEMPLATE/tag-suggestion.yml`).

Details and alternatives: [research.md](research.md).

## Technical Context

**Language/Version**: JavaScript (ES2022 modules, no build step); HTML/CSS; Python 3.12
for tests; generated code in R, Python 3 and now Stata 16+

**Primary Dependencies**: none added at runtime. Tests: Node test runner, pytest,
Playwright, axe; R with `haven`; Stata (optional, local only)

**Storage**: browser `localStorage` for selection and options (unchanged keys; options gain
`"stata"`)

**Testing**: Node unit tests for `codegen.js`, `columns.js` and the new `feedback.js`;
Playwright e2e for the Selection view and the tag link; generated-script tests running R,
Python and, where installed, Stata on fixture data

**Target Platform**: GitHub Pages; evergreen browsers; desktop and phone

**Project Type**: static web application plus generated R/Python/Stata projects

**Performance Goals**: Selection view stays responsive with several hundred variables
(list renders under 200 ms for 500 rows, as today)

**Constraints**: static only (no backend); no study data on the site or in issues; WCAG
checks pass light and dark; no horizontal scroll at 390px

**Scale/Scope**: 4 cohorts, ~115,000 variables; selections typically 10–200 variables

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Before design | After design |
|---|---|---|
| I. Test-driven | Each story starts with failing tests (Node, e2e, generated) | Pass, with one recorded exception: the Stata run cannot be required in CI (Complexity Tracking) |
| II. Documented code | New `feedback.js` export and changed `codegen.js` get JSDoc; README and download contract updated | Pass: contracts written; README "Stata" section and `docs/` update listed for tasks |
| III. Static Pages | No server; the tag link is a plain GitHub URL | Pass |
| IV. Simplicity | No new dependency or build step | Pass: Stata mirrors existing R/Python structure; layout reuses the Variables view's technique |
| Workflow | Spec → plan → tasks → implement; tests ordered first | Pass |

## Project Structure

### Documentation (this feature)

```text
specs/003-user-testing-updates/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── selection-view.md
│   ├── stata-project.md
│   └── tag-suggestion.md
├── checklists/requirements.md
└── tasks.md             (next: /speckit-tasks)
```

### Source Code (repository root)

```text
site/
├── index.html                   Selection view markup: one list, download area
├── styles.css                   Selection layout, sticky download bar, tag link
├── js/core/
│   ├── codegen.js               + Stata selection/codes/labels; README text for 3 languages
│   ├── columns.js               Stata name rule also when Stata code is chosen
│   └── feedback.js              NEW: REPOSITORY, tagSuggestionUrl()
├── js/ui/
│   ├── review.js                one list with remove; download area; Stata option
│   ├── results.js               "Suggest a tag change" link in details
│   └── selected.js              accept "stata" in stored options
├── templates/
│   ├── README.md                Stata run steps
│   └── stata/                   NEW: load_data.do, merge.do
.github/ISSUE_TEMPLATE/tag-suggestion.yml   NEW
docs/data-format.md or README.md            Stata output documented
tests/
├── js/codegen.test.mjs, columns.test.mjs, feedback.test.mjs (new)
├── python/e2e/test_us2_selection.py, test_us3_download.py, test_us1_search.py
└── python/generated/test_generated_scripts.py, conftest.py (needs_stata)
```

**Structure Decision**: Existing single static-site layout; no new top-level folders.
Each story maps to its own short branch off `003-user-testing-updates`:
`003-us1-one-list`, `003-us2-download-in-view`, `003-us3-stata`, `003-us4-tag-suggestion`.

## Complexity Tracking

| Violation | Why needed | Simpler alternative rejected because |
|---|---|---|
| The Stata output test runs only where Stata is installed, not in CI (Principle I: tests run in CI) | Stata is licensed and cannot be installed on GitHub runners | Text-only tests of the do-file cannot show it produces the same data as R/Python; dropping the run entirely would leave FR-008 unchecked. CI still runs the do-file text tests, and the PR's "How to review" requires a local Stata run. |
