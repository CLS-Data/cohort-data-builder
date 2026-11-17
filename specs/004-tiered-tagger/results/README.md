# Results: flat and tiered tagging on real variables

Two reports, made on 13 and 16 November 2026 with the tagger as of commit `436baf0`.
Open them in a browser; each is a single self-contained HTML file.

| Report | What it compares |
|---|---|
| [`report-10k.html`](report-10k.html) | 10,000 variables, three ways: gpt-oss:120b flat, gpt-oss:120b tiered, Clef tiered |
| [`report-clef-vs-tev.html`](report-clef-vs-tev.html) | The first 200 of the same sample: Clef tiered and tev1:0.8b tiered (a local decision model) |

**What is in them:** variable names, labels and value labels from the cohorts in
`site/data` (already in this repository), and the tags each run gave them. No respondent
data.

**Sample:** 10,000 variables picked at random (seed 2026) from all 113,767 in bcs70, mcs,
ncds and next_steps.

**Settings:**
- All runs: the bundled CLOSER scheme (15 areas, 107 topics), 8 workers, batches of 20.
- gpt-oss tiered: `--descend-at 0.5 --max-areas 3`.
- Clef and tev: `--descend-at 0.3 --keep-at 0.3 --max-areas 3`.
- Tiered runs offer `other` at tier 1 as an exit.

There are no expected answers for real variables, so the reports show where the methods
agree and differ, not which is right. Findings are in `../research.md`, "Results".

In `report-clef-vs-tev.html`, Clef's requests, wall time and variables per minute are for
its whole 10,000-variable run. Compare the "≈ s/var (1 worker)" column instead.

## Reproducing

The scripts are in `scripts/`. Their inputs and run folders go to `adhoc/tiered/`, which is
git-ignored. `compare_sample.py` explains each step in its docstring:
1. export the cohorts;
2. `sample`;
3. `run`;
4. `report`.

Re-running needs Ollama, signed in for the cloud models. It takes about 2.5 hours for the
three main runs, and makes about 26,000 requests.

`build_labelled_set.py` and `score_labelled_set.py` are the fictional labelled set (82
variables with expected topics) and its scorer, which sweeps the thresholds (research R13).
That comparison has not been run yet (task T027).
