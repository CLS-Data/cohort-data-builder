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
- When one cohort is chosen its button has `aria-disabled="true"` and the title "At least
  one cohort stays chosen"; pressing it does nothing.
- A loading cohort's button shows a busy state (`aria-busy="true"`); a failed one stays
  pressed and its overview row offers Retry.
- Replaces `<select id="dataset">`. The tests' `#dataset` selector moves to
  `.cohorts button[data-cohort=…]`.

## Title, subtitle, footer (FR-016)

| Place | One cohort | Several |
|---|---|---|
| `document.title` | `BCS70 · Cohort Data Builder` | `NCDS + BCS70 · Cohort Data Builder` |
| `#mark-sub` | full name | short names joined by ` + ` |
| `#foot-counts` | as today | summed variables and files, then `· N cohorts` |
