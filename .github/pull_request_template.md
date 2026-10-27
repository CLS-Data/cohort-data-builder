## Summary

<!-- What changed and why, in 1–3 lines. -->

## Tasks

<!-- Task IDs from specs/001-cohort-data-builder/tasks.md, e.g. T032–T037. -->

## How to review

<!--
Required by the constitution: a reviewer must be able to check this PR by following these
steps alone. Replace every placeholder below with real commands, URLs and expected results,
delete steps that do not apply, and keep it to about 15 lines. The pr-description check
fails while placeholders remain.
-->

**Time needed:** ~N min

1. Check out: `git fetch && git switch <branch>`
2. Run: `<test command>` → <expected result>
3. Try it: `<serve command>`, open <URL>, <what to click> → <what you should see>
4. Read closely: <files that carry the logic>. Skim: <wiring, fixtures>
5. Test-first: each `test(…)` commit comes before the `feat(…)`/`fix(…)` commit it covers

**Out of scope:** <what this PR deliberately does not do>

## Checklist

- [ ] Failing tests committed before the implementation that passes them
- [ ] JSDoc / docstrings on every new export
- [ ] README / `docs/data-format.md` updated if behaviour or the data format changed
- [ ] CI green
- [ ] No study data added
