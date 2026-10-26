# Implementation Plan: Cohort Data Builder

**Branch**: `001-cohort-data-builder` (work is currently on `main`; no feature branch has
been created) | **Date**: 2026-10-26 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/001-cohort-data-builder/spec.md`

## Summary

Rebuild the PoC in `PoC/` as a production, test-driven project with two parts:

1. **A static website** published on GitHub Pages. It loads cohort data supplied by the
   data team (BCS70 and Next Steps at launch) and lets researchers:
   - search and filter variables, including by topic;
   - build a selection;
   - generate a zipped R/Python merge project entirely in the browser.
2. **GitHub Actions** that:
   - check the supplied data against its documented format;
   - run ruff, Biome and all tests, including running the generated R and Python on
     fabricated data;
   - publish the site only when everything passes.

Preparing the data (dictionary conversion, missing-code derivation, topic tagging) is out of
scope: the data arrives ready to use in the format in
[contracts/site-data.md](contracts/site-data.md).

User-facing behaviour follows the PoC. The main engineering change is splitting the
front-end into DOM-free core modules (unit-tested under Node) and thin UI modules (tested
in a real browser), so everything can be written test-first.

## Technical Context

**Language/Version**:
- JavaScript as native ES modules (ES2022), with no transpilation.
- Python 3.12 via uv, for test tooling only.
- R ≥ 4.1 and Python ≥ 3.9 for the *generated* scripts.

**Primary Dependencies**:
- Runtime: none.
- Dev (Python, via uv): `pytest`, `pytest-playwright`, `axe-playwright-python`, `ruff`,
  `pandas`, `pyreadstat`.
- Dev (npm): Biome only, with an exact version pin.

**Storage**:
- Supplied JSON data committed under `site/data/`.
- The browser's `localStorage` for user selections and settings.
- No server-side storage.

**Testing**:
- `node --test` for core JavaScript.
- pytest for the supplied-data checks, the generated-script tests, and the Playwright
  browser and accessibility tests.

**Target Platform**:
- GitHub Pages static hosting.
- Current Chrome, Firefox, Safari and Edge.

**Project Type**: Static web application.

**Performance Goals**:
- Search results update in under 0.5 s on 35,000 variables (SC-002).
- First view usable in under 3 s (SC-007).

**Constraints**:
- No server runtime and no study data anywhere.
- All site URLs are relative, so it works under a repository sub-path.
- No secrets in the build.
- Everything pinned to exact versions.
- No data-preparation tooling in the repository (FR-029).

**Scale/Scope**:
- 2 cohorts, 136 data files and 43,882 variables at launch.
- About 100 topics in 15 areas.
- 2 views (Variables, Selection).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Requirement | How this plan complies | Pre | Post |
|---|---|---|---|---|
| I. TDD | Failing test first, CI blocks on failure, deterministic tests | Core JS has `tests/js`. UI is covered by Playwright in `tests/python/e2e`. Supplied-data rules have one failing fixture per rule. Generated scripts are run, not snapshotted. Fixtures are fabricated with fixed seeds. CI blocks merge and deploy. tasks.md will order test tasks first. | ✅ | ✅ |
| II. Documented code | Doc comments on all exports, README, data formats documented | A JSDoc comment on every JS export, checked in review. Python docstrings are enforced by ruff `D` rules. The README covers use, local run, tests and deploy. The supplied-data format is in `docs/data-format.md`, from contracts/site-data.md. | ✅ | ✅ |
| III. Static GitHub Pages | Static output, client-side logic, sub-path safe, automated deploy after tests, no secrets | `site/` is served as-is and the zip is built in the browser. A sub-path browser test checks relative URLs. `pages.yml` deploys only after CI passes. | ✅ | ✅ |
| IV. Simplicity | Justify dependencies and complexity | There are no runtime dependencies, no build step, no Python package and no CLI. Each dev tool is justified in research.md; Biome is the only npm package (R5). | ✅ | ✅ |
| Constraints | Reproducible, evergreen browsers, pinned third-party code | `uv.lock` and `package-lock.json` are committed. Actions are pinned to commit SHAs. No CDN scripts are used. | ✅ | ✅ |
| Workflow gates | Tests, lint/format and build before merge | `ci.yml` runs the data checks, ruff, Biome, node tests and pytest on every pull request. There is no build step to run. | ✅ | ✅ |

There are no violations, so Complexity Tracking is empty.

## Project Structure

### Documentation (this feature)

```text
specs/001-cohort-data-builder/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── site-data.md          # supplied data format + checks D1–D8
│   └── download-project.md   # what the zip contains and how its scripts behave
├── checklists/requirements.md
└── tasks.md                  # /speckit-tasks
```

### Source Code (repository root)

```text
README.md
CONTRIBUTING.md            # branching, commits, pull requests, releases
.gitignore                 # includes PoC/ (local reference repo, never committed)
docs/data-format.md        # supplied-data format for the data team
pyproject.toml             # uv project (not packaged): dev group, ruff, pytest config
uv.lock
.python-version
package.json               # Biome (dev) only
package-lock.json
biome.json

