# Tasks: The Topic Tagger as a Python API

**Input**: `specs/006-tagger-api/`: spec.md, plan.md, research.md (R1–R9), data-model.md,
contracts/api.md and quickstart.md.

**Tests**: Required (constitution I). Within each story the test task comes first:
1. Write the tests.
2. Run them and see them fail.
3. Commit them as `test(tagger): …`.
4. Write the code that passes them, and commit it as `feat(tagger): …` (or `refactor(tagger): …` for the foundational moves).

**Where**: All paths are under `tools/topic-tagger/`.
- Run tests from there with `uv run pytest`.
- Lint with `uv run ruff check . && uv run ruff format --check .`.
- API tests use **provider objects** (T001), not the fake HTTP hosts. They need no network and no local port.
- `tests/conftest.py` already has `StubProvider` (a scripted chat host), `FakeClock` and fixtures for `scheme_small.toml`, `scheme_1tier.toml`, `scheme_3tier.toml`, `scheme_run.toml` and `variables.jsonl`.

**Branch**: `006-tagger-api`, off `005-configurable-classifier`. One PR, targeting `005-configurable-classifier` until #48 and #51 merge.

**Rules checked throughout**:
- The CLI's output and every existing test stay unchanged (FR-016).
- API calls create no files and print nothing (FR-011, SC-003).
- The source label for a setting given to the API is `call`. The CLI keeps `cli`.

## Format: `[ID] [P?] [Story] Description`

---

## Phase 1: Setup

- [x] T001 Add provider-object fakes to `tests/conftest.py`, with a docstring each:
  - `FakeDecisionModel(probability=None, remote=False, refuse_over=None)`:
    - methods `check()`, `is_remote()` and `decide(state, instructions, options)`;
    - `probability(state, option) -> float` defaults to 0.9 for the first option and shares the rest equally;
    - `refuse_over=n` raises `OptionLimitError(400, "too many options", len(options))` when more than `n` options are offered;
    - it records `calls` (each `(state, instructions, options)`) and `checks` (a count).
  - `FakeChatModel(...)`: not needed. `StubProvider` already has `remote` and counts `checked`; the `fake_chat` fixture is `StubProvider(first_option)`, a reply that depends only on the request. Both fakes count host checks in `checked`.
  - Pytest fixtures `fake_decision` and `fake_chat`.

  No production code changes in this task.

---

## Phase 2: Foundational: shared pieces the API and the CLI both use (blocks every story)

**Purpose**: move the logic the API needs out of the CLI, with no change in behaviour (research R2, R4, R5; data-model "Internal changes").

- [x] T002 [P] Write failing tests in `tests/test_scheme.py`:
  1. `parse_scheme(text)` on the text of `closer.toml`, `scheme_small.toml` and `scheme_3tier.toml` gives the same `hash` as `load_scheme` on the file (`closer.toml`: `"3c9f6b4b4ef9"`), and an equal `root`.
  2. `parse_scheme("name = 1")` raises `SchemeError` whose message starts with `<text>`. `parse_scheme(bad, source="mine.toml")` starts with `mine.toml`.
  3. `parse_scheme("not toml [")` raises `SchemeError` containing `not valid TOML`.
  4. `load_scheme` accepts a `str` path as well as a `Path`.
- [x] T003 [P] Write failing tests in `tests/test_run_settings.py` for `settle(given, scheme, label="cli")`:
  1. It returns `Resolved` with the same values and sources as `resolve`, with sources labelled `label` instead of `cli` (try `label="call"`).
  2. It raises `ValueError` with the CLI's exact wording:
     - `--descend-at must be between 0 and 1` for `descend_at=1.5`;
     - the same for `keep_at=-0.1`;
     - `--max-follow must be 0 (no cap) or more` for `max_follow=-1`;
     - `--keep-at needs --provider ollama-decision` for `keep_at` with a chat provider;
     - `--descend-at and --max-follow need --method tiered` for flat with `descend_at` given.
  3. With `scheme_1tier.toml` and `method="tiered"`, `values["method"] == "flat"` and `notes` contains `This taxonomy has one tier: tagging flat.`
  4. With flat, `descend_at` and `max_follow` are dropped from `sources`.
  5. The file `keep_at` note from `resolve` is still in `notes`.
