# Tasks: A configurable classification pipeline for the Topic Tagger

**Input**: `specs/005-configurable-classifier/`: spec.md, plan.md, research.md
(R1–R10), data-model.md, contracts/cli.md, contracts/formats.md and quickstart.md.

**Tests**: Required (constitution I). Within each story the test task comes first:
1. Write the tests.
2. Run them and see them fail.
3. Commit them as `test(tagger): …`.
4. Write the code that passes them, and commit it as `feat(tagger): …` (or `fix(tagger): …`).

**Where**: All paths are under `tools/topic-tagger/`.
- Run tests from there with `uv run pytest`.
- Lint with `uv run ruff check . && uv run ruff format --check .`.
- Reuse the scripted chat model in `tests/conftest.py` and the fake HTTP hosts in
  `tests/test_provider.py` (`FakeOllama`) and `tests/test_decision_provider.py`.
- Tests must not touch the network or Ollama.

**Branches**: One short branch per phase off `005-configurable-classifier`, for example
`005-foundation`, `005-us1-tiers` and `005-us2-methods`. One PR each, squash-merged.

**Docs in the same change** (constitution II): each story ends with a docs task, so its PR
updates `README.md` and `docs/formats.md` together with the code. Polish (T029–T030) only
checks the docs read as one whole.

**Compatibility rules**, checked by tests throughout:
- `closer.toml` keeps its hash.
- `tests/fixtures/flat_prompt.txt` still matches.
- Tier prompts with no `[questions]` are byte-for-byte as in 004.

## Format: `[ID] [P?] [Story] Description`

---

## Phase 1: Setup

- [x] T001 [P] Add `tests/fixtures/scheme_1tier.toml`. It uses the nested form (contracts/formats.md): 5 tier-1 leaves, `age`, `smoking`, `housing`, `income` and `other`, with `fallback_topic = "other"`. There is no `[run]` and no `[questions]`. Add a header comment saying what it is for.
- [x] T002 [P] Add `tests/fixtures/scheme_3tier.toml`, an uneven three-tier taxonomy in the nested form:
  - `health`, with:
    - `physical_health`, a group of the leaves `respiratory`, `cardiac` and `diabetes`;
    - `mental_health`, a group of `depression` and `anxiety`;
    - `smoking`, a tier-2 leaf;
  - `demographics`, holding the tier-2 leaves `age` and `gender`;
  - `other`, a tier-1 leaf and the fallback.

  `fallback_topic = "other"`. Some categories have no description.
- [x] T003 [P] Add `tests/fixtures/scheme_run.toml`. It is `scheme_small.toml` (004 form) plus:
  - `[run]`: `provider = "ollama-decision"`, `model = "fake-decision"`, `method = "tiered"`, `descend_at = 0.3`, `max_follow = 2`, `keep_at = 0.2`;
  - `[questions]`: `tier2 = "Which topic within {group}?"`.

---

## Phase 2: Foundational: one category tree (blocks every story)

**Purpose**: `scheme.py` loads both file forms into one `Category` tree and derives the
views the rest of the code already uses (research R3, R4; data-model "Category" and
"Taxonomy").

- [x] T004 Write failing tests in `tests/test_scheme.py`:
  1. `closer.toml` and `scheme_small.toml` load with **the same `hash` as before**. Pin today's values as literals, copied from `uv run topic-tagger check-scheme` on `main`. They have `tiers == 2`, and unchanged `topics`, `topic_ids`, `domains` and `domain_of`.
  2. `scheme_1tier.toml` has `tiers == 1` and 5 leaves. Each `domains` entry is a one-topic domain of itself, and `domain_of("age").id == "age"`.
  3. `scheme_3tier.toml` has:
     - `tiers == 3`;
     - leaves in file order (`respiratory, cardiac, diabetes, depression, anxiety, smoking, age, gender, other`);
     - `domain_of("respiratory").id == "health"`;
     - `path_of("respiratory") == ["health", "physical_health"]`;
     - a missing description read as `""`.
  4. Each of these files is refused, with these locations:
     - a 4th tier: `categories[0].categories[0].categories[0].categories[0]`, "at most 3 tiers";
     - the same id at two tiers;
     - a group with `categories = []`;
     - only one leaf;
     - `fallback_topic` naming a group;
     - both `domains` and `categories` in one file;
     - a missing `label` in the nested form.

     Every problem is listed, not only the first.
  5. `to_json()` adds `tiers` and the `categories` tree, and keeps `domains` (data-model). `scheme_from_json(to_json())` round-trips for the 1-, 2- and 3-tier fixtures, and still reads a 004 `scheme.json` that has only `domains`.
