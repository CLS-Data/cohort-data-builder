# Implementation Plan: Tiered tagging (decision model) for the Topic Tagger

**Branch**: `004-tiered-tagger` | **Date**: 2026-11-13 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/004-tiered-tagger/spec.md`

## Summary

Add a second tagging method to `tools/topic-tagger`: `--method tiered`. Instead of one
request listing every topic, each batch walks the taxonomy. One request chooses each
variable's areas (tier 1). Then one request per chosen area chooses topics from that area
only (tier 2), and so on for deeper trees. The walk reuses the existing pieces: prompts,
reply checks and the retry ladder. Each is generalised from "the scheme's topics" to "this
node's children". The flat method stays the default and is unchanged. Records gain `method`
and, for tiered tags, the `path` of areas chosen. A git-ignored `adhoc/tiered/` folder
holds a hand-labelled set of fictional variables and a script. The script tags the set both
ways and prints a comparison. That comparison decides whether tiered should become the
default (SC-001).

The tiered walk asks a **decider** at each tier, and there are two:
- **Chat decider:** batches variables into one prompt and checks a JSON reply, using the
  existing machinery, for chat models such as `gpt-oss:20b-cloud`.
- **Decision decider:** uses **Clef** (`clef:cloud`) through a new `ollama-decision`
  provider. That provider posts one variable at a time to Ollama's `/v1/systemone`, with
  one yes/no (`noul`) question per option, and uses the probabilities as confidences.

The comparison covers flat/gpt-oss, tiered/gpt-oss and tiered/Clef.

## Technical Context

**Language/Version**: Python 3.12 (the tagger's own project, `tools/topic-tagger/`)

**Primary Dependencies**: unchanged: `openai`, `pydantic`, `langchain-core`, `rich`. No
new dependency: the `/v1/systemone` call uses the standard library's `urllib.request`
(R10).

**Storage**: the output folder's `tags.jsonl`, `scheme.json` and `run.json`, with new
fields (contracts/formats.md).

**Testing**: pytest, with the existing scripted stand-in provider. It is extended to answer
by request (it sees which options a request lists). No network, no Ollama.

**Target Platform**: the maintainer's machine (macOS/Linux), Ollama on `localhost:11434`.
Cloud models are reached through it. Clef needs Ollama 0.40.6 or later for `clef:cloud`.
`ollama pull clef:cloud` adds it.

**Project Type**: CLI tool (standalone Python project)

**Performance Goals**: at most 1 + `--max-areas` requests per batch when nothing fails
(SC-002). The ad hoc comparison runs in under 10 minutes with the cloud model (SC-004).

**Constraints**: the flat method's prompts and output are unchanged apart from the
`method` field (FR-009). The tagger imports nothing outside its folder. `adhoc/` is never
committed. Only fictional variables are sent to the cloud model unless the maintainer
chooses otherwise.

**Scale/Scope**: the bundled CLOSER scheme has 15 areas and about 100 topics. Cohorts go up
to about 37,000 variables.

## Constitution Check

*GATE: checked before Phase 0 research, and again after Phase 1 design.*

| Principle | Status | How |
|---|---|---|
| I. Test-driven development | Pass | Each change starts with a failing test against the stand-in provider. The tier walk, routing, thresholds, retries per tier, the record fields, staleness by method and dry-run output are all deterministic. The ad hoc comparison is development tooling outside the product. It is not shipped, so it needs no CI tests (see Complexity Tracking). |
| II. Documented code | Pass | Docstrings on the new module and functions. `docs/formats.md` and the tagger README describe `--method`, `--descend-at`, `--max-areas`, `method`, `path` and the per-tier counts (FR-010). |
| III. Static GitHub Pages deployment | Pass (not affected) | Tagger only. The site reads `topics`, which is unchanged. `scripts/topics.py` ignores the new fields. |
| IV. Simplicity | Pass, with notes | No new dependency and no new abstraction beyond a small `Node` tree built from the scheme. The prompt, reply and runner functions take a node's children instead of the scheme. The scheme format stays two-tier. The walk is written for any depth because it costs nothing extra: it is the same loop. |
| Quality gates | Pass | The existing `topic-tagger` workflow runs lint and tests. The pull request has a "How to review" section. |

**After design**: still passes. One module is added (`tiered.py`). `prompt.py`, `reply.py`
and `runner.py` are generalised, with their flat behaviour pinned by the existing tests.

## Project Structure

### Documentation (this feature)

```text
specs/004-tiered-tagger/
├── spec.md
├── plan.md              # this file
├── research.md          # decisions R1–R8
├── data-model.md        # Node, decision path, records
├── quickstart.md        # how to run and compare
└── contracts/
    ├── cli.md           # new options and dry-run output
    └── formats.md       # tags.jsonl / run.json additions