site/                      # published as-is to GitHub Pages
├── index.html
├── styles.css
├── data/                  # SUPPLIED by the data team; committed, never generated
│   ├── datasets.json
│   └── <key>/{manifest.json,index.json,dict/*.json}
├── templates/             # download templates, fetched as text
│   ├── r/{load_data.R,merge.R}
│   ├── python/{load_data.py,merge.py,requirements.txt}
│   ├── README.md
│   ├── data-README.md
│   └── project.Rproj
└── js/
    ├── core/              # pure, DOM-free, unit-tested under Node
    │   ├── text.js        # esc, highlight, level names
    │   ├── storage.js     # namespaced, failure-safe localStorage access
    │   ├── data.js        # load and index supplied data
    │   ├── search.js      # filtering, counts, same-label index
    │   ├── details.js     # a variable's details as data (answers, missing, kept, lossy)
    │   ├── topics.js      # topic selection, matching, grid tallies
    │   ├── selection.js   # add/remove/range, default columns, restore
    │   ├── columns.js     # sanitising, problems(), format rules
    │   ├── codegen.js     # templates → project files, escaping, codebook
    │   └── zip.js         # store-only zip writer
    └── ui/                # DOM rendering and wiring, browser-tested
        ├── boot.js
        ├── state.js
        ├── views.js
        ├── results.js
        ├── overview.js
        ├── panel.js
        └── review.js

tests/
├── js/                    # node --test: *.test.mjs per core module
├── fixtures/              # tiny fabricated cohorts (valid + one per broken rule)
└── python/
    ├── data/              # D1–D8 checks over site/data/, and their fixture tests
    ├── generated/         # generate a download via Node, run R and Python, compare, ruff
    └── e2e/               # Playwright user-story flows, sub-path, axe

.github/workflows/
├── ci.yml                 # every push and pull request: all gates
└── pages.yml              # main: run ci.yml, then deploy site/ to Pages
.github/pull_request_template.md
.github/dependabot.yml     # github-actions, uv, npm
```

**Structure Decision**: A single static site in `site/`, with the supplied data and the
download templates inside it, and tests split by runner. `PoC/` is a separate git
repository (`macknix/cohort-data-builder`) kept locally as a reference only: it is
git-ignored here and never committed. Its `site/data/` provides the initial supplied data,
copied into `site/data/`.

**Version control**: GitHub flow with an integration branch per feature, as set out in
`CONTRIBUTING.md` (tasks T001–T006): `main` is protected (pull request, one approval,
`ci` status check, squash merge, no force push); feature work happens on
`001-cohort-data-builder`, with one short-lived branch and pull request per phase or story;
Conventional Commits, with each failing test committed (`test:`) before the code that
passes it (`feat:`/`fix:`), so reviewers can confirm test-first from history; Dependabot
keeps pinned actions and locks current; `v0.1.0` is tagged when the P1 MVP is complete.

## Complexity Tracking

No violations to justify.
