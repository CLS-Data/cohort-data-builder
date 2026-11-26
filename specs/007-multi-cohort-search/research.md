# Research: Search several cohorts at once

Decisions behind [plan.md](plan.md). Each: what was chosen, why, what else was weighed.

## R1. Where each sweep's age comes from

**Decision**: Add an optional `age` to each `manifest.wave.list[]` entry: the cohort
members' typical age in years at that sweep (a number; months as a fraction, 9 months =
0.75), with an optional `ageRange: [min, max]` when a sweep was fielded across ages. When
`age` is absent the site derives it from a sweep key of the form `<n>y` or `<n>m`
(`"14y"` → 14, `"9m"` → 0.75). Otherwise the sweep is "age not known" and is drawn in a
labelled column after the last known age (FR-012b).

**Rationale**: The age axis needs a number per sweep. Sweep keys are already age-shaped
in the fixture (`5y`, `10y`) and the documented examples (`0y`, `14y`), so most sweeps
need nothing new, but keys are labels, not a contract, and some cohorts may key sweeps by
year or by a label such as `34/35`. An explicit field is the contract; key parsing is a
fallback so the site works before every manifest carries `age`.

**Alternatives**: a site-owned lookup table of ages (`js/core/ages.js`): rejected, data
belongs in the supplied data, not code, and would drift when a cohort is updated. Parsing
the sweep label (`"Sweep 1, 2004"`): rejected, labels hold years, not ages.

**Open item for tasks**: the planning session could not read `site/data/` (it is closed to
the assistant by the user's permission settings), so the sweep keys of the four real
cohorts were not checked. The first task inventories them (a person runs one command; see
quickstart.md) and decides per cohort whether `age` must be added.

## R2. The shared age axis: ordinal columns, not a linear scale

**Decision**: The axis is the sorted union of the distinct ages of every chosen cohort's
sweeps. Each distinct age is one column of equal width; every cohort row has a cell in
every column, empty where it has no sweep at that age. Column labels give the age
("11", "9m"). With one cohort the columns are its sweeps, which is today's layout (FR-012a).

**Rationale**: A linear scale crowds early childhood (MCS has sweeps at 9 months, 3, 5 and
7) and leaves long gaps in adulthood; bars would overlap at phone width (spec edge case).
Ordinal columns line the same age up exactly, keep near ages adjacent but separate (NCDS 11
next to BCS70 10), never overlap, and reuse the existing equal-width bar and cell drawing.

**Alternatives**: linear or square-root age scale: overlaps and needs collision handling;
bucketing ages into life stages: hides which sweep is which and makes a click ambiguous.

**Width**: with four cohorts the union is roughly 30 columns. Below the width they need the
chart scrolls sideways inside its own box with the row labels pinned, so the page itself
never scrolls sideways (SC-006).

## R3. Matching topics across cohorts by id

**Decision**: The topic filter holds topic and domain **ids** (`{kind, id}`) instead of
indices into one cohort's flattened scheme. Each cohort maps ids to its own indices when it
is filtered and tallied. A cohort without tags (no `manifest.topics`) is "untagged": while
a topic filter is active it has no matches, its overview row and result heading say "no
topic tags" rather than "no matches", and its topic sub-rows read "no topic tags" (FR-015).

**Rationale**: Indices differ between scheme versions; ids are the scheme's identity (D7
already checks ids). All cohorts are tagged from the same scheme (spec assumption), so ids
line up; a topic missing from one cohort's scheme simply has no cells for it.

**Alternatives**: require identical scheme hashes and refuse to combine otherwise: too
strict, one re-tagged cohort would break the feature.

## R4. One state object, many cohorts

**Decision**: `state` keeps a `cohorts` map of loaded cohorts (`key` → `{manifest, vars,
topics, domains, labelIndex}`) and a `chosen` list of keys in catalogue order. Filters
that apply everywhere (query, level, topic filter, threshold) stay global; the sweep and
file filters become `{cohort, i}` (FR-006, FR-007). Searching runs the existing
`filterVariables` once per chosen cohort and keeps per-cohort results; a new
`searchCohorts` in `core/search.js` does this without DOM so it is unit-tested.

**Rationale**: `filterVariables` is already pure and per-cohort; wrapping it keeps every
existing test meaningful and keeps single-cohort behaviour identical (FR-005).

**Alternatives**: concatenate every cohort into one index with a cohort column: changes the
index-row contract and every function that reads a row.

## R5. Keys that include the cohort

**Decision**: Selection entries gain `cohort` (the cohort key); `keyOf` becomes
`<cohort>:<file>:<name>` and result-row keys `<cohort>:<fileIndex>:<name>` (FR-010).
Storage is unchanged: each cohort's selection is still saved under its own key
(`cohort-data-builder:<key>:selection`) without the `cohort` field, which is added on
restore, so existing saved selections keep working.

