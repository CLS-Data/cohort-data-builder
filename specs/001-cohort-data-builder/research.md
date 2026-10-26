# Phase 0 Research: Cohort Data Builder

Decisions behind the Technical Context in [plan.md](plan.md). The PoC in `PoC/` is the
behavioural reference throughout; where a decision departs from it, the reason is given.

Scope note (2026-10-26): data-preparation tooling (dictionary conversion, missing-code
derivation, topic tagging, site-data build) is **out of scope**. Cohort data is supplied
ready to use in the format in [contracts/site-data.md](contracts/site-data.md).

## R1. Python environment

- **Decision**: uv manages Python 3.12 (`.python-version`), the virtual environment and the
  lockfile (`uv.lock`, committed). Python is used only for project tooling: the supplied-
  data checks, the browser and accessibility tests, and the tests that run the generated
  Python scripts. There is no application Python package; `pyproject.toml` declares a
  non-packaged project (`[tool.uv] package = false`) with a `dev` dependency group.
- **Rationale**: User requirement (uv). With data supplied, nothing in the product itself
  needs Python, so no package or CLI is built.
- **Alternatives considered**: A `cdb` CLI package (dropped with the toolkit).

## R2. Python linting and formatting

- **Decision**: Ruff (`ruff check`, `ruff format --check`) over all Python in the
  repository, with rule sets `E, F, W, I, B, UP, SIM, D` (Google docstrings); tests exempt
  from `D`. The Python templates contain `{{placeholders}}` so are excluded from the
  repository-wide run; instead the generated-script tests run `ruff check` on each
  **rendered** Python project.
- **Rationale**: User requirement (ruff). The Python researchers receive is the most
  important Python in the project, so it is linted too.

## R3. Front-end technology

- **Decision**: Plain HTML, CSS and native ES modules, no framework and no bundler, served
  from `site/` as in the PoC. Code is split into **core** modules (pure functions, no DOM:
  data access contracts, search/filter, topics, selection and column naming, code
  generation, zip writing) and **ui** modules (DOM rendering and wiring). Every exported
  function has a JSDoc comment.
- **Rationale**: GitHub Pages with no build step (Principle III), no runtime dependencies
  (Principle IV); the core/ui split makes TDD practical.
- **Alternatives considered**: React/Vue/Svelte + Vite (rejected: build step and
  dependencies the PoC shows are unnecessary); TypeScript (rejected: compile step).

## R4. JavaScript testing

- **Decision**: Node's built-in runner (`node --test tests/js/`) with `node:assert` for all
  core modules. No test dependencies.
- **Rationale**: Zero dependencies; core modules are DOM-free.
- **Alternatives considered**: Vitest/Jest (rejected: dependency tree for no gain); jsdom
  (rejected: UI behaviour is better covered in a real browser, R6).

## R5. JavaScript linting

- **Decision**: Biome (lint + format check), pinned exactly as the only `devDependency` in a
  minimal `package.json`, run as `npx biome ci site tests/js`.
- **Rationale**: Ruff does not lint JavaScript and the quality gate requires lint/format on
  all code. Biome is one self-contained tool.
- **Alternatives considered**: ESLint + Prettier (rejected: two tools, large tree); no JS
  linting (rejected: breaks the quality gate).

## R6. Browser and accessibility tests

- **Decision**: pytest with `pytest-playwright` (Chromium in CI) against the site served by
  a local static server, covering every user story's acceptance scenarios, plus
  `axe-playwright-python` failing on serious/critical violations (SC-009). One test serves
  the site under `/cohort-data-builder/` to prove sub-path safety (R11).
- **Rationale**: Keeps test tooling in the uv toolchain; tests the real page.
- **Alternatives considered**: Playwright for Node (rejected: moves tooling to npm);
  Selenium (rejected: slower, flakier).

## R7. Supplied-data checks

- **Decision**: A pytest module (`tests/python/data/`) implements rules D1–D8 from
  [contracts/site-data.md](contracts/site-data.md) with the standard library, run over every
  cohort in `site/data/` in CI. Its own tests use small fixture cohorts, one per rule
  violation. It runs first in CI so a bad data drop fails fast with a readable list.
- **Rationale**: FR-030 requires checking supplied data without building a toolkit; a test
  suite is the lightest home and is already a CI gate.
- **Alternatives considered**: JSON Schema + validator package (rejected: cross-file rules
  D2–D8 need code anyway); checking in the browser at load time (rejected: errors would
  reach users instead of blocking publishing).

## R8. Missing codes

- **Decision**: The browser and generated scripts consume each variable's supplied `na`
  object verbatim (FR-024). No derivation logic exists in the project.
- **Rationale**: Clarified scope; correctness of the codes is the data team's.
- **Testing consequence**: Generated-script tests assert that exactly the supplied codes are
  converted and that `kept` codes never are (SC-005), using fixtures and the known BCS70
  examples.

## R9. Testing the generated R and Python projects

- **Decision**: pytest generates real downloads by calling the site's core code-generation
  module from Node (a small driver, as in the PoC's `generate_bundle.mjs`), writes fabricated
  data files (`.tab`, `.csv`, `.dta`, `.sav` via pandas/pyreadstat), runs `Rscript` and
  `python`, and asserts outputs are correct and identical (FR-027, SC-003). Skips locally
  without R/haven; CI installs both, so nothing skips there.
- **Rationale**: The only way to prove generated code works is to run it.

## R10. Templates

- **Decision**: Download templates live in `site/templates/` and are fetched as text on the
  first download, replacing the PoC's build-generated `templates.json`. A JS test asserts each
  template contains its required placeholders.
- **Rationale**: Without a build step, the browser reads the templates directly.

## R11. Paths under a repository sub-path

- **Decision**: Every URL is relative (`data/…`, `js/…`, `templates/…`); none starts with
  `/`. Proven by the sub-path browser test.

## R12. CI/CD

- **Decision**: GitHub Actions:
  - `ci.yml` on every push and pull request: `uv sync --locked`; supplied-data checks;
    `ruff check`; `ruff format --check`; `biome ci`; `node --test`; `pytest` (generated-script
    tests with R + haven via `r-lib/actions/setup-r`, Playwright and axe).
  - `pages.yml` on push to `main`: calls the CI workflow (`workflow_call`) and, only if it
    passes, publishes `site/` with `actions/upload-pages-artifact` and
    `actions/deploy-pages`.
  Every action is pinned to a commit SHA with the version in a comment.
- **Rationale**: User requirement (GitHub Actions); Principle III and the quality gates.

## R13. Initial data

- **Decision**: The initial BCS70 and Next Steps data is the supplied-format output the PoC
  produced (`PoC/site/data/`), committed under `site/data/` until the data team supplies
  replacements. It must pass D1–D8.
- **Rationale**: Gives a conforming starting point without any preparation tooling.

## R14. Performance

- **Decision**: Load `index.json` once per cohort (≈2.4 MB raw for BCS70, roughly 400 KB
  gzipped by Pages); load per-file dictionaries on demand; render 200 rows at a time;
  debounce search ~120 ms. A JS test asserts filtering 35,000 synthetic rows stays well
  inside the SC-002 budget.
- **Rationale**: The PoC meets SC-002 and SC-007 this way.
