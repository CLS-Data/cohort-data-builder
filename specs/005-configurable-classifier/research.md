# Research: A configurable classification pipeline

Decisions for feature 005. Each one gives the decision, the rationale and the alternatives.
It builds on `specs/004-tiered-tagger/research.md`.

## R1. How a decision host reports too many options

- **Findings** (Ollama docs, 16 November 2026):
  - `https://docs.ollama.com/capabilities/decision` states "2–26 named options".
  - The API reference `https://docs.ollama.com/api/systemone.md` says "The option limit
    depends on the model". The `criteria` schema allows 2 to 255.
  - Errors are JSON `{"error": "<message>"}`, with HTTP 400 for an invalid request (also used
    for a prompt over the context window) and 413 for size limits.
  - No message text is documented for too many options, and the API offers no way to look
    up a model's limit.
- **Measured** (T032, 16 November 2026, `scripts/demo.py` against the local Ollama):
  `clef:cloud` answered a flat question with all 107 leaves of the bundled scheme, and one
  with a 30-topic group, without error. It picked sensible topics well past option 26 (for
  example `identifiers`, option 104 of 107). Clef has no limit at or below 107, so there is no
  refusal text to record. The text match stays as designed, for models that do refuse, and
  is covered by the stubbed tests in `tests/test_decision_provider.py`.
- **Decision**:
  - The provider no longer checks the number of options.
  - On an HTTP error it reads the body's `error` text.
  - A 400 or 413 raises `OptionLimitError(ProviderError)` when its text has both of these,
    and does not mention `context` or `token`:
    - an options word: `option`, `choice` or `criteri`;
    - a size word: `too many`, `exceed`, `limit`, `at most` or `maximum`.

    The error carries the status, the host's message and the number of options sent.
  - Every other error stays a plain `ProviderError` and goes through the retry ladder, as
    today.
- **Rationale**:
  - The limit belongs to the model (spec FR-009), and the host is the only thing that knows
    it.
  - Matching on the text is the only signal the API gives. Keeping the match narrow means a
    400 caused by one oversized variable (context window) is not mistaken for a too-big
    question, which would stop a whole run.
- **Open, for the maintainer** (task in `/speckit-tasks`): send Clef a 27-option `choice`
  outside the sandbox. Record the exact status and text here, and pin the fake host's
  refusal and the match to it. If Clef answers without refusing (for example, it scores only
  26), record that. The provider already raises `ProviderError` for an option with no
  probability, and this case would then also be turned into `OptionLimitError`.
- **Alternatives**:
  - A per-model limit table, or a `max_options` setting: rejected by the user. Limits
    differ by model and are not published.
  - Treating every 400 as fatal: stops runs over a single bad variable.
  - Probing the model with a test question at start-up: costs a request, and still depends
    on recognising the same error.

## R2. Stopping the run on `OptionLimitError`

- **Decision**:
  - `OptionLimitError` is never retried and never sent one variable at a time:
    `DecisionDecider`, `tiered._ask` and `Runner._batch` re-raise it.
  - The runner sets its stop flag, as it does for Ctrl-C. Batches still in flight finish
    and are stored; no new batch starts.
  - `RunResult.stop_reason` holds the message. `run.json` gets `stop_reason`, and the CLI
    exits with **5** (`REFUSED`).
- **The message**, built where the question is known (the walk knows the node):
  - which question: the whole flat list, the top tier, or a group by id and label;
  - its option count;
  - the host's message;
  - the hint: for flat, "tag tiered"; for a group, "split <group> into smaller groups".
- **Rationale**:
  - The same question will be refused for every variable that reaches it, so retrying only
    wastes requests and marks variables failed (spec SC-002).
  - Reusing the stop flag keeps what was tagged, and resuming already works.
- **Alternatives**:
  - Mark the variables failed and carry on: the spec rejects this.
  - Stop only that branch of the taxonomy: tags would quietly lack a whole group.

## R3. One tree for both file forms

- **Decision**:
  - A `Category(id, label, description, children)` tree.
  - The 004 form (`domains` → `topics`) loads as a two-tier tree. The new form nests
    `[[categories]]` tables under `categories`, at most three deep.
  - A file uses one form or the other, never both.
  - In the new form, `description` is optional. The 004 form keeps its current rules.
- **The hash**: as before, over the parsed file, but without the `[run]` table. A 004 file,
  which has no `[run]`, therefore keeps its hash, and its output folders stay current
  (FR-004, FR-018).
- **Rationale**:
  - One tree is what both methods and both model kinds walk.
  - Hashing the parsed content (not the text) was already the rule. Leaving out `[run]`
    means editing a threshold does not redo every tag.
- **Alternatives**:
  - A `tiers = [...]` list of named levels with parent links: harder to write by hand, and
    harder to check.
  - Converting 004 files on load and changing their hash: forces a full retag for no change.

## R4. Keeping the `Scheme` views

- **Decision**: `Scheme` holds `root` and derives the old views from it:
  - `topics`: every leaf, in file order;
  - `topic_ids` and `topic_number`;
  - `domains`: one per top-tier category, holding all leaves beneath it. A top-tier leaf is
    its own one-topic domain;
  - `domain_of(leaf)`: its top-tier ancestor.

  `scheme.json` gains `categories` (the tree) and `tiers`, and keeps `domains` from the
  derived view.