- [x] T004 [P] Write failing tests in `tests/test_variables.py`: `variable_from_dict` accepts a valid `variables.jsonl` line as a dict, giving the same `Variable` that `read_variables` gives for that line. It raises `ValueError` with the same messages for a missing `file`, an empty `variable`, and bad `values`.
- [x] T005 Run T002–T004 and see them fail. Commit as `test(tagger): parse_scheme, settle and variable_from_dict`.
- [x] T006 [P] In `src/topic_tagger/scheme.py`, add `parse_scheme(text: str, source: str = "<text>") -> Scheme`:
  - it holds the TOML parsing, validation, hash and `Scheme` construction now in `load_scheme`;
  - error messages start with `source`.

  `load_scheme(path)` reads the file (keeping its `cannot read` error) and calls `parse_scheme(text, str(path))`. Docstrings on both.
- [x] T007 [P] In `src/topic_tagger/run_settings.py`, add `settle(given: dict, scheme: Scheme, label: str = "cli") -> Resolved`. It moves the following from `cli._settle`, unchanged:
  - the range checks;
  - the `--keep-at` check;
  - the tiered-options check;
  - the file notes;
  - the one-tier fallback and its note (appended to `notes`, not printed);
  - dropping `descend_at`/`max_follow` sources when flat.

  It renames the `cli` source to `label`. It raises `ValueError(message)`. Avoid a circular import: import `Scheme` only under `TYPE_CHECKING`.
- [x] T008 [P] In `src/topic_tagger/variables.py`, rename `_parse`'s dict half to a public `variable_from_dict(data: dict) -> Variable`. `_parse` keeps the JSON decoding and calls it. Docstring.
- [x] T009 In `src/topic_tagger/cli.py`, make `_settle` call `run_settings.settle(given, scheme)`:
  - print each note with `_err`;
  - return the `ValueError`'s message as the problem;
  - set `args` from the values and `args.settings_source` from the sources, as now.

  In `src/topic_tagger/runner.py`, add a `RecordSink` protocol (`append(records: list[dict]) -> None`, docstring) and type `Runner`'s `store` as `RecordSink`. Then run the whole suite: every existing CLI test must pass unchanged. Commit as `refactor(tagger): share scheme parsing, settings checks and the line parser`.

**Checkpoint**: the suite passes, and the CLI output is byte-for-byte as before.

---

## Phase 3: User Story 1: tag in one call with a scheme file (P1) 🎯 MVP

**Goal**: `tag(inputs, scheme)` returns one `Result` per input in order, using the scheme's `[run]`, with nothing written.

**Independent test**: with `fake_decision`, tag three strings with `scheme_run.toml` (decision, tiered). Each result has leaf topics, confidences and a path; `tmp_path` stays empty; `capsys` captures nothing.

- [x] T010 [US1] Write failing tests in the new `tests/test_api.py`:
  0. An autouse fixture in `tests/test_api.py`: `monkeypatch.chdir(tmp_path)` before each test. After it, assert `list(tmp_path.iterdir()) == []` and `capsys.readouterr() == ("", "")`. Tests that expect an exception still pass through it (SC-003).
  1. `tag(["Do you smoke?", "Weight in kg", "Do you smoke?"], scheme_run_path, provider=fake_decision)` returns 3 results in input order:
     - each `input` is the string passed;
     - `tags` are strongest first, and every `topic` is a leaf id of the scheme;
     - `path` is a list of `(group, confidence)`;
     - `failed` is False;
     - duplicates are tagged separately.
  2. Each string reaches the model as the state `{"name": "", "label": text, "values": []}`.
  3. A `Variable` input reaches the model as `{"name": …, "label": …, "values": [...]}`, exactly as `tiered._state` makes it. A dict in the `variables.jsonl` form behaves the same. Strings, variables and dicts mix in one call. A `Variable` with 40 value labels reaches the model with 30 of them, then `"… and 10 more"`.
  4. `classify("Do you smoke?", scheme_run_path, provider=fake_decision)` returns one `Result`, not a list.
  5. `Results`:
     - supports `len`, indexing and iteration;
     - `settings["method"] == "tiered"`, with `sources["method"] == "file"`;
     - `scheme_hash` equals `load_scheme(scheme_run_path).hash`;
     - `requests_by_tier` is non-empty.
  6. `tag([], …)` returns empty `Results`, and `fake_decision.calls == []` and `checks == 0`.
  7. `Result.topics` lists the topic ids. `Result.to_dict()` has `topics`, `method`, `model`, `scheme`, `failed` and `error`, plus `path` when tiered.
