# Contract: `topic-tagger tag` options

| Option | Default | Meaning |
|---|---|---|
| `--method flat\|tiered` | `flat` | `flat`: one request per batch listing every topic (as now). `tiered`: one request per tier (see spec FR-002). |
| `--descend-at X` | `0.5` | Tiered only. Follow an area when its confidence is at least X (0–1). |
| `--max-areas N` | `3` | Tiered only. Follow at most N areas per variable (N ≥ 1). |

Errors (exit 2, bad input):
- `--descend-at` outside 0–1;
- `--max-areas` below 1;
- `--descend-at` or `--max-areas` given without `--method tiered`.

## `--dry-run --method tiered`

Prints the first batch's tier-1 request, a line `--- tier 2 example (<area label>) ---`,
then the tier-2 request for the first area, with the batch's variables. Nothing is sent.

## Summary line

The summary adds, for a tiered run:
`Requests by tier: 1: <n>, 2: <n>` and `Areas followed per variable: <mean>`.