- **Rationale**:
  - Statistics, the report and the live display group by area. "Top-tier category" is the
    natural meaning of area at any depth.
  - `scripts/topics.py` reads `scheme.json` `domains` → `topics`, so the site merge keeps
    working without change.
- **Alternatives**: Rewriting stats, the report and the display to show every tier.
  Possible later, but not needed for this feature.

## R5. Which tags are exits

- **Decision**: Only the fallback is an exit, offered at tier 1. In 004, any leaf chosen at
  a tier that also held groups was treated as an exit, and dropped when a group gave tags.
  That was right only because the fallback was the only such leaf.
- **Rationale**: In an uneven taxonomy, real leaves sit beside groups (for example tier 2 of
  `example-3-tier.toml`). Dropping them would lose true tags.
- **Selection is unchanged**: at a tier with groups, leaves and groups are chosen alike, by
  `descend_at`, the strongest always, at most `max_follow`. At a tier of only leaves, every
  answered leaf is kept, and decision models also apply `keep_at`.

## R6. Flat with a decision model

- **Decision**: `flat_tree(scheme)` is a root whose children are every leaf, including the
  fallback.
  - It is walked with `DecisionDecider`: one `choice` per variable, `keep_at` applies, and
    no path is stored. The record's method is `flat`.
  - Flat with an LLM keeps its own path (`build_messages`), so its prompt is
    byte-for-byte what it is today (`tests/fixtures/flat_prompt.txt`).
- **Rationale**: This reuses the decider, retries and stop logic, with no second code path
  for decision models.
- **Alternatives**: A separate flat decision loop in the runner: it would duplicate the
  ladder and the stop handling.

## R7. Tiered with a one-tier taxonomy

- **Decision**: The resolved method becomes `flat`. The CLI prints "this taxonomy has one
  tier: tagging flat", and records `method: "flat"`.
- **Rationale**: The two are the same question. Storing `flat` means a later flat run does
  not count the tags as stale.

## R8. Tier questions

- **Guidance for decision models** (checked in the `systemone` API reference, 16 November
  2026): the request has only `model`, `state`, `images`, `questions` and `keep_alive`.
  There is no field for shared background, and `state` is the thing being judged.
  - So every question's `instructions` is the scheme's guidance, a blank line, then the
    question. Each request has one question, so this is the same as shared context.
  - The `state` stays the variable alone.
  - This changes 004's Clef requests, which sent no guidance. The tags are not marked out
    of date, because the guidance was already in the hash.
- **Decision**: an optional `[questions]` table with keys `flat`, `tier1`, `tier2` and
  `tier3`.
  - `{group}` is replaced by the label of the category whose children are offered. That is
    the taxonomy's name at tier 1.
  - Decision model: the question replaces the built-in question, after the guidance (above).
  - LLM: it is added as a line, `Question: …`, before the options. With no `[questions]`,
    the prompts are exactly as today.
  - Unknown keys, or `tierN` beyond the taxonomy's depth, are refused when the file is
    loaded.
  - The questions are part of the hash.
- **Rationale**: Decision models see only the question and the options, so the wording is
  how the user steers them (spec story 4). Leaving today's prompts unchanged keeps the
  golden prompt test, and the 004 comparison, valid.

## R9. Run settings and precedence

- **Decision**: a `[run]` table with these keys:

  | Key | Values |
  |---|---|
  | `provider` | `ollama` or `ollama-decision` |
  | `model` | text |
  | `method` | `flat` or `tiered` |
  | `descend_at` | 0–1 |
  | `max_follow` | integer ≥ 0, where 0 means no cap |
  | `keep_at` | 0–1 |

  - Unknown keys and bad values are refused at load, with their location.
  - Precedence: the command line, then `[run]`, then the defaults. `run_settings.resolve()`
    returns the values and `{setting: "cli" | "file" | "default"}`, written to `run.json`
    as `settings_source`.
  - Defaults are as in 004:
    - `ollama`, `gpt-oss:20b`;
    - flat for a chat model, tiered for a decision model;
    - descend at 0.5, follow at most 3, keep at 0.3.
- **Two rules change**:
  - `--max-areas` becomes `--max-follow`. The old name stays as an alias, since "areas" has
    no meaning at tier 3.
  - A `keep_at` in the file is ignored by a chat model, with a note. On the command line it
    is still an error, as in 004. A shared file may name a decision model's threshold and
    still be run with a chat model.
- **Not in `[run]`**: base URL, API key, workers, batch size, retries, timeout and output
  paths. These are machine-specific, or secret (spec assumption).
- **Rationale**: one file reproduces a classification (SC-005), and the command line still
  allows one-off changes.

## R10. Depth and the check command

- **Decision**:
  - At most three tiers. A deeper file is refused, with the location of the first category
    at tier 4.
  - `check-scheme` prints:
    - the tiers, and the categories at each tier;
    - the leaves;
    - the largest question flat (every leaf, plus nothing else);
    - the largest question at each tier, naming the group, and counting the fallback exit
      at tier 1.
  - The dry run prints one example request per tier, following the first group down, for
    the chosen model kind.
- **Rationale**: the user decides whether a taxonomy fits their model (spec story 5). The
  tool cannot know the model's limit (R1), so it only reports sizes.