- [x] T011 [US1] Run T010 and see it fail. Commit as `test(tagger): tag and classify in one call`.
- [x] T012 [US1] Create `src/topic_tagger/api.py` with Google-style docstrings throughout:
  - `Tag(topic, label, confidence)`: frozen dataclass.
  - `Result(input, tags, path, failed, error)`, with the `topics` property and `to_dict()`, as in data-model.md.
  - `Results`: a `Sequence[Result]` with `settings`, `sources`, `notes`, `requests_by_tier`, `retries`, `scheme_name`, `scheme_hash` and a `failed` property.
  - `_MemorySink` with `append(records)`, keeping records by `file` (the position).
  - `_to_variable(i, item)`:
    - a `str` becomes `Variable(file=str(i), variable="", label=item)`;
    - a `Variable` gets `dataclasses.replace(item, file=str(i))`;
    - a `dict` goes through `variable_from_dict` and then is replaced the same way; a `ValueError` is re-raised as `ValueError(f"input {i}: {e}")`;
    - anything else raises `TypeError(f"input {i}: expected text, a Variable or a dict, got {type(item).__name__}")`.
  - `Tagger.__init__(scheme=None, *, provider=None, model=None, method=None, descend_at=None, max_follow=None, keep_at=None, base_url="http://localhost:11434/v1", api_key=None, timeout=120, batch_size=20, workers=2, retries=2, allow_remote=False, check=True)`:
    - loads the scheme: a `Scheme` is used as is, `None` means `parse_scheme(bundled_scheme_text(), "closer.toml")`, anything else goes to `load_scheme`;
    - calls `settle(..., label="call")` and stores `settings`, `sources` and `notes`;
    - makes the provider with `get_provider` when given a name (`api_key` defaults to `os.environ.get("TOPIC_TAGGER_API_KEY")`);
    - no network.
  - `Tagger.tag(inputs)`:
    - converts the inputs;
    - returns empty `Results` for no inputs;
    - checks the host once (`self._checked`) unless `check=False`;
    - builds `Settings` (with `model=f"{provider}:{model}"`) and a `Runner(scheme, provider, _MemorySink(), settings, SystemClock(), decider=…)`, with a `DecisionDecider(provider, keep_at, scheme.guidance)` for a decision provider;
    - runs it, and maps each record and each failed key (`"{i}/{name}"`) back to its position;
    - a failed input has `error = run_result.last_error`;
    - tags get their labels from `scheme.topics`.
  - `Tagger.classify(input)`.
  - Module-level `tag(inputs, scheme=None, **options)` and `classify(input, scheme=None, **options)`.

  Run T010 until it passes. Commit as `feat(tagger): tag and classify text and variables in code`.
- [x] T013 [US1] Re-export from `src/topic_tagger/__init__.py`, with `__all__` exactly as in contracts/api.md:
  - `tag`, `classify`, `Tagger`, `Result`, `Results`, `Tag`;
  - `Variable`, `Scheme`, `load_scheme`, `parse_scheme`;
  - `SchemeError`, `ProviderError`, `OptionLimitError`, `RemoteModelError` (a stub class until US3).

  Add a test to `tests/test_api.py` that every name in `topic_tagger.__all__` imports and has a docstring (see it fail first). Commit as `test(tagger): …` then `feat(tagger): the public names, in topic_tagger.__all__`.

**Checkpoint**: MVP. `from topic_tagger import tag` works with a scheme's `[run]`.

---

## Phase 4: User Story 2: choose the model, provider and method in code (P1)

**Goal**: call arguments override `[run]`; schemes come from text, objects or the bundle; provider objects are accepted.

**Independent test**: the same scheme tagged with and without `method="flat"` records both methods, with `sources["method"]` `file` and `call`.

- [x] T014 [US2] Write failing tests in `tests/test_api.py`:
  1. With `scheme_run.toml`:
     - `method="flat"` gives `settings["method"] == "flat"` and `sources["method"] == "call"`;
     - every `path is None`;
     - `fake_decision` was asked one question per input offering every leaf.
  2. `descend_at=0.9, max_follow=1` override the file's values, and their sources are `call`.
  3. `tag(texts, parse_scheme(text_of_scheme_run))` behaves as the file, with the same `scheme_hash`.
  4. `tag(texts, provider=fake_decision)` with no scheme uses the bundled scheme (`scheme_hash == "3c9f6b4b4ef9"`, `scheme_name == "CLOSER topics"`).
  5. A provider object with `decide` is a decision model (default method `tiered`, `keep_at` `0.3`). A `fake_chat` object is a chat model (default method `flat`, `keep_at` None). The `provider` source is `call` in both cases.
  6. With `fake_chat` and `scheme_small.toml`, both `flat` and `tiered` give leaf tags.
  7. With `scheme_1tier.toml` and `method="tiered"`, `notes == ["This taxonomy has one tier: tagging flat."]` and the method is `flat`.
  8. `model="my-model"` with a provider object is stored in `to_dict()["model"]` as `ollama-decision:my-model`. Without it, the model is `ollama-decision:custom`.
  9. `Tagger(...)` exposes `settings`, `sources` and `notes` before any call, with no `check()` made.
  10. With `topic_tagger.api.get_provider` monkeypatched to record its arguments and return `fake_decision`: `Tagger(provider="ollama-decision", base_url="http://h:1/v1", timeout=7, api_key="k")` passes `base_url`, `timeout`, `model` and `api_key` through. With no `api_key` and `TOPIC_TAGGER_API_KEY=env` set, it passes `"env"`.
  11. With `fake_chat` and `scheme_small.toml` flat, `batch_size=1` over 3 inputs sends 3 requests (`len(fake_chat.calls) == 3`), and the default sends 1. A `[run]` table cannot set `batch_size`: it is rejected by the scheme check, as on the command line.
  12. A provider object without `is_remote`, or with neither `decide` nor `complete`, raises `TypeError` at `Tagger(...)`, naming the missing method.