- [x] T005 Implement in `src/topic_tagger/scheme.py`:
  - a frozen `Category(id, label, description, children)`;
  - `Scheme.root` and `Scheme.tiers`;
  - `topics`, `topic_ids`, `topic_number`, `domains`, `domain_of` and the new `path_of`, all derived from `root`;
  - `validate()` for the nested form. Rules: "Unique across the whole taxonomy, at every tier", "No category may sit at tier 4", "at least two leaves", "`fallback_topic` must name a leaf", and "A file uses `categories` (nested) or `domains` (004), never both".
  - The 004 form is loaded into the same tree, keeping its current rules.
  - `to_json()` and `scheme_from_json()` as in contracts/formats.md.

  Keep the hash computation unchanged for now: T021 removes `[run]` from it. Docstrings on every new class and function. Then run the whole suite; the other modules must pass unchanged.

**Checkpoint**: every existing test passes, and the scheme can be 1–3 tiers.

---

## Phase 3: User Story 1: any taxonomy of one to three tiers (P1) 🎯 MVP

**Goal**: Tag with a 1-, 2- or 3-tier taxonomy, flat or tiered, with a chat model. Each
record stores leaves, and its path through the tiers.

**Independent test**: With the scripted chat model, tag `tests/fixtures/variables.jsonl`
with each fixture taxonomy. Every stored topic is a leaf of that taxonomy, and three-tier
tiered records carry two-step paths.

- [x] T006 [P] [US1] Write failing tests in `tests/test_tiered.py`:
  1. `build_tree(scheme_3tier)` keeps `health → physical_health → {respiratory, cardiac, diabetes}`. It puts `other` at tier 1 as an exit, and `_height(root) == 3`.
  2. Moving the fallback prunes empty groups, repeatedly up the tree. A fixture where the fallback is the only leaf of a tier-2 group, itself the only child of a tier-1 group, loses both groups.
  3. `walk` over `scheme_3tier` with a scripted decider:
     - one variable chooses `health`, then `physical_health` (0.8) and the tier-2 **leaf** `smoking` (0.7) at the same tier, then `respiratory`;
     - it ends with tags `respiratory` and `smoking`;
     - its path is `[("health", …), ("physical_health", 0.8)]`;
     - `smoking` is **not** dropped as an exit (research R5).
  4. The fallback chosen with a group that gives tags is still dropped, as in 004.
  5. `requests_by_tier` has three entries.
- [x] T007 [P] [US1] Write failing tests in `tests/test_prompt.py`:
  1. The flat chat prompt for `scheme_small.toml` still equals `tests/fixtures/flat_prompt.txt`.
  2. For `scheme_3tier.toml`, the flat prompt lists every leaf once, under headings of its path (`## Health › Physical health`). A tier-1 leaf goes under no heading.
  3. For `scheme_1tier.toml`, it lists the leaves with no headings.
- [x] T008 [US1] Write failing tests in `tests/test_runner.py`. Use the scripted chat model to tag with `scheme_1tier.toml` flat, and with `scheme_3tier.toml` flat and tiered. Check:
  - every record's topics are leaves of its scheme;
  - tiered records have `method == "tiered"` and paths of one or two entries;
  - `RunResult.requests_by_tier` has three entries for the three-tier run.
- [x] T009 [US1] Implement `build_tree` for any depth in `src/topic_tagger/tiered.py`:
  - convert from `scheme.root`;
  - move the fallback to tier 1, pruning empty groups repeatedly up the tree;
  - in `walk`, restrict `exits` to the fallback id (research R5). Update the comment and docstring that describe areas and exits so they say "groups".
- [x] T010 [US1] Implement the path headings in `src/topic_tagger/prompt.py` `_system()` (no headings for one tier; the 004 output is unchanged for two tiers), so that T007 passes.
- [x] T011 [US1] Make T008 pass in `src/topic_tagger/runner.py`. It is probably only `_tiered` needing no area-specific assumptions. Check that `display.py`, `stats.py` and `report.py` work for 1- and 3-tier schemes by extending one test each in `tests/test_display.py`, `tests/test_stats.py` and `tests/test_report.py`, with a 3-tier scheme. Fix only what fails.

