# Data model: Updates from user testing

No new stored data. Two existing structures gain a value, and one new structure (a tag
suggestion) is built in the browser and handed to GitHub.

## Download options (changed)

Held in `state.options`, saved per cohort in browser storage as today.

| Field | Type | Change |
|---|---|---|
| `languages` | array of `"r"`, `"python"`, `"stata"` | **`"stata"` added**. Order of display: R, Python, Stata. At least one needed to download. |
| `outputFormat` | `"csv"` \| `"dta"` \| `"sav"` | unchanged; with Stata only and `sav`, the do-file writes `.dta` (research R3) |
| `missingToNa` | boolean | unchanged; applies to Stata too |

Validation: stored options from before this feature (no `"stata"`) load unchanged. An
unknown language in storage is dropped.

## Selected variable (unchanged)

`{ name, file, wave, label, column }`, keyed by `<file>:<name>`. The Selection tab now shows
each once, in the column list, with rename and remove.

Column-name rules (`problems()`): the existing `dta` rule (Stata names: letters, digits,
`_`, at most 32 characters, not starting with a digit) now also applies whenever
`languages` includes `"stata"`, whatever the output format, because the do-file creates
Stata variables.

## Tag suggestion (new, transient)

Built by `tagSuggestionUrl()` from a variable's dictionary entry and the cohort manifest;
never stored.

| Field | Source | Notes |
|---|---|---|
| cohort | `manifest.name` | e.g. `BCS70` |
| variable | entry `variable` | |
| file | selection/row file | |
| label | entry `label` | truncated to 300 characters |
| current tags | entry `topics` → `Topic label (90%)` joined by `; ` | all tags, including those below the threshold; truncated to fit the URL |
| suggested tags, why | left empty | the user writes these on GitHub |

Issue title: `Tag suggestion: <variable> (<cohort>)`. Label: `tag-suggestion` (applied by
the issue form). See [contracts/tag-suggestion.md](contracts/tag-suggestion.md).