- [x] T015 [US2] Run T014 and see it fail. Commit as `test(tagger): settings, schemes and providers from code`.
- [x] T016 [US2] In `src/topic_tagger/api.py`, make T014 pass. *(Done: this code went in with T012, ahead of its tests, so T014 passed on its first run. Each part was checked by removing it and seeing a T014 test fail. The tests were committed as regression tests.)*
  - a provider object counts as `ollama-decision` if `hasattr(obj, "decide")`, else `ollama` (check for `check`, `is_remote`, and `decide` or `complete`; else `TypeError` naming what is missing), when settling;
  - `model` defaults to `"custom"` for objects;
  - everything else should already follow from `settle` (verify the one-tier note reaches `Results.notes`).

  Commit as `feat(tagger): call arguments override the scheme's [run]; provider objects`.

---

## Phase 5: User Story 3: errors a caller can handle (P2)

**Goal**: every problem is an exception, with the CLI's wording; nothing is printed; cloud models need consent.

**Independent test**: each row of quickstart.md step 5 raises its exception, and `capsys` stays empty.

- [x] T017 [US3] Write failing tests in `tests/test_api.py` (the autouse fixture from T010 checks that nothing is printed or written):
  1. A broken scheme path raises `SchemeError` listing every problem. `parse_scheme` of bad text raises it too.
  2. `descend_at=1.5` raises `ValueError("--descend-at must be between 0 and 1")`. `keep_at=0.4` with `fake_chat` raises a `ValueError` about `--keep-at`. Neither touches the provider.
  3. `tag([42], …)` raises `TypeError` naming input 0. A dict without `file` raises `ValueError` starting `input 0:`.
  4. A provider whose `check()` raises `ProviderError("model missing")` makes `tag` raise that error before any `decide`.
  5. `FakeDecisionModel(remote=True)` without `allow_remote` raises `RemoteModelError` (a `ProviderError` subclass) whose message names the model and says to pass `allow_remote=True`. `calls` and `checks` are both 0. With `allow_remote=True` it tags.
  6. `FakeDecisionModel(refuse_over=5)` with the bundled scheme flat raises `OptionLimitError`, with `.options == 107` and `.question == "every topic, asked flat"`.
  7. A decision model that raises `ProviderError("no answer")` for one input's state every time gives that `Result` `failed=True` and `error == "no answer"` (the only error in the call). The others are tagged, with `failed=False` and `error == ""`, and the call does not raise.
  8. Search `src/topic_tagger/api.py`: it contains no `print(`, `input(`, `sys.exit` or `open(`. Test this by reading the source.
- [x] T018 [US3] Run T017 and see it fail. Commit as `test(tagger): errors from the API`.
- [x] T019 [US3] In `src/topic_tagger/api.py`:
  - define `class RemoteModelError(ProviderError)` with a docstring;
  - in `Tagger.tag`, before the host check, raise it when `provider.is_remote() and not allow_remote`. (`RemoteModelError` was already defined in `api.py` with T012, so `__init__.py` needed no stub.)
  - if `RunResult.refusal` is set after the run, raise it (its `question` and `advice` are already filled in by the walk);
  - replace the `RemoteModelError` stub in `__init__.py`.

  Commit as `feat(tagger): the API raises, never prints; cloud models need allow_remote`.

---

## Phase 6: User Story 4: reuse one tagger (P3)

**Goal**: one `Tagger`, many calls, one host check.

**Independent test**: a tagger called twice checks the host once and matches two one-call results.

