<!--
Sync Impact Report
==================
Version change: (unversioned template) → 1.0.0
Modified principles:
  - [PRINCIPLE_1_NAME] → I. Test-Driven Development (NON-NEGOTIABLE)
  - [PRINCIPLE_2_NAME] → II. Documented Code
  - [PRINCIPLE_3_NAME] → III. Static GitHub Pages Deployment
  - [PRINCIPLE_4_NAME] → IV. Simplicity
  - [PRINCIPLE_5_NAME] → removed (project defines four principles)
Added sections:
  - Deployment & Technology Constraints (was [SECTION_2_NAME])
  - Development Workflow & Quality Gates (was [SECTION_3_NAME])
Removed sections: none
Templates reviewed (not modified by this command; they read the constitution at runtime):
  - .specify/templates/plan-template.md (Constitution Check gate) ✅ compatible
  - .specify/templates/spec-template.md ✅ compatible
  - .specify/templates/tasks-template.md ⚠ states "Tests are OPTIONAL"; under Principle I
    tests are mandatory, so generated task lists MUST always include test tasks first
Follow-up TODOs: none
-->

# Cohort Data Builder Constitution

## Core Principles

### I. Test-Driven Development (NON-NEGOTIABLE)

All production code MUST be written using the Red-Green-Refactor cycle:

- A failing automated test MUST be written and observed to fail before the code that
  makes it pass is written.
- Only the minimum code needed to make the failing test pass MUST be added; refactoring
  happens only while all tests are green.
- Every bug fix MUST begin with a test that reproduces the bug.
- Tests MUST run automatically in CI on every push and pull request; a failing test
  suite blocks merge and deployment.
- Tests MUST be deterministic: no reliance on network access, wall-clock time, or random
  values without injection or seeding.

**Rationale**: Writing tests first defines expected behaviour before implementation,
prevents untested code paths, and gives a safety net for change in a project with no
server-side runtime to catch errors.

### II. Documented Code

All code MUST be understandable without reverse-engineering it:

- Every exported module, function, class, and type MUST have a doc comment (e.g. JSDoc/
  TSDoc) describing its purpose, parameters, return value, and thrown errors.
- Non-obvious logic MUST carry an inline comment explaining *why*, not *what*.
- The repository `README.md` MUST describe what the application does, how to install
  dependencies, run tests, run locally, and deploy.
- Data formats the application reads or produces MUST be documented alongside the code
  that handles them.
- Documentation MUST be updated in the same change as the code it describes; stale
  documentation is treated as a defect.

**Rationale**: Clear documentation lowers the cost of onboarding, review, and future
change, and makes test intent and data contracts explicit.

### III. Static GitHub Pages Deployment

The application MUST be deployable as a static site on GitHub Pages:

- The build output MUST consist solely of static assets (HTML, CSS, JavaScript, and
  static data files) with no server-side runtime, database, or backend API owned by
  this project.
- All application logic and data processing MUST execute in the browser.
- Asset paths MUST work when served from a repository sub-path
  (`https://<user>.github.io/<repo>/`), not only from the domain root.
- Deployment MUST be automated (e.g. GitHub Actions) and MUST run only after the full
  test suite passes.
- Secrets MUST NOT be embedded in client-side code or the published build.

**Rationale**: GitHub Pages serves only static files; designing for that constraint from
the start avoids features that cannot be deployed.

### IV. Simplicity

- Start with the simplest design that satisfies the current specification (YAGNI).
- Each runtime dependency MUST be justified by a concrete need that cannot be met
  reasonably with the platform or existing dependencies.
- Added complexity (new abstractions, frameworks, build steps) MUST be justified in the
  feature plan's Complexity Tracking section.

**Rationale**: A small, simple codebase is easier to test, document, and keep deployable
as a static site.

## Deployment & Technology Constraints

- Hosting target: GitHub Pages, published from the repository via an automated workflow.
- The production build MUST be reproducible from a clean checkout using documented
  commands.
- The application MUST function in current versions of mainstream evergreen browsers
  (Chrome, Firefox, Safari, Edge).
- Any third-party code loaded at runtime MUST be pinned to an exact version.

## Development Workflow & Quality Gates

- Each change follows the Spec Kit flow (specify → plan → tasks → implement); task lists
  MUST order test tasks before the implementation tasks they cover.
- Before merge, a change MUST pass: all automated tests, linting/formatting checks, and a
  production build.
- Code review MUST confirm tests were written first (tests present for all new
  behaviour), doc comments are present, and README/data-format docs are current.
- Merges to the default branch trigger deployment to GitHub Pages only when every gate
  above passes.

## Governance

- This constitution supersedes all other development practices for this project. Where
  guidance conflicts, the constitution wins.
- Amendments MUST be made through a documented change to this file, including a Sync
  Impact Report, a version bump, and an updated Last Amended date.
- Versioning follows semantic versioning: MAJOR for removing or redefining a principle;
  MINOR for adding a principle or section or materially expanding guidance; PATCH for
  clarifications and wording fixes.
- Every feature plan MUST pass the Constitution Check gate before design and again after
  design; any violation MUST be recorded and justified in Complexity Tracking.
- Compliance is reviewed on every pull request against the principles above.

**Version**: 1.0.0 | **Ratified**: 2026-10-26 | **Last Amended**: 2026-10-26
