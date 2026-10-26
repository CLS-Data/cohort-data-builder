# CLAUDE.md

Cohort Data Builder is a static GitHub Pages site for searching the variables of UK
longitudinal cohort studies, building a selection, and downloading a ready-to-run R/Python
project that merges those variables from the researcher's own data. The project rules are
in `.specify/memory/constitution.md`. What to build is in
`specs/001-cohort-data-builder/spec.md`, how in `plan.md`, and the work in `tasks.md`.
`PoC/` is a git-ignored local reference: never import from it or commit it.

## Commands

Available once Phase 1 (Setup) is merged:

```sh
uv sync && uv run playwright install chromium && npm ci   # setup
uv run pytest tests/python/data                           # supplied-data checks
npm test                                                  # JavaScript core tests
uv run pytest                                             # Python, generated-script, browser tests
uv run ruff check . && uv run ruff format --check .       # Python lint/format
npm run lint                                              # JavaScript lint/format (Biome)
uv run python -m http.server -d site 8000                 # run the site locally
```

## How work is done

- Follow `CONTRIBUTING.md`. Work on a short branch per phase or story (e.g. `001-us1-search`)
  off `001-cohort-data-builder`, with one pull request per branch, squash-merged.
- Test-driven: write the failing test, run it and see it fail, then commit it
  (`test(…)`). Then write the code that passes it and commit that (`feat(…)` / `fix(…)`).
  Use Conventional Commits.
- Tick tasks off in `tasks.md` as they are completed.
- Every exported JavaScript function gets a JSDoc comment. Every Python module, class and
  public function gets a Google-style docstring.

## Pull requests

When opening a pull request, always fill in the template's *How to review* section with
concrete numbered steps a reviewer can follow without other context:
- exact checkout and test commands, with expected results;
- what to open or click, and what should happen;
- which files need close reading and which are routine;
- what is out of scope.

Never leave template prompts or placeholders. Keep it under about 15 lines.
