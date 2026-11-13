# Contract: `topic-tagger tag` options

| Option | Default | Meaning |
|---|---|---|
| `--method flat\|tiered` | `flat` | `flat`: one request per batch listing every topic (as now). `tiered`: one request per tier (see spec FR-002). |
| `--descend-at X` | `0.5` | Tiered only. Follow an area when its confidence is at least X (0–1). |
| `--max-areas N` | `3` | Tiered only. Follow at most N areas per variable; `0` means no cap. |
| `--keep-at X` | `0.3` | Decision provider only. Keep a topic when its probability is at least X (0–1); `0` keeps every topic. |
| `--provider ollama-decision` | | Ollama's decision API (`/v1/systemone`), e.g. `--model clef:cloud`. Tiered only: `--method` defaults to `tiered`, and `--method flat` exits 2. |

Errors (exit 2, bad input):
- `--descend-at` outside 0–1;
- `--max-areas` below 0;
- `--descend-at` or `--max-areas` given without `--method tiered`;
- `--keep-at` given without `--provider ollama-decision`.

Exit 3 (no host) when Clef is not pulled: `model clef:cloud is not installed; run: ollama pull clef:cloud`.

A model ending `:cloud` or `-cloud` asks before sending (unless `--yes`), for every Ollama provider.

## `/v1/systemone` request (decision provider)

```json
{"model": "clef:cloud",
 "state": {"name": "smoke5", "label": "Does the mother smoke", "values": ["1: Yes", "2: No"]},
 "questions": {"option": {"type": "choice",
   "instructions": "Which areas of a survey is this variable about? If more than one applies, share the probability between them.",
   "criteria": {"health": "Health: … It includes: Smoking, …", "housing": "Housing: …"}}}}
```

2 to 26 options per question; a scheme with a bigger tier exits 2 before any request.
Confidences are read from `answers.option.probabilities.<id>`.

## `--dry-run --method tiered`

With the decision provider it prints the first variable's tier-1 and one tier-2
`/v1/systemone` body as JSON. With a chat provider it prints the first batch's tier-1 request, a line `--- tier 2 example (<area label>) ---`,
then the tier-2 request for the first area, with the batch's variables. Nothing is sent.

## Summary line

The summary adds, for a tiered run:
`Requests by tier: 1: <n>, 2: <n>` and `Areas followed per variable: <mean>`.