**Rationale**: Equal names in different cohorts must be different selections; per-cohort
storage already exists and keeps a cohort's selection valid on its own.

## R6. Restoring selections of cohorts that are not chosen

**Decision**: At start the site reads the saved selection key of every catalogue cohort.
Chosen cohorts load as now. Each unchosen cohort with a non-empty saved selection is loaded
in the background (manifest and index only), its selection validated by the existing
`restore`, and shown in the Selected panel and Selection view under its cohort (FR-017).

**Rationale**: `restore` needs the index to drop variables that no longer exist; showing an
unvalidated selection could download names that are gone. Only people with saved
selections pay the cost.

**Behaviour change**: someone who used BCS70 and NCDS separately before this feature will
see both selections together, and download both, until they remove one. Release notes and
the tutorial say so.

## R7. Loading cohorts

**Decision**: A cohort loads when it is chosen (or has a saved selection, R6), once, and
stays loaded for the session. Loading shows "Loading NCDS…" in that cohort's overview row;
a failure shows the cohort's name, the error and a Retry button in its row, and the other
cohorts keep working (spec edge case).

**Rationale**: SC-003 (under 3 s to add a cohort) is met by today's per-cohort files; one
cohort on first visit (clarification) keeps the first load as today.

## R8. The cohort control

**Decision**: The header's `<select>` becomes a group of toggle buttons, one per catalogue
cohort, each showing its colour mark and short name with `aria-pressed`. The last pressed
button cannot be released (FR-002): it is marked `aria-disabled` with the title "At least
one cohort stays chosen". At phone width the group wraps onto its own header line.

**Rationale**: Four cohorts fit as buttons; one click adds or removes (FR-001); toggle
buttons are the simplest accessible multi-choice with no popup to manage.

**Alternatives**: a multi-select dropdown with checkboxes: two clicks per change and a
popup to make accessible; checkboxes in a fieldset: fine, but take more room than buttons.

## R9. Cohort colours

**Decision**: Six cohort colour tokens in `styles.css` (`--coh-1` … `--coh-6`), each with
light and dark values, chosen so every pair is distinct from each other and from the
topic-domain colours, and passing 3:1 non-text contrast against the background in both
themes. Known cohorts are pinned to a token by key (`[data-cohort="ncds"] { --coh:
var(--coh-1) }`), so adding a cohort never recolours the others; an unknown cohort gets the
token at its catalogue position modulo six (FR-026). The tutorial uses the same stylesheet,
so it gets the same colours (US5.4).

**Marker shape**: a cohort is marked with a vertical bar or a tag carrying its short name
(text always present, FR-027); topic domains keep their small square swatch. Shape and
text, not colour alone, tell them apart (FR-028).

**Alternatives**: colour in `datasets.json`: puts presentation in the supplied data and
would need a light and dark pair per cohort there.

## R10. The download: one zip, a folder per cohort

**Decision**: A new `buildBundle(projects, templates, options, today)` in
`core/codegen.js`. With one cohort it returns `buildProject`'s result unchanged (FR-024).
With several it calls `buildProject` once per cohort and nests each project's files under
`cohorts-merge-<date>/`, beside a new top-level `README.md` filled from a new template
`site/templates/cohorts-README.md`. Each cohort folder is byte-for-byte the single-cohort
project (FR-020, SC-005). Zip name `cohorts-merge-<date>.zip`.

**Rationale**: Reuses the whole single-cohort generator; each folder can be handed to a
colleague and run alone; the comparison test for SC-005 is a direct file comparison.

**Alternatives**: shared scripts looping over cohorts (rejected at specify, Q2).

## R11. Column-name checks per cohort

**Decision**: `problems()` is called once per cohort's part of the selection and the
results are merged by the cohort-qualified key (FR-019). `fixDots` likewise per cohort.

## R12. Results grouped by cohort

**Decision**: The result list is the concatenation of each chosen cohort's matches in
catalogue order, each preceded by a group heading row (colour, name, match count, or "no
matches"). Paging ("show more") runs over the concatenation as now. The per-cohort counts
in the result count are buttons that jump to that cohort's group, drawing more rows if
needed (reusing `jumpTo`).

**Rationale**: Clarification Q2 (grouped); no new paging logic.

## R13. Testing

**Decision**: A second fictional fixture cohort, `tests/fixtures/data/mini2`, with a
different identifier, sweeps at ages that interleave with `mini`'s, one sweep without a
derivable age, a shared variable name with `mini`, and a version-2 topic scheme sharing one topic id with
`mini`; a third fixture `mini3` has no tags. Node tests cover the
new and changed core functions; Playwright tests cover each user story; generated-script
tests download a two-cohort bundle and compare each folder's output with the single-cohort
download's (SC-005). Every fixture value is invented; no real data is used.
