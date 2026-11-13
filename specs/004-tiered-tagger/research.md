# Research: Tiered tagging

## R1. Requests per tier: per batch, grouped by area

- **Decision**: Tier 1 is one request for the whole batch over the areas. Tier 2 is one
  request per chosen area, holding only the batch's variables routed there. Deeper tiers
  repeat this.
- **Rationale**: This is "one call per tier" without one call per variable. With 20
  variables and areas capped at 3 per variable, a batch typically touches 3–6 areas, so it
  takes 4–7 requests, against 1 for flat. Each request is short, and each decision is among
  at most about 15 options.
- **Alternatives**:
  - One request per variable per tier: 20× more requests, too slow for 37,000 variables.
  - Tier 2 listing all chosen areas' topics in one request: fewer requests, but it brings
    back the long list the feature is meant to avoid.

## R2. What tier 1 shows the model

- **Decision**: For each area, its label and description followed by its topic labels as a
  short comma-separated list, without topic descriptions.
- **Rationale**: Area descriptions alone are thin ("Health"). The topic labels tell the
  model where, say, "pregnancy" lives (Health or Family?). This is far shorter than the
  flat prompt, which carries every topic's description.
- **Alternatives**: Area label and description only. The ad hoc comparison can test this
  variant if routing errors show up. It is a one-line change in `prompt.py`.

## R3. Which areas to follow

- **Decision**: Follow each area with confidence ≥ `--descend-at` (default 0.5), at most
  `--max-areas` (default 3), strongest first. Always follow the strongest area.
- **Rationale**: Variables legitimately span areas ("mother smoked in pregnancy": Health
  and Family). A cap bounds the request count (SC-002). Always following the top area
  means no variable stalls at tier 1.
- **Alternatives**:
  - Top-1 only: cheapest, but loses every secondary topic, which the flat guidance asks for.
  - No cap: unbounded requests.

## R4. Stored confidence

- **Decision**: Store the tier-2 (leaf) confidence. Record the tier-1 confidence in `path`.
- **Rationale**: The site filters by confidence. Multiplying the tiers (0.8 × 0.8 = 0.64)
  would shift every tiered tag down and make the two methods incomparable. `path` keeps
  the information for the report and for later analysis.
- **Alternatives**: The product of the tiers: arguably calibrated, but it changes the
  meaning of the existing slider.

## R5. Retries and failures

- **Decision**: Each request runs the existing ladder: retries, then variables asked alone,
  then failed for that group. A variable is stored when all its groups finish. It counts as
  failed only if it ends with no tags.
- **Rationale**: This is the same behaviour as flat, applied per request. A variable keeps
  its good areas' tags even when one area fails.

## R6. Mixing methods in one output folder

- **Decision**: Records store `method`. `state()` treats a record made with a different
  method as stale, so switching method redoes the tags. A missing `method` means flat.
- **Rationale**: This is the same rule as the scheme hash: tags reflect how they were made.
  It is needed for the comparison, which uses separate folders anyway.

## R7. Scheme depth

- **Decision**: Keep the two-tier TOML format. Build a generic `Node` tree from it and walk
  it with one loop that works at any depth.
- **Rationale**: "And so on" is covered by the walk, while the scheme format and its
  validation stay as they are (YAGNI). Nested topics in TOML can come later and only need
  `Node` to be built differently.

## R8. Ad hoc testing

- **Decision**:
  - The set: `adhoc/tiered/` holds about 80 fictional variables written for this, in the
    tagger's input format, with `expected.json` giving the topics a person would choose
    (bundled CLOSER scheme).
  - The script: `compare.py` runs `topic-tagger tag` twice (`--method flat` and
    `--method tiered`, `--model gpt-oss:20b-cloud --yes`) into `runs/<method>-<date>/`.
  - The scores: top-1 hit (is the strongest tag expected?), recall and precision against
    `expected.json`, requests and seconds, and a list of disagreements.
  - Version control: `/adhoc/` is added to `.gitignore`.
- **Rationale**:
  - The variables are fictional, which follows the standing rule: no study metadata goes
    to a cloud model unless the maintainer chooses.
  - The set spans every area, with some cross-area variables, so routing errors show.
  - Keeping the folder git-ignored means real data in `adhoc/data/` is never committed.
- **Alternatives**:
  - Real BCS70 variables: more realistic, but they need labelling and the maintainer's
    consent to send them to a cloud model. Left as an option in the quickstart.
  - The 60-variable test fixture: it uses the small 3-area scheme and has no expected
    topics.
- **Models**: three runs:
  - flat with `gpt-oss:20b-cloud`;
  - tiered with `gpt-oss:20b-cloud`;
  - tiered with `clef:cloud` (`--provider ollama-decision`).

## R9. Clef: how to ask

- **Decision**:
  - At each tier, one `noul` question per option, keyed by the option id. Its
    `instructions` are "Is this survey variable about <label>? <description>". For areas,
    the topic labels are appended, as in R2.
  - The `state` is the variable as a JSON object: `{"name", "label", "values"}`, with values
    capped at 30, as the chat prompt does.
  - Confidence is the `noul` probability.
  - Areas are followed by `--descend-at` and `--max-areas` (R3).
  - Leaves are kept at ≥ `--keep-at` (default 0.3, the threshold the scheme's guidance
    already gives chat models). The strongest leaf is kept if none passes.
- **Rationale**: Topics are multi-label. A `choice` question returns one winner, and its
  probabilities sum to 1, so a second true topic would look weak. `noul` gives each option
  an independent probability, which matches "every topic that applies".
- **Alternatives**: One `choice` question per tier. It is cheaper, but single-label. The ad
  hoc script can try it as a variant if `noul` proves slow or costly.

## R10. Calling `/v1/systemone`

- **Decision**: A small `OllamaDecisionProvider` uses `urllib.request` to send
  `POST {base}/v1/systemone` with
  `{"model", "state", "questions": {id: {"type": "noul", "instructions": …}}}`, and reads
  `answers[id].noul`.
  - **Checking the model:** `check()` reuses `GET /v1/models`, as the chat provider does.
  - **Splitting:** more than 64 options are split across requests (the cloud limit).
  - **Retries and timeouts:** none in the client, since retries are the runner's job. The
    timeout comes from `--timeout`.
- **Rationale**: The `openai` client has no such endpoint, and the `ollama` Python package
  would be a new dependency for one POST. The standard library is enough, and it is easy to
  fake in tests with the existing local-server pattern.
- **Alternatives**: The `ollama` package (`ollama.systemone`): a new runtime dependency.
  `typesafe-sdk`: the same objection.

## R11. One variable per Clef request

- **Decision**: The decision decider sends one variable per request. Concurrency comes from
  `--workers`. `--batch-size` still groups variables for the walk and for storing.
- **Rationale**: `state` describes one thing, and its questions are about that thing.
  Packing variables into one state and naming questions per variable would mix them up.
- **Cost**: about 1 + (areas followed) requests per variable. For the 80-variable set that
  is about 250 requests. For a full cohort it is large, which is one reason this is
  compared before becoming any default.

## R12. Remote models

- **Decision**: For both Ollama providers, a model counts as remote when it ends in
  `-cloud` or `:cloud`.
- **Rationale**: `clef:cloud` uses the `:cloud` form, which today's `-cloud` check misses,
  so the tool would not ask before sending metadata off the machine. This is a fix that
  applies to chat models too (FR-014).
