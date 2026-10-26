# Contributing

How changes reach this repository. The rules come from the project constitution
(`.specify/memory/constitution.md`); where this file and the constitution differ, the
constitution wins.

## Branches

- `main` is what GitHub Pages publishes. It only changes through a reviewed pull request.
- Each feature has an integration branch named after its spec folder, e.g.
  `001-cohort-data-builder`.
- Each phase or user story is a short-lived branch off the integration branch, e.g.
  `001-setup`, `001-us1-search`, merged back by pull request when its checkpoint in
  `tasks.md` is green.
- The integration branch is merged into `main` by pull request when the MVP is complete and
  again when the feature is finished.

## Commits

[Conventional Commits](https://www.conventionalcommits.org), with a scope where useful
(`feat(us1): …`):

| Type | Use for |
|---|---|
| `test` | A new or changed test |
| `feat` | New behaviour |
| `fix` | A bug fix |
| `refactor` | A change that keeps behaviour the same |
| `docs` | Documentation and specs only |
| `ci` | Workflows and CI configuration |
| `chore` | Tooling, dependencies, housekeeping |

**Test first, visibly.** Commit each failing test (`test(…)`) before the code that makes it
pass (`feat(…)` / `fix(…)`). Reviewers use this order to confirm the change was
test-driven.

## Pull requests

1. Push your branch and open a pull request into the integration branch (or `main`, for an
   integration-branch merge).
2. Fill in the template. **How to review** is required: numbered steps a reviewer can follow
   without any other context, giving
   - the exact checkout and test commands, with the expected results;
   - what to open or click, and what should happen;
   - which files need close reading and which are routine;
   - what is deliberately out of scope.

   Placeholder text (`~N min`, `<branch>`, …) fails the `pr-description` check.
3. Wait for the required checks, then ask for review.
4. Merge with **squash merge** only.

## Required checks

| Check | What it runs |
|---|---|
| `ci` | Supplied-data checks, ruff, Biome, JavaScript tests, pytest (generated R and Python scripts, browser and accessibility tests) |
| `pr-description` | The pull request has a filled-in How to review section |

## Branch protection

Set by an organisation admin. Until these are on, follow them by hand.

| Setting | `main` | `001-cohort-data-builder` |
|---|---|---|
| Require a pull request before merging | Yes | Yes |
| Required approvals | 1 (dismiss stale approvals) | 0 |
| Required status checks | `ci`, `pr-description` (branch up to date) | `ci`, `pr-description` (branch up to date) |
| Require linear history (squash only) | Yes | Yes |
| Allow force pushes / deletion | No | No |

## Releases

Releases are tagged `vX.Y.Z` on `main` and published as GitHub Releases. `v0.1.0` is the
MVP: search, select and download.

## Dependencies

Dependabot opens one grouped pull request per ecosystem each week (GitHub Actions, uv,
npm). These go through the same checks and review as any other change.