- [x] T020 [US4] Write failing tests in `tests/test_api.py`:
  1. `t = Tagger(scheme_run_path, provider=fake_decision)`. `t.tag(a)`, then `t.tag(b)`, gives `fake_decision.checks == 1`.
  2. The results equal `tag(a, …)` and `tag(b, …)` made separately: same topics and confidences.
  3. `check=False` makes no `check()` call at all.
  4. `t.classify(x)` reuses the same check.
- [x] T021 [US4] Run T020.
  - If any test fails: commit the tests as `test(tagger): one tagger, many calls`, make them pass in `src/topic_tagger/api.py`, and commit that as `feat(tagger): …`.
  - If all pass (T012 already checks the host once): no code change follows. Commit the tests as `test(tagger): one tagger, many calls (regression)`, with the commit body saying T012 already covers it.

---

## Phase 7: Polish and cross-cutting

- [x] T022 Write failing `tests/test_api.py::test_the_api_and_the_cli_give_the_same_tags` (SC-002, FR-014). For each of the four combinations (chat or decision model, flat or tiered) on `tests/fixtures/variables.jsonl`:
  - run `cli.main([...], provider_factory=lambda args: model, clock=FakeClock())` into `tmp_path` with `--yes --plain --batch-size 20 --workers 1`;
  - run `tag(read_variables(path), …, provider=model, batch_size=20, workers=1)`;
  - with one worker, the batches are the same and in the same order on both sides;
  - assert each variable's topics, confidences and path are equal.

  Use `scheme_small.toml`. For chat, use a deterministic `FakeChatModel` whose reply depends only on the request, not on call order. Fix any difference found in `api.py`. Commit the test, then the fix.
- [x] T023 [P] Bump the version to `0.2.0` in `pyproject.toml` and `src/topic_tagger/__init__.py`. Add a test in `tests/test_package.py` that the two agree. Run `uv lock` (the project's own entry changes only).
- [x] T024 [P] Add a "Using it from Python" section to `README.md`, after the CLI sections:
  - a three-line example;
  - schemes from text;
  - overriding `[run]`;
  - provider objects for tests;
  - `allow_remote`;
  - the exceptions table;
  - what the API does not do (no files, no resume; use the CLI for those);
  - a link to `specs/006-tagger-api/contracts/api.md`.

  Also add a line to the repository `CLAUDE.md` tagger paragraph: "it can also be used from Python (`from topic_tagger import tag`)".
- [x] T025 [P] Add the 006 API to `scripts/demo.py`. It needs no network, so it goes in the `--offline` group:
  - a step `python API: tag, settings and errors` that runs `tag` with an inline fake decision model on `example-3-tier.toml`;
  - it checks the leaf tags, `sources`, the one-tier note, and `RemoteModelError`.
- [ ] T026 Run quickstart.md steps 1–5, the full suite, ruff, and at the repository root `uv run pytest tests/python` (checking `scripts/topics.py` still merges). Tick the tasks here.
- [ ] T027 Maintainer, outside the sandbox: run quickstart.md step 6 against the local Ollama, and `uv run python scripts/demo.py --yes`.

---

## Dependencies

- **Setup (T001)**: needed by every API test.
- **Foundational (T002–T009)**: blocks every story. T002–T004 can be written in parallel, and so can T006–T008. T009 depends on T007.
- **US1 (T010–T013)**: after Foundational. The MVP.
- **US2 (T014–T016)**: after US1 (same `api.py`).
- **US3 (T017–T019)**: after US1, independent of US2 apart from the shared file.
- **US4 (T020–T021)**: after US1.
- **Polish**: T022 after US2 and US3. T023–T025 in parallel, any time after US3. T026 last. T027 can be done any time after T026.

Stories share `api.py` and `tests/test_api.py`, so in practice they go in order: US1 → US2 → US3 → US4.

## Parallel examples

- **Foundational tests**: T002 (`test_scheme.py`), T003 (`test_run_settings.py`) and T004 (`test_variables.py`) together.
- **Foundational code**: T006 (`scheme.py`), T007 (`run_settings.py`) and T008 (`variables.py`) together, then T009.
- **Polish**: T023 (version), T024 (README) and T025 (demo) together.

## Implementation strategy

1. **MVP**: Setup, Foundational and US1. `tag()` works from a scheme file, which is the feature.
2. **US2**: overrides and provider objects, which make it usable in other people's tests.
3. **US3**: errors and consent, needed before anyone relies on it in a pipeline.
4. **US4 and polish**: reuse, the CLI equivalence test, docs and the demo. Then T027 with a real model.