- [x] T011b [US1] Document the nested form in the same PR:
  - **`docs/formats.md`**: the `[[categories]]` nesting, at most 3 tiers, optional descriptions, the rules from data-model "Category", and the `scheme.json` `categories` and `tiers` fields;
  - **`README.md`**: taxonomies of 1–3 tiers, uneven depth, and that areas in the report are tier-1 categories.

**Checkpoint**: US1 is done. Any 1–3 tier taxonomy tags with a chat model, flat or tiered.

---

## Phase 4: User Story 2: any model with either method; refusals stop the run (P1)

**Goal**: Decision models tag flat or tiered. There is no built-in option limit. A
too-many-options refusal stops the run with exit 5 (research R1, R2, R6, R7).

**Independent test**: Run fake decision hosts flat and tiered on the fixture taxonomies. A
host that refuses questions with more than 5 options stops the run, naming the question.

- [x] T012 [P] [US2] Write failing tests in `tests/test_decision_provider.py`, against the fake decision host:
  1. A `choice` with 27 or more options is **sent**, so there is no client-side 2–26 check.
  2. An HTTP 400 with body `{"error": "too many options for choice question"}` raises `OptionLimitError`, with `status == 400`, the `host_message` and `options == 27`.
  3. A 413 whose text mentions criteria does the same.
  4. A 400 with `{"error": "prompt exceeds context window"}` raises a plain `ProviderError`, **not** `OptionLimitError`, and includes the host's text.
  5. A 500 stays a plain `ProviderError`.
  6. A 400 with `{"error": "prompt for choice question exceeds the model's context window"}` stays a plain `ProviderError`, so mentioning "choice" alone is not enough. The match needs an options word together with a size word: `too many`, `exceed`, `limit`, `at most` or `maximum`, and no `context` or `token`. Record the rule in research.md R1.
- [x] T013 [P] [US2] Write failing tests in `tests/test_tiered.py`:
  1. `flat_tree(scheme)` has every leaf as a direct child of the root, including the fallback, in file order.
  2. `walk(flat_tree, …)` with a `DecisionDecider` over a scripted decision provider keeps leaves at `keep_at`, and the strongest leaf if none passes. It stores no path, and sends 1 request per variable.
  3. When the decision provider raises `OptionLimitError` for a node, `walk` re-raises it, and the error names the question:
     - at the root of a flat tree: "every topic, asked flat";
     - at the tiered root: "the tier-1 categories and the fallback exit";
     - at a group: its id, label and tier.

     The decider is called once only: no retries and no single requests.
  4. `choice_problems` no longer exists.
- [x] T014 [US2] Write failing tests in `tests/test_runner.py` and `tests/test_cli.py`:
  1. Decision **flat** with `scheme_small.toml` tags every variable. Records have `method: "flat"` and no `path`, and `requests == variables`.
  2. `--provider ollama-decision --method flat` is accepted (it was exit 2 in 004).
  3. With a fake host that refuses questions over 5 options:
     - **flat** with 8 leaves: the exit status is 5;
     - stderr matches contracts/cli.md: "refused a question with 8 options (every topic, asked flat)", the host's text, and "Tag tiered";
     - `run.json` has `stop_reason`;
     - `counts.failed == 0`, and no retries are counted.
  4. With a scheme where one group has 6 children, **tiered**, `--workers 2` and `--batch-size 2`:
     - batches finished before the refusal are stored, including one that was in flight beside the refused batch (the fake host delays it until the refusal has been sent);
     - no new batch starts after the refusal;
     - the message names that group;
     - after splitting the group in the scheme and running again, the stored variables are not redone.
  5. **Tiered with `scheme_1tier.toml`** prints "This taxonomy has one tier: tagging flat." and records `method: "flat"`.
- [x] T015 [US2] Implement in `src/topic_tagger/providers/__init__.py` and `src/topic_tagger/providers/ollama_decision.py`:
  - `class OptionLimitError(ProviderError)` with `status`, `host_message` and `options`;
  - remove `MIN_OPTIONS`/`MAX_OPTIONS` and the check in `decide()`;
  - in `_call`, read the HTTP error body's `error` text and include it in messages;
  - raise `OptionLimitError` for 400 or 413 when the text matches `option|choice|criteri` (case-insensitive), as in research R1.

  Update the module docstrings, which mention 2 to 26.
