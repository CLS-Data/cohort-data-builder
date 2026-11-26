# Implementation Plan: Search several cohorts at once

**Branch**: `007-multi-cohort-search` | **Date**: 2026-11-26 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/007-multi-cohort-search/spec.md`

## Summary

The builder goes from one cohort at a time to any set of cohorts, all in the existing
static site:

1. **Choose cohorts**: the header drop-down becomes toggle buttons; the choice lives in
   the address (`#ncds+bcs70`) and storage; a cohort loads when first chosen.
2. **Search across them**: the pure per-cohort `filterVariables` runs once per chosen
   cohort; results are grouped by cohort; sweep and file filters belong to one cohort;
   the topic filter matches by topic id.
3. **Stacked overview**: a description line and a sweep row per cohort on a shared
   ordinal age axis; topic rows gain a sub-row per cohort. Sweep ages come from a new
   optional `age` in the manifest, else from age-shaped sweep keys.
4. **Colour**: one colour token per cohort, light and dark, pinned by key, shown with the
   cohort's name; distinct in shape from topic-domain swatches.
5. **Selection and download**: selections are kept per cohort (storage unchanged) and
   shown grouped by cohort; column checks run per cohort; one zip holds a top-level
   README and each cohort's unchanged single-cohort project.
6. **Tutorial**: intro, demo panels and download step updated for two cohorts.

Details and alternatives: [research.md](research.md).

## Technical Context

**Language/Version**: JavaScript (ES2022 modules, no build step); HTML/CSS; Python 3.12
for data checks and tests; generated code in R, Python 3 and Stata 16+ (unchanged)

**Primary Dependencies**: none added. Tests: Node test runner, pytest, Playwright, axe; R,
Python and (optionally) Stata for generated-script tests

**Storage**: browser `localStorage`: new `_site:cohorts`; old `_site:cohort` read once;
per-cohort selection keys unchanged

**Testing**: Node unit tests for new `core/ages.js`, `core/cohorts.js` and changed
`search.js`, `topics.js`, `selection.js`, `columns.js`, `codegen.js`; Playwright e2e per
story; data checks for sweep ages; generated-script comparison of bundle folders with
single-cohort projects. New fictional fixture cohorts `tests/fixtures/data/mini2` and `mini3`

**Target Platform**: GitHub Pages; evergreen browsers; desktop and phone (390px)

**Project Type**: static web application plus generated R/Python/Stata projects

**Performance Goals**: search across all four cohorts (~115,000 variables) redraws in under
1 s (SC-002; one pass today is well under that per cohort); adding a cohort under 3 s
(SC-003)

**Constraints**: static only; no study data anywhere (the assistant cannot read
`site/data/` here: sweep keys of the real cohorts are confirmed by a person, quickstart §0);
WCAG checks pass in both themes and all text sizes; no page-level sideways scroll at 390px

**Scale/Scope**: 4 cohorts now, designed for up to 6 colours; selections typically 10–200
variables across 1–4 cohorts

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Before design | After design |
|---|---|---|
| I. Test-driven | Every story starts with failing Node/e2e/generated tests | Pass: test files named per story (below); fixtures `mini2` and `mini3` are invented data; no licensed-tool skip beyond the existing Stata one |
| II. Documented code | New exports get JSDoc; data-format and download docs change with code | Pass: contracts written; `site-data.md`, `docs/data-format.md`, `download-project.md`, README listed for update |
| III. Static Pages | No server; cohorts load as static files; relative paths | Pass: the address uses the hash; subpath test extended |
| IV. Simplicity | No dependency or build step | Pass: reuses `filterVariables`, `buildProject`, `restore`; ordinal axis reuses bar/cell drawing; toggle buttons, not a custom widget |
| Workflow | spec → plan → tasks → implement; tests first | Pass |

No violations; Complexity Tracking is empty.

## Project Structure

### Documentation (this feature)

```text
specs/007-multi-cohort-search/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── sweep-ages.md             manifest `age` / `ageRange` and checks
│   ├── cohort-choice.md          address, storage, header control, titles
│   ├── variables-view.md         overview, results, panel with several cohorts
│   └── multi-cohort-download.md  zip layout, top README, buildBundle
├── checklists/requirements.md
└── tasks.md                      (next: /speckit-tasks)
```

### Source Code (repository root)

```text
site/
├── index.html                  cohort toggle group replaces <select id="dataset">
├── styles.css                  --coh-1…6 tokens (light/dark), .coh-mark/.coh-tag,
│                               age-axis columns, sub-rows, group headings, chart scroll
├── js/core/
│   ├── ages.js                 NEW: sweepAge(), ageLabel(), ageAxis()
│   ├── cohorts.js              NEW: parseChoice(), formatChoice(), orderChoice(), colourSlot()
│   ├── search.js               searchCohorts() over chosen cohorts; filters by {cohort,i}
│   ├── topics.js               topic filter by id; per-cohort id → index map
│   ├── selection.js            entries carry `cohort`; keyOf with cohort; restore adds it
│   ├── columns.js              + problemsByCohort(bundles, manifests, format, languages)
│   └── codegen.js              buildBundle(); cohorts README filling
├── js/ui/
│   ├── state.js                cohorts map, chosen, results, bundles; filter shapes
│   ├── boot.js                 choose/load/retry cohorts; address and storage; titles
│   ├── overview.js             description lines, sweep rows and topic sub-rows on the axis
│   ├── results.js              grouped list, cohort tags, per-cohort count jump, chips
│   ├── panel.js, review.js     grouped by cohort; per-cohort checks; bundle download
│   └── selected.js             per-cohort save/restore; restore unchosen cohorts
├── templates/cohorts-README.md NEW
└── tutorial/                   index.html, tutorial.js, tutorial.css: two-cohort demo
scripts/checks.py               age checks (D3)
docs/data-format.md, specs/001-…/contracts/site-data.md, download-project.md, README.md
tests/
├── fixtures/data/mini2/, mini3/ NEW fictional cohorts (mini2: v2 topic scheme; mini3:
│                               untagged); datasets.json lists mini, mini2, mini3
├── js/ages.test.mjs, cohorts.test.mjs (NEW); search, topics, selection, codegen tests
├── python/data/test_checks.py  age checks
├── python/e2e/test_007_choose.py, test_007_overview.py, test_007_selection.py,
│   test_007_colour.py, test_007_tutorial.py (NEW); existing tests: selector update
└── python/generated/test_generated_scripts.py   bundle == single-cohort comparison
```

**Structure Decision**: Existing single static-site layout; two new core modules, one new
template, one new fixture cohort. Work goes on short branches off
`007-multi-cohort-search`, one per story: `007-us1-choose-search`, `007-us2-overview`,
`007-us3-selection-download`, `007-us4-colour`, `007-us5-tutorial`, preceded by
`007-foundation` (sweep ages, fixtures `mini2` and `mini3`, multi-cohort state and keys, with the
single-cohort site unchanged).

**Order**: foundation → US1 → US2 and US3 (independent) → US4 → US5. Colour tokens land in
the foundation as plain marks so US1–US3 can show cohorts; US4 completes and audits them.

## Complexity Tracking

None.
