# Feature Specification: The Topic Tagger as a Python API

**Feature Branch**: `006-tagger-api`

**Created**: 2026-11-17

**Status**: Draft

**Input**: User description: "Plan the above so that the tagger can be used within code."
The above is a function that you can pass text, a TOML config, a model and a provider to.
It applies the scheme's `[run]` table with the same precedence as the command line, and
returns tags in memory without writing files.

## Context

Since feature 002 the tagger has been a command-line tool. Its input is a `variables.jsonl`
file and its output is a folder (`tags.jsonl`, `run.json`, a report). Its modules can be
imported, but only by wiring internal pieces together by hand:

- loading the scheme;
- making a provider;
- choosing a tree and a decider;
- walking it.

Even then, the `[run]` table is not applied and there is no promise that any of it stays
stable.

This feature adds a small, documented API, so that other code can classify text or
variables in one call, with the same scheme files and the same results as the command line.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Tag in one call with a scheme file (Priority: P1)

A researcher writing a Python notebook or pipeline has some variables (or plain pieces of
text). They tag them in one call, naming a scheme file, and get each one's topics back as
Python objects. Nothing is written to disk. The scheme's `[run]` table decides the provider,
model and method, as it does for the command line.

**Why this priority**: This is the feature. Everything else adjusts it.

**Independent Test**: With a scripted fake model, tag three pieces of text with a scheme
whose `[run]` names a decision model and tiered tagging. Each result holds the expected
leaf topics with confidences and paths, and no file is created.

**Acceptance Scenarios**:

1. **Given** a scheme file with `[run]` naming a model and method, **When** the caller tags
   a list of strings, **Then** each string gets its tags, ordered strongest first, each
   one a leaf of the taxonomy, with the method and model that produced them.
2. **Given** variables with names, labels and value labels, **When** the caller tags them,
   **Then** the model sees the same information the command line would send for those
   variables.
3. **Given** one piece of text, **When** the caller classifies it alone, **Then** they get a
   single result, not a list.
4. **Given** any call, **Then** no file or folder is created.

---

### User Story 2 - Choose the model, provider and method in code (Priority: P1)

The caller overrides the scheme's `[run]` settings for one call: provider, model, method,
`descend_at`, `max_follow` and `keep_at`. They can also pass TOML text instead of a file,
or a scheme already loaded. They can pass their own provider object (for example a fake in
tests, or a host the tool does not know), and the host's address and key.

**Why this priority**: Without overrides the API is only as flexible as the file, and tests
of calling code need a fake model.

**Independent Test**: The same scheme tagged twice, once as the file says and once with
`method="flat"` in the call, records the two methods. The result shows where each setting
came from.

**Acceptance Scenarios**:

1. **Given** a scheme whose `[run]` says `tiered`, **When** the caller passes `method="flat"`,
   **Then** the call tags flat, and the result says the method came from the call.
2. **Given** TOML text rather than a path, **Then** it is loaded with the same checks and
   the same hash as the same text in a file.
3. **Given** no scheme at all, **Then** the bundled scheme is used.
4. **Given** a provider object rather than a name, **Then** it is used as it is, as a
   decision model if it answers choice questions and a chat model otherwise.
5. **Given** a one-tier taxonomy and `method="tiered"`, **Then** it tags flat, and the
   result carries the same note the command line prints.

---

### User Story 3 - Errors a caller can handle (Priority: P2)

Every problem is raised as an exception the caller can catch, with the same wording as the
command line. The API never prints, prompts or exits the process.

**Why this priority**: A library that prints or exits cannot be embedded. These are also
the cases where the command line's exit codes already show what is needed.

**Independent Test**: Each case below raises the named exception, and nothing is written to
stdout or stderr.

**Acceptance Scenarios**:

1. **Given** a broken scheme, **Then** `SchemeError` is raised, listing every problem.
2. **Given** an out-of-range setting (for example `descend_at=1.5`, or `keep_at` with a chat
   model), **Then** `ValueError` is raised, with the command line's wording.
3. **Given** a host that is unreachable or lacks the model, **Then** `ProviderError` is
   raised before anything is tagged.
4. **Given** a model that refuses a question for having too many options, **Then**
   `OptionLimitError` is raised, naming the question and what to change.
5. **Given** a cloud model, **When** the caller has not allowed metadata to leave the
   machine, **Then** a `RemoteModelError` is raised without sending anything. Allowing it
   is one argument, the equivalent of `--yes`.
6. **Given** a variable that still fails after the retries, **Then** the call does not
   raise; that variable's result is marked failed, with the call's last error message.

---

### User Story 4 - Reuse one tagger for many calls (Priority: P3)

A pipeline makes one tagger (scheme, model and settings, checked once) and calls it many
times, for example once per file.

**Why this priority**: It is cheaper than checking the host and settings on every call, but
the one-call function covers the common case.

