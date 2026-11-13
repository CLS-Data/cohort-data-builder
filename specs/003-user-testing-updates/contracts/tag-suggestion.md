# Contract: Tag suggestion link and issue form

## The link (builder)

In each variable's opened details, after the Topics line: a link, text
"Suggest a tag change" (or "Suggest a tag" when the variable has none), opening in a new
tab (`target="_blank" rel="noopener"`).

```text
https://github.com/CLS-Data/cohort-data-builder/issues/new
  ?template=tag-suggestion.yml
  &title=Tag suggestion: <variable> (<cohort>)
  &cohort=<cohort name>
  &variable=<variable>
  &file=<file>
  &label=<label, ≤ 300 characters>
  &current=<Topic (90%); Topic (60%)…, or "none">
```

Every value is URL-encoded. The whole URL is at most 8,000 characters: if longer, `current`
then `label` are cut, ending with `…`. Built by `tagSuggestionUrl(entry, file, manifest)`
in `site/js/core/feedback.js` (pure, no DOM).

## The issue form (`.github/ISSUE_TEMPLATE/tag-suggestion.yml`)

| Field id | Type | Required | Notes |
|---|---|---|---|
| `cohort` | input | yes | pre-filled |
| `variable` | input | yes | pre-filled |
| `file` | input | yes | pre-filled |
| `label` | textarea | no | pre-filled |
| `current` | textarea | no | pre-filled current tags |
| `suggested` | textarea | yes | "Which topics should it have, or not have?" |
| `why` | textarea | no | |

Form settings: `name: Tag suggestion`, `title: "Tag suggestion: "`,
`labels: ["tag-suggestion"]`. The `tag-suggestion` label must exist in the repository.