```

### Source Code

```text
tools/topic-tagger/
├── src/topic_tagger/
│   ├── tiered.py        # NEW: Node tree from a scheme; the tier walk; ChatDecider, DecisionDecider
│   ├── providers/ollama_decision.py  # NEW: POST /v1/systemone (urllib), check(), is_remote()
│   ├── prompt.py        # options-based messages: flat = root's leaves; tiered = a node's children
│   ├── reply.py         # parse_reply takes the allowed ids, not the scheme
│   ├── runner.py        # Settings.method/descend_at/max_areas; per-tier counts; ladder per request
│   ├── store.py         # make_record(method, path); state() compares method too
│   └── cli.py           # --method, --descend-at, --max-areas; dry-run; summary per tier
├── tests/
│   ├── test_tiered.py   # NEW: tree, routing, thresholds, fallback, depth, retries per tier
│   ├── test_decision_provider.py  # NEW: fake /v1/systemone server: request shape, 64-split, errors
│   ├── test_prompt.py   # + tier prompts list only the node's children
│   ├── test_reply.py    # + ids outside the node's options rejected
│   ├── test_runner.py   # + tiered run end to end with the stand-in
│   ├── test_store.py    # + method/path fields; method change is stale
│   └── test_cli.py      # + options, dry-run, run.json, summary
├── docs/formats.md
└── README.md

adhoc/tiered/                 # NOT committed (/adhoc/ added to .gitignore)
├── variables.jsonl      # ~80 fictional variables, tagger input format
├── expected.json        # {variable: [topic ids a person expects]}
├── compare.py           # tags both ways with the cloud model, scores, prints the table
└── runs/                # output folders, one per method and date
```

**Structure Decision**: everything is inside the tagger's own project, as feature 002
requires. Ad hoc work lives in `adhoc/`, as asked, and is git-ignored like other working
files.

## Design notes

- **One batch, tiered** (R1): the batch is a group at the root. While there are groups,
  the walk takes one (a node and its variables).
  - If the node has more than one child, it sends one request listing them.
  - If it has exactly one child, it routes every variable there without asking, with the
    parent's confidence. This is how the bundled `other` area, whose only topic is
    `other`, becomes the fallback with no special case.
  - Children that are topics become tags. Children that are areas get new groups, with
    the variables routed to them (R3).
- **Retries** (R5): each request runs the existing ladder. A variable left out at one area
  is asked alone at that area. A variable is stored when all its groups have finished. It
  is failed only if it ends with no tags.
- **Confidence** (R4): a stored topic keeps its tier-2 confidence, so the site's confidence
  slider means the same thing for both methods. The tier-1 confidences go in `path`.
- **Staleness** (R6): `state()` compares `method` as well as the scheme hash. Records
  without `method` are flat.

## Complexity Tracking

| Addition | Why needed | Simpler alternative rejected because |
|---|---|---|
| `adhoc/tiered/compare.py` without CI tests | Development tool for judging SC-001 with a real model. It is not part of the product, and it needs the network and a cloud model. | Putting it in the tagger would ship an evaluation harness that depends on a live model. A CI version could only use the stand-in, which says nothing about quality. |
| `Decider` (one method: options + variables → confidences) with two implementations | Chat models answer a batch in JSON; Clef answers one state with typed questions. The tier walk must not care which. | Two tier walks, one per model kind, would duplicate the routing, thresholds and retries. |
| A second provider kind (`DecisionProvider`: `decide(state, questions)`) | `/v1/systemone` is not a chat API; the `Provider.complete` method cannot express it. | Forcing Clef through chat completions is not supported by Ollama. |
| Generalising `prompt`/`reply`/`runner` to options | Tier requests need the same messages, checks and ladder over a subset of ids. | A parallel copy for tiered requests would let the two methods drift apart. |