**Independent Test**: A tagger made once and called twice checks the host once, and gives
the same results as two one-call tags.

**Acceptance Scenarios**:

1. **Given** a tagger, **When** it is called twice, **Then** the host is checked once.
2. **Given** a tagger, **Then** its resolved settings and their sources can be read before
   any call.

### Edge Cases

- **Empty input**: an empty list returns an empty result without contacting the host.
- **Duplicates**: two inputs with the same text or key are tagged separately, and results
  stay in input order.
- **Mixed input**: strings, variables and `variables.jsonl`-style dictionaries may be mixed
  in one call.
- **Long value lists**: very long value lists are cut as on the command line (30 values).
- **Partial refusal**: with a refusal part way through a call, nothing already tagged is
  returned; the exception names the refused question and what to change. The same call
  is refused again in the same way, so there is nothing to resume.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The package MUST offer a documented function that tags a list of inputs with
  a scheme and returns one result per input, in input order.
- **FR-002**: The package MUST offer a function that classifies one input and returns one
  result.
- **FR-003**: The package MUST offer a reusable tagger object holding the scheme, provider
  and resolved settings, which the functions above use.
- **FR-004**: The scheme MAY be given as a file path, as TOML text, as a loaded scheme, or
  left out (the bundled scheme). Text MUST be checked like a file, and give the same hash.
- **FR-005**: An input MAY be plain text, a variable (file, name, label, value labels), or a
  dictionary in the `variables.jsonl` line format. Plain text MUST be sent as the
  variable's label.
- **FR-006**: The provider, model, method, `descend_at`, `max_follow` and `keep_at` MUST be
  resolved as on the command line: the call's argument, else the scheme's `[run]`, else the
  default. The same checks and notes MUST apply.
- **FR-007**: The host's address, API key, timeout, batch size, workers and retries MUST be
  call arguments, with the command line's defaults. None of them may be read from the
  scheme.
- **FR-008**: A provider MAY be given as a name or as an object. An object with `decide` MUST
  be treated as a decision model, and one with `complete` as a chat model.
- **FR-009**: Each result MUST give:
  - the input;
  - its tags (topic id, topic label, confidence), strongest first;
  - for tiered tagging, its path of groups;
  - whether it failed, and if so the call's last error message (errors are not tracked
    per input).
- **FR-010**: Each call MUST also give:
  - the settings used and their sources;
  - any notes;
  - the requests sent per tier;
  - retries;
  - the scheme's name and hash.
- **FR-011**: The API MUST NOT write files, print, prompt or exit. Problems MUST be raised
  as exceptions, with the same wording as the command line.
- **FR-012**: A cloud model MUST NOT be sent anything unless the caller allows it
  explicitly. Otherwise `RemoteModelError` MUST be raised before any request.
- **FR-013**: The host MUST be checked once per tagger, before its first request, and never
  for an empty input.
- **FR-014**: For the same scheme, settings and model replies, the API and the command line
  MUST produce the same tags.
- **FR-015**: Everything public MUST be importable from `topic_tagger` and listed in its
  `__all__`. Names outside that list stay internal.
- **FR-016**: The command line's behaviour and output MUST NOT change.
- **FR-017**: The README MUST gain a "Using it from Python" section with a worked example.
  Every public name MUST have a docstring.

### Key Entities

- **Tagger**: a scheme, a provider and resolved settings, checked once and reusable.
- **Input**: text, a variable, or a `variables.jsonl`-style dictionary.
- **Result**: one input's tags, path, failure and error.
- **Results**: a call's results in input order, with the settings, sources, notes and
  request counts.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A researcher can tag a list of strings with a scheme file in at most 3 lines
  of code (an import, the call, and reading the result).
- **SC-002**: For the fixture variables with a scripted model, the API's tags equal the
  command line's `tags.jsonl` topics for all four combinations: chat or decision model,
  flat or tiered.
- **SC-003**: Calls create no files and write nothing to stdout or stderr. This is checked
  over the whole API test suite.
- **SC-004**: Every error case in User Story 3 raises its documented exception, with no
  network request for the cases caught before tagging.
- **SC-005**: All existing tests pass unchanged, and the command line's output is identical.

## Assumptions

- **Single caller**: the caller runs one call at a time on a tagger; concurrent use of one
  tagger is not promised.
- **No async**: an asynchronous API, streaming partial results, and returning partial
  results after a refusal are out of scope.
- **No resume**: the API does not resume from or write `tags.jsonl`; callers who want an
  output folder use the command line.
- **Prompts unchanged**: plain text is tagged with the scheme's guidance as written; it is
  the scheme author's job to word it for text rather than survey variables if needed.
- **Hosts**: the same two built-in providers (`ollama`, `ollama-decision`); others come in
  as provider objects.
- **Version**: the package version goes from 0.1.0 to 0.2.0, the first with a public API.
