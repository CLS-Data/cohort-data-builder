# Contract: choosing cohorts (address, storage, control)

## Page address

`index.html#<key>[+<key>…]`, e.g. `#ncds+bcs70`. Keys are written in catalogue order
whatever order they were chosen. On load and on `hashchange`, unknown keys are dropped;
an address with no known key is ignored. A single key (`#bcs70`) is today's address and
still works, so existing links keep working.

## Storage

| Key | Value | Notes |
|---|---|---|
| `cohort-data-builder:_site:cohorts` | `["ncds","bcs70"]` | NEW: the choice |
| `cohort-data-builder:_site:cohort` | `"bcs70"` | OLD: read once if the new key is absent; no longer written |
| `cohort-data-builder:<key>:selection` | `[{name,label,file,wave,column}]` | unchanged, one per cohort |

Order of precedence: address, `cohorts`, `cohort`, first catalogue cohort.

## Header control

```html
<div class="cohorts" role="group" aria-label="Cohorts">
  <button type="button" data-cohort="ncds" aria-pressed="true">
    <span class="coh-mark" aria-hidden="true"></span>NCDS</button>
  …
</div>
```

- One button per catalogue cohort, catalogue order; pressing toggles the cohort.
- Each button's title says what the cohort is: full name — description, then
  `N variables in M files.` (FR-011).
- When one cohort is chosen its button has `aria-disabled="true"` and its title adds "At
  least one cohort stays chosen."; pressing it does nothing.
- A loading cohort's button shows a busy state (`aria-busy="true"`); a failed one stays
  pressed and its heading in the results offers Retry.
- Replaces `<select id="dataset">`. The tests' `#dataset` selector moves to
  `.cohorts button[data-cohort=…]`.

## Title and footer (FR-016)

| Place | One cohort | Several |
|---|---|---|
| `document.title` | `Cohort Data Builder` | `Cohort Data Builder` |
| `#foot-counts` | as today | summed variables and files, then `· N cohorts` |
