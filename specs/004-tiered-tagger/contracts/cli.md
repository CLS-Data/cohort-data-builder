# Contract: `topic-tagger tag` options

| Option | Default | Meaning |
|---|---|---|
| `--method flat\|tiered` | `flat` | `flat`: one request per batch listing every topic (as now). `tiered`: one request per tier (see spec FR-002). |
| `--descend-at X` | `0.5` | Tiered only. Follow an area when its confidence is at least X (0–1). |
| `--max-areas N` | `3` | Tiered only. Follow at most N areas per variable (N ≥ 1). |
| `--keep-at X` | `0.3` | Decision provider only. Keep a topic when its probability is at least X (0–1). |
| `--provider ollama-decision` | | Ollama's decision API (`/v1/systemone`), e.g. `--model clef:cloud`. Needs `--method tiered`. |

Errors (exit 2, bad input):
- `--descend-at` outside 0–1;
- `--max-areas` below 1;
- `--descend-at` or `--max-areas` given without `--method tiered`;
- `--keep-at` given without `--provider ollama-decision`;
- `--provider ollama-decision` with `--method flat` (message: "a decision model answers one tier
  at a time: use --method tiered").

Exit 3 (no host) when Clef is not pulled: `model clef:cloud is not installed; run: ollama pull clef:cloud`.

A model ending `:cloud` or `-cloud` asks before sending (unless `--yes`), for every Ollama provider.

## `/v1/systemone` request (decision provider)

```json
{"model": "clef:cloud",
 "state": {"name": "smoke5", "label": "Does the mother smoke", "values": ["1: Yes", "2: No"]},
 "questions": {"health": {"type": "noul", "instructions": "Is this survey variable about Health? …"},
               "housing": {"type": "noul", "instructions": "…"}}}
```

At most 64 questions per request. Answers are read from `answers.<id>.noul`.

## `--dry-run --method tiered`

With the decision provider it prints the first variable's tier-1 and one tier-2
`/v1/systemone` body as JSON. With a chat provider it prints the first batch's tier-1 request, a line `--- tier 2 example (<area label>) ---`,
then the tier-2 request for the first area, with the batch's variables. Nothing is sent.

## Summary line

The summary adds, for a tiered run:
`Requests by tier: 1: <n>, 2: <n>` and `Areas followed per variable: <mean>`.
