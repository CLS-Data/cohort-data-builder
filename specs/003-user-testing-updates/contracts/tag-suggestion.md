# Contract: Tag suggestion link and issue form

## The dialog (builder)

In each variable's opened details, after the Topics line: a button, "Suggest a tag change"
(or "Suggest a tag" when the variable has none). It opens a modal dialog
(`js/ui/suggest.js`) named "Suggest tags for <variable>":

- a "Filter topics" box, focused on open;
- the variable's current tags first, ticked, with their confidence; then every other topic
  of the cohort's taxonomy, by domain;
- a live summary ("Adds Tenure · removes Alcohol"), and "Open on GitHub", disabled until
  something changes;
- "Why (optional)"; Cancel or Escape closes without doing anything.

"Open on GitHub" opens the issue link below in a new tab, with the choice written into
`suggested` and the reason into `why`, and closes the dialog. Nothing in the builder changes.

## The link

```text
https://github.com/CLS-Data/cohort-data-builder/issues/new
  ?template=tag-suggestion.yml
  &title=Tag suggestion: <variable> (<cohort>)
  &cohort=<cohort name>
  &variable=<variable>
  &file=<file>
  &label=<label, ≤ 300 characters>
  &current=<Topic (90%); Topic (60%)…, or "none">
  &suggested=Add: <Domain › Topic>; …⏎Remove: <Domain › Topic>; …   (lines only when non-empty)
  &why=<the reason, when given>
```

Every value is URL-encoded. The whole URL is at most 8,000 characters: if longer, `current`
then `why`, then `label` are cut, ending with `…`. Built by
`tagSuggestionUrl(entry, file, manifest, suggestion)`
in `site/js/core/feedback.js` (pure, no DOM).

## The issue form (`.github/ISSUE_TEMPLATE/tag-suggestion.yml`)

| Field id | Type | Required | Notes |
|---|---|---|---|
| `cohort` | input | yes | pre-filled |
| `variable` | input | yes | pre-filled |
| `file` | input | yes | pre-filled |
| `label` | textarea | no | pre-filled |
| `current` | textarea | no | pre-filled current tags |
| `suggested` | textarea | yes | pre-filled from the dialog: "Add: …" / "Remove: …" |
| `why` | textarea | no | pre-filled when given |

Form settings: `name: Tag suggestion`, `title: "Tag suggestion: "`,
`labels: ["tag-suggestion"]`. The `tag-suggestion` label must exist in the repository.