- [x] T016 [US2] Implement in `src/topic_tagger/tiered.py`:
  - `flat_tree(scheme)`;
  - `DecisionDecider.decide` re-raises `OptionLimitError` instead of skipping the variable;
  - `_ask` re-raises it at once, with the question named, with no retry and no singles;
  - delete `choice_problems` and its `MAX_OPTIONS` import;
  - update the `DecisionDecider` docstring ("tags tiered only" is no longer true).
- [x] T017 [US2] Implement in `src/topic_tagger/runner.py` and `src/topic_tagger/cli.py`:
  - **Runner**:
    - decision-flat goes through `walk(flat_tree(…))`, storing method `flat` with no path;
    - `Runner(..., decider=…)` accepts any method;
    - an `OptionLimitError` from a batch sets the stop flag, and `RunResult.stop_reason` holds the message (research R2).
  - **CLI**:
    - remove the "tags tiered only" error and the `choice_problems` check from `_check_method` and `_tag`;
    - add exit status `REFUSED = 5`;
    - print the message from contracts/cli.md;
    - write `stop_reason` to `run.json`;
    - a one-tier taxonomy turns tiered into flat, with the notice.

- [x] T017b [US2] Document in the same PR:
  - **`README.md`**:
    - decision models tag flat or tiered;
    - option limits are the model's, with no built-in check;
    - the refusal message, and exit 5 in the exit code table.

    Remove "tiered only" and every "26".
  - **`docs/formats.md`**: `run.json` `stop_reason`, and decision-flat records (`method: "flat"`, no `path`).

  T032 (Clef's real refusal text) should be done before this PR merges.

**Checkpoint**: US1 and US2 work. All four combinations run, and a refusal stops cleanly.

---

## Phase 5: User Story 3: the TOML file controls the run (P2)

**Goal**: The `[run]` table sets the provider, model, method and thresholds. The command
line overrides it, and sources are recorded (research R9; data-model "RunSettings").

**Independent test**: Tag with `scheme_run.toml` and no options. `run.json` shows the
file's values with source `file`. Adding `--method flat` changes only `method`, with
source `cli`.

- [ ] T018 [P] [US3] Write failing tests in `tests/test_scheme.py`:
  1. `[run]` is parsed into `Scheme.run`.
  2. Each of these is refused, with its location:
     - `run.colour = 1` (unknown key);
     - `run.method = "deep"`;
     - `run.provider = "x"`;
     - `run.descend_at = 1.5`;
     - `run.keep_at = -0.1`;
     - `run.max_follow = -1`;
     - `run.max_follow = 1.5`.

     The rules are "0–1" for thresholds, and "integer ≥ 0 (0 = no cap)" for `max_follow`.
  3. **The hash leaves out `[run]`**: `scheme_run.toml` with only `descend_at` changed has the same hash. With its `[questions]` changed, it has a different hash.
- [ ] T019 [P] [US3] Write failing tests in a new `tests/test_run_settings.py` for `resolve(cli: dict, file: RunSettings | None) -> (values, sources)`:
  1. **Precedence**: CLI, then file, then default.
  2. **Defaults**:
     - `provider` `ollama`;
     - `model` `gpt-oss:20b`;
     - `method` `tiered` for `ollama-decision`, else `flat`;
     - `descend_at` 0.5, `max_follow` 3, `keep_at` 0.3.
  3. **The method default follows the resolved provider**: a file provider of `ollama-decision` gives tiered when `method` is unset.
  4. A file `keep_at` with a chat provider is dropped, with a note.
  5. Each `sources` entry is `cli`, `file` or `default`.
- [ ] T020 [US3] Write failing tests in `tests/test_cli.py`:
  1. `tag --scheme scheme_run.toml` with a fake decision host and no options gives a `run.json` with `settings.method == "tiered"`, `descend_at == 0.3`, `max_follow == 2`, `max_areas == 2`, and `settings_source` all `file` except the unset ones (`default`).
  2. `--method flat` gives `method` from source `cli`.
  3. `--max-areas 1` still works, as an alias of `--max-follow`.
  4. A bad `[run]` value exits 2, naming `run.<key>` and the file.
  5. `--keep-at` with a chat provider on the command line is still exit 2.
  6. The end-of-run summary prints the method, the provider (model kind), the model and the number of tiers, for example `Method: tiered with ollama-decision:fake-decision, 2 tiers`. It still prints `Requests by tier: …` (spec FR-021).
- [ ] T021 [US3] Implement `[run]` parsing and validation in `src/topic_tagger/scheme.py`. Leave `run` out of the hash's canonical JSON (research R3). Add a comment saying why.
- [ ] T022 [US3] Create `src/topic_tagger/run_settings.py`, with `RunSettings` and `resolve()` as tested. Give the module, class and functions Google-style docstrings.
- [ ] T023 [US3] Wire it into `src/topic_tagger/cli.py`:
  - argparse defaults of `None` for `--provider`, `--model`, `--method`, `--descend-at`, `--max-follow` (with `--max-areas` as an alias, `dest="max_follow"`) and `--keep-at`;
  - load the scheme before making the provider;
  - `_check_method` uses the resolved values;
  - write `settings_source`, `tiers`, `max_follow` and `max_areas` to `run.json` (contracts/formats.md);
  - rename `Settings.max_areas` to `max_follow` in `src/topic_tagger/runner.py`, and update `RunResult.areas_followed` wording to "groups followed";
  - add the method, provider, model and tiers line to the summary (`_tier_lines` in `cli.py`), as T020 item 6 requires.
- [ ] T023b [US3] Document in the same PR:
  - **`README.md`**: the `[run]` table, precedence (command line, then file, then default), `--max-follow` with `--max-areas` as an alias, and a file `keep_at` being ignored by chat models;
  - **`docs/formats.md`**: `[run]` keys and values, the hash leaving out `[run]`, and `run.json` `settings_source`, `tiers` and `max_follow`.

**Checkpoint**: a scheme file alone reproduces a run.

---

## Phase 6: User Story 4: the prompt shapes each question (P2)

**Goal**: The guidance reaches both kinds of model. `[questions]` words the flat question
and each tier's question (research R8).

**Independent test**: A dry run with `scheme_run.toml` shows the tier-2 question, with
`{group}` filled in, in the decision body's `instructions` and in the chat prompt.

- [ ] T024 [P] [US4] Write failing tests:
  1. **`tests/test_scheme.py`**: `[questions]` accepts `flat`, and `tier1` up to `tier<tiers>`. It refuses `tier3` in a two-tier scheme, and refuses unknown keys, with their locations.
  2. **`tests/test_tiered.py`**:
     - `decision_request` at a tier-2 node of `scheme_run.toml` has `instructions == guidance + "\n\n" + "Which topic within Health?"` (research R8);
     - with no question for a tier, the question part is the built-in 004 wording, unchanged;
     - flat decision requests use `questions.flat` when set.
  3. **`tests/test_prompt.py`**:
     - `build_option_messages` with a question adds the line `Question: Which topic within Health?` before `Options. Use only these ids:`;
     - without one, the output is byte-for-byte as in 004 (pin it with a literal);
     - the flat chat prompt adds `Question: …` when `questions.flat` is set.
  4. **Guidance reaches the decision model**: every `/v1/systemone` body, at every tier and flat, has `instructions` starting with the scheme's guidance (stripped), then a blank line, then the question. The `state` is unchanged: the variable only (research R8).
- [ ] T025 [US4] Implement `[questions]` in `src/topic_tagger/scheme.py`, and pass questions and guidance to the deciders and prompts in `src/topic_tagger/tiered.py` and `src/topic_tagger/prompt.py`:
  - `{group}` is the label of the node being asked about, which is the scheme's name at the root;
  - the questions are part of the hash. They already are, being outside `[run]`; T018 tests this.

- [ ] T025b [US4] Document in the same PR. In `docs/formats.md` and `README.md`, cover:
  - `[questions]` keys and `{group}`;
  - the hash including the questions;
  - the guidance going to decision models before each question.

**Checkpoint**: the user steers each question from the file.

---

## Phase 7: User Story 5: see what each run will ask (P3)

**Goal**: `check-scheme` reports sizes, and the dry run shows every tier (research R10;
contracts/cli.md).

**Independent test**: `check-scheme tests/fixtures/scheme_3tier.toml` prints tiers, counts
and the largest question per tier, without a model.

- [ ] T026 [P] [US5] Write failing tests in `tests/test_cli.py`:
  1. **`check-scheme`**:
     - on `scheme_3tier.toml` it prints the lines of contracts/cli.md, with these counts: tier 1: 3 categories; leaves 9; flat 9 options; tier 1: 3 options, counting the exit; tier 2: 3 options in `health`; tier 3: 3 options in `physical_health`;
     - on `closer.toml` it prints `2 tiers` and its unchanged hash;
     - on `scheme_run.toml` it prints the run settings line.
  2. **`tag --dry-run`**:
     - with `scheme_3tier.toml` and a decision provider, it prints three JSON bodies, preceded by `--- tier 1 ---`, `--- tier 2 example (Health) ---` and `--- tier 3 example (Physical health) ---`;
     - with a chat provider, it prints three chat requests;
     - flat prints one;
     - nothing is sent: the fake host sees no request.
- [ ] T027 [US5] Implement `_check_scheme` and the dry-run printing in `src/topic_tagger/cli.py`. Replace `_print_tiered_requests` and `_print_decision_requests` with one function that follows the first group down to the leaves. Put a helper `question_sizes(tree)` in `src/topic_tagger/tiered.py`, with a docstring.

- [ ] T027b [US5] Document in the same PR. In `README.md`, cover:
  - the new `check-scheme` output, and how to compare its largest question with a model's limit;
  - the dry run showing every tier.

**Checkpoint**: every story is done.

---

## Phase 8: Polish and cross-cutting

- [ ] T028 [P] Add `src/topic_tagger/schemes/example-1-tier.toml` and `src/topic_tagger/schemes/example-3-tier.toml`. Each is commented as a worked example, and the 3-tier one is uneven, with `[questions]` and `[run]`. Add a test in `tests/test_package.py` that both are packaged and load.
- [ ] T029 [P] Read `README.md` through as a whole, after T011b–T027b:
  - one consistent vocabulary: category, group, leaf, tier, and "area = tier-1 category";
  - the bundled examples (T028) are referred to;
  - no "tiered only", "26" or `--max-areas` left except as the alias.
- [ ] T030 [P] Read `docs/formats.md` through as a whole against contracts/formats.md. Fix any gaps left by the story PRs.
- [ ] T031 [P] Fix `specs/004-tiered-tagger/research.md` R10 and R14 with a one-line note each: "Superseded by 005 research R1/R6: the option limit is the model's, and decision models can tag flat."
- [ ] T032 Maintainer, outside the sandbox: run quickstart.md step 8.
  - Record Clef's exact status and error text for a 107-option `choice` in `specs/005-configurable-classifier/research.md` R1.
  - If the text does not match `option|choice|criteri`, open a `fix(tagger)` change. Its test, in `tests/test_decision_provider.py`, uses the real text.
- [ ] T033 Run the full quickstart.md steps 1–7, `uv run pytest`, ruff, and at the repository root `uv run pytest tests/python` (checking `scripts/topics.py` still merges). Tick the tasks here.

---

## Dependencies and execution order

- **Setup (T001–T003)**: no dependencies; all [P].
- **Foundational (T004–T005)**: blocks every story.
- **US1 (T006–T011)**: needs Phase 2. It is the MVP.
- **US2 (T012–T017)**:
  - needs Phase 2, and uses `build_tree` from T009;
  - T012 and T015 (the provider) can start right after Phase 2, in parallel with US1.
- **US3 (T018–T023)**: needs Phase 2. It touches `scheme.py` and `cli.py`, so do it after US2's `cli.py` work (T017), to avoid conflicts.
- **US4 (T024–T025)**: needs US3's `scheme.py` changes (T021), and both deciders (T016).
- **US5 (T026–T027)**: needs US1 and US2 (trees and the flat tree), and US3 for the run settings line.
- **Docs**: each story's `b` task (T011b, T017b, T023b, T025b, T027b) goes in that story's PR.
- **Polish**: after all stories. T032 can happen any time after T015, and should be done before the US2 PR merges.

Inside each story: tests, then models (`scheme.py`), then the walk and providers, then the
runner and CLI.

## Parallel examples

```text
After Phase 2:  T006 (test_tiered)  ‖  T007 (test_prompt)  ‖  T012 (test_decision_provider)
US2 tests:      T012  ‖  T013   (different files)
US3 tests:      T018  ‖  T019
Polish:         T028  ‖  T029  ‖  T030  ‖  T031
```

## Implementation strategy

1. **MVP**: Phases 1–3 (US1). The tool takes any taxonomy of one to three tiers with a
   chat model. Stop and validate with quickstart steps 1–2.
2. **US2**: decision models flat and tiered, and the refusal stop. Together with US1, this
   is everything the user asked for in function.
3. **US3 and US4**: the file becomes the whole pipeline.
4. **US5 and polish**: checking, docs and examples. Then T032 with real Clef.
