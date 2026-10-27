# Feature Specification: Topic Tagger

**Feature Branch**: `002-topic-tagger`

**Created**: 2026-10-27

**Status**: Draft

## Clarifications

### Session 2026-10-27

- Q: What does the tool read and write? → A: Its own simple generic format. A separate ad hoc
  processing script in this repository converts between that format and the site data.
- Q: How are the final statistics kept? → A: A terminal summary plus a saved report with charts
  that opens in a browser.
- Q: Is agreement with a hand-tagged sample in scope? → A: No, left for later.
- Q: Should the tool know about sweeps? → A: No. An input record may carry any extra fields,
  and the report groups by the one named with an option (default `sweep`).
- Q: Should the tool tag the participant identifier by rule? → A: No. That is study-specific;
  the processing script leaves the identifier out of the export and tags it on merge.
- Q: Should error messages name Ollama? → A: Only when the Ollama provider is chosen; other
  hosts get neutral messages.
- Q: Should the tool fall back to the bundled scheme? → A: No. A scheme file must always be
  chosen; the bundled one is an example to copy.

**Input**: User description: "Data providers will provide the metadata without assigned topics. We need a simple client tool, with simple controls of prompts/topics that can be run locally by a maintainer on their machine with ollama. This tool lives in this repository and must not be entangled into the rest of the repo as ideally it will be usable by other people. I want the client tool to produce some nice visuals and runtime stats plus some final stats on the produced topics."

## Overview

Cohort Data Builder lets researchers browse variables by topic, but only if each variable
carries topic tags. Spec 001 assumed the data providers would supply those tags (001
FR-029). They will not: they supply the variable metadata without topics.

Topic Tagger is a small command-line tool that a maintainer runs on their own machine. It
reads variable metadata, asks a language model running locally through Ollama which topics
each variable belongs to, and writes the tags with a confidence for each. The maintainer
controls the topic scheme and the instructions given to the model by editing one plain
file. While it runs, the tool shows live progress and speed. When it finishes, it reports
how the topics came out.

The tool is self-contained. It lives in this repository but shares no code with the site
and does not depend on it, so other people can use it for their own studies. It reads and
writes a simple, documented format of its own. A separate processing script in this
repository, outside the tool, converts between that format and the site's data: it exports
a cohort's variables for tagging, then merges the tags back.

This feature supersedes 001 FR-029 in one respect only: the project now includes a
topic-tagging tool. Converting dictionaries and deriving missing codes remain out of scope.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Tag a cohort's variables (Priority: P1)

A maintainer has received a cohort's metadata with no topics. They point the tool at it and
choose a model they have in Ollama. The tool tags every variable with one or more topics
from the scheme, each with a confidence between 0 and 1, and writes the result.

**Why this priority**: Without tags, the site's topic features are hidden for the cohort.
This is the core value of the tool.

**Independent Test**: Run the tool on a small fictional cohort with a stand-in model that
gives fixed answers. Confirm every variable gets tags, every tag names a topic in the
scheme, and every confidence is between 0 and 1.

**Acceptance Scenarios**:

1. **Given** untagged metadata and a running Ollama with the chosen model, **When** the
   maintainer runs the tool, **Then** every variable is tagged with one or more scheme
   topics, each with a confidence from 0 to 1, and the result is written.
2. **Given** a model reply that names a topic not in the scheme or gives a confidence
   outside 0–1, **When** it is received, **Then** that reply is rejected and the variables
   in it are retried, never stored as given.
3. **Given** a model reply that leaves some variables out, **When** it is received, **Then**
   only the missing variables are retried.
4. **Given** Ollama is not running or the model is not installed, **When** the tool starts,
   **Then** it stops before any tagging with a message saying which is the problem and how
   to fix it.
5. **Given** the maintainer wants to check the setup first, **When** they ask for a dry run,
   **Then** the tool shows the exact instructions and first batch it would send, and sends
   nothing.

---

### User Story 2 - Stop and carry on (Priority: P1)

Tagging a large cohort takes hours. The maintainer can stop the tool at any point and run it
again later. It carries on from where it stopped, without redoing finished work.

**Why this priority**: BCS70 has about 32,000 variables. A run that had to finish in one
sitting, or that started again after a crash, would be impractical.

**Independent Test**: Stop a run on the fictional cohort part way through, run it again,
and confirm only the untagged variables are sent to the model and the final result matches
an uninterrupted run.

**Acceptance Scenarios**:

1. **Given** a run stopped part way (by the maintainer, a crash or a lost connection),
   **When** the tool is run again, **Then** variables already tagged are skipped and the
   rest are tagged.
2. **Given** finished tags and an edit to the topic scheme or instructions, **When** the tool
   is run again, **Then** the tags made under the old version are treated as out of date and
   redone.
3. **Given** the maintainer wants a fresh start, **When** they ask to retag, **Then** every
   variable is tagged again regardless of existing tags.
4. **Given** the maintainer wants to try things out, **When** they limit the run to some files
   or a number of variables, **Then** only those are tagged.

---

### User Story 3 - Control the topics and the instructions (Priority: P1)

The maintainer decides which topics exist and how the model is told to apply them. Both
live in one plain, commented file that they edit by hand: topic areas, the topics in each,
a description of each topic, and general guidance for the model. The tool starts with the
scheme the site uses today (15 areas, about 100 topics, based on CLOSER Discovery).

**Why this priority**: The quality of the tags depends on the scheme and the guidance. The
maintainer must be able to improve them without changing code.

**Independent Test**: Add a topic and change the guidance in the file, dry-run the tool, and
confirm the new topic and guidance appear in what would be sent. Then introduce a mistake
(a duplicate topic id) and confirm the tool refuses to run and names it.

**Acceptance Scenarios**:

1. **Given** the scheme file, **When** the maintainer edits a topic's description or the
   guidance, **Then** the next run uses the new text.
2. **Given** a scheme file with a mistake (a duplicate id, a malformed id, a topic area with
   no topics, a missing description), **When** the tool starts, **Then** it stops and lists
   each mistake with where it is.
3. **Given** the maintainer has several schemes or instruction variants, **When** they run
   the tool, **Then** they can choose which file to use.

---

### User Story 4 - Watch a run (Priority: P2)

While the tool runs, the maintainer sees what is happening:
- progress through the variables, with time remaining;
- speed, in variables per minute;
- failed and retried requests;
- the topics being assigned, building up as tags arrive.

**Why this priority**: A long run that shows nothing can't be trusted or judged. The live
view tells the maintainer early if the model or the guidance is producing poor tags, so they
can stop and adjust.

**Independent Test**: Run the tool on the fictional cohort with a stand-in model. Confirm the
display shows the counts and speed, and that the final counts match the result written.

**Acceptance Scenarios**:

1. **Given** a run in progress, **When** the maintainer looks at the terminal, **Then** they
   see variables done and left, percentage, elapsed time, estimated time remaining, speed,
   and the number of failed and retried requests, updated at least once a second.
2. **Given** tags arriving, **When** the display updates, **Then** it shows the most-used
   topics and topic areas so far, with counts.
3. **Given** the output is not a live terminal (e.g. redirected to a file), **When** the tool
   runs, **Then** it writes plain periodic progress lines instead of a live display.

---

### User Story 5 - Review the final topic statistics (Priority: P2)

When a run ends, the maintainer gets a summary of how the topics came out, to judge whether
the tags are good enough to publish and what to change in the scheme or guidance.

**Why this priority**: The maintainer needs evidence before publishing machine-assigned
tags. Final statistics show gaps, overused topics and low confidence at a glance.

**Independent Test**: Tag the fictional cohort with a stand-in model whose answers are known,
and confirm each statistic in the summary matches what is expected from those answers.

**Acceptance Scenarios**:

1. **Given** a finished run, **When** the summary is shown, **Then** it includes:
   - variables tagged, skipped and failed;
   - run time and average speed;
   - the model and scheme version used;
   - the number of variables per topic and per topic area;
   - topics never used;
   - the spread of confidences;
   - the share of variables tagged only below the site's default threshold (50%);
   - the average number of topics per variable;
   - counts per data file, and per value of the grouping field (default `sweep`).
2. **Given** a finished run, **When** the maintainer wants to keep or share the statistics,
   **Then** a self-contained report file is saved beside the output, which opens in a
   browser without a network connection and shows the same statistics with charts:
   - variables per topic area, and per topic within each area;
   - the spread of confidences;
   - topic areas by the grouping field, when the variables have it;
   - speed over the run.
3. **Given** several runs, **When** the maintainer opens their reports, **Then** each names
   its run (date, model, scheme version, settings), so they can be compared side by side.

---

### User Story 6 - Publish the tags on the site (Priority: P2)

A maintainer turns a cohort supplied without topics into site data with topics. They export
the cohort's variables into the tool's input format, tag them, and merge the tags and the
scheme back into the cohort's site data. The site's data checks then pass, and the site
shows the topics.

**Why this priority**: The tags are only useful to researchers once they are on the site.
Keeping this step outside the tool keeps the tool reusable.

**Independent Test**: Take the fictional cohort without topics, export it, tag it with a
stand-in model, and merge it back. Confirm the site's data checks pass and the topic
features appear on the site for that cohort.

**Acceptance Scenarios**:

1. **Given** a cohort folder in the site data format without topics, **When** the maintainer
   exports it, **Then** they get the tool's input file with every variable except the
   participant identifier: file, name, label, value labels and sweep.
2. **Given** the tool's output for that cohort, **When** the maintainer merges it, **Then**:
   - the scheme is written into the cohort's manifest;
   - the participant identifier gets the scheme's identifier topic (default `identifiers`)
     at 100%, without the model;
   - each variable's tags go into its dictionary entry, as `[topic id, confidence]`;
   - the index rows get the same tags as `[topic number, percent]`, strongest first;
   - nothing else in the cohort's data changes.
3. **Given** tags for variables that are not in the cohort, or variables with no tags,
   **When** the merge runs, **Then** it lists them and does not stop. Untagged variables are
   left without topics.
4. **Given** a merge has been done, **When** the site's data checks run, **Then** they pass
   with no topic errors.

---

### Edge Cases

- A variable has no label: it is still sent, with its name and any value labels; if the
  model cannot place it, it gets the scheme's catch-all topic ("other") at low confidence.
- The model is slow or a request hangs: each request has a time limit, after which it is
  retried, and a run never stalls indefinitely on one request.
- The model keeps failing on the same batch: after a set number of retries the variables are
  tried one at a time; any still failing are recorded as failed, listed at the end, and
  retried on the next run.
- Two runs are started on the same cohort at once: the second refuses to start rather than
  corrupting the tags.
- The chosen model runs on Ollama's servers ("cloud" models), not the maintainer's machine:
  the tool says before starting that variable names and labels will leave the machine and
  asks for confirmation, unless told explicitly to proceed. No study data is ever sent, only
  metadata.
- The metadata contains thousands of value labels for one variable: only as many as fit a
  set limit are sent, so one variable cannot overflow a request.
- A tagged result is stopped mid-write: the stored tags are never left half-written; at most
  the batches in flight are lost.

## Requirements *(mandatory)*

### Functional Requirements

**Input and output**

- **FR-001**: The tool MUST read variable metadata in its own simple, documented format: one
  record per variable, with data file, name, label and value labels, plus any other fields,
  which it keeps for grouping in the statistics and never sends to the model. It MUST NOT
  read the site's data folder.
- **FR-002**: The tool MUST write, in its own documented format, every variable's topics with
  a confidence (0–1) for each, together with the model and the scheme version that produced
  them and when. It MUST also write the scheme used.
- **FR-003**: Tags from the tool, merged by the processing script (FR-026), MUST pass the
  site's supplied-data checks (001 rules D4 and D7).
- **FR-004**: The tool MUST NOT send or require any study data; only variable metadata
  (names, labels, value labels, file names).

**Tagging**

- **FR-005**: The tool MUST tag using a model served by Ollama at an address the maintainer
  can set (by default the local machine), with the model chosen by the maintainer.
- **FR-006**: The tool MUST accept only topics from the scheme and confidences from 0 to 1,
  rejecting and retrying anything else.
- **FR-007**: The tool MUST send every input variable to the model; it MUST NOT contain
  study-specific rules. (Tagging a study's identifier by rule is the processing script's
  job, FR-026.)
- **FR-008**: The tool MUST send variables in batches, with the batch size and the number of
  requests in flight set by the maintainer, and MUST retry failed requests a set number of
  times before trying variables one at a time.
- **FR-009**: The tool MUST provide a dry run that shows what would be sent and sends
  nothing.
- **FR-010**: The tool MUST check before starting that the host is reachable and the model
  exists, stopping with a clear message otherwise. Messages name the host and how to fix
  the problem only for the provider chosen (e.g. `ollama pull` for Ollama), and are neutral
  for any other host.
- **FR-011**: The tool MUST warn and ask for confirmation before sending metadata to a model
  that does not run on the maintainer's machine, unless told explicitly to proceed.

**Resuming**

- **FR-012**: The tool MUST save tags as it goes, so that stopping at any point loses at most
  the requests in flight.
- **FR-013**: The tool MUST skip variables already tagged with the current scheme and
  instructions, and redo those tagged with an earlier version.
- **FR-014**: The tool MUST let the maintainer retag everything, or limit a run to chosen
  files or a number of variables.
- **FR-015**: The tool MUST refuse to start a second run on the same output while one is in
  progress.

**Controls**

- **FR-016**: The topic scheme (topic areas, topics, ids, labels, descriptions) and the
  guidance given to the model MUST live in one plain, commented, hand-editable file, which
  the maintainer can choose per run.
- **FR-017**: The tool MUST check the scheme file before tagging and list every mistake
  (duplicate or malformed ids, empty topic areas, missing labels or descriptions) with its
  location.
- **FR-018**: The tool MUST ship with the scheme the site uses today as an example, which the
  maintainer copies to start their own. It MUST NOT use any scheme the maintainer has not
  chosen: the scheme file is a required argument.
- **FR-019**: All other run settings (model, address, batch size, requests in flight,
  retries, limits, grouping field) MUST have sensible defaults and be shown by the tool's
  help.

**Visuals and statistics**

- **FR-020**: During a run, the tool MUST show progress, elapsed and remaining time, speed,
  failures and retries, and the leading topics and topic areas so far, updated at least once
  a second; with no live terminal, it MUST write plain progress lines instead.
- **FR-021**: At the end of a run (including a run stopped by the maintainer), the tool MUST
  show the final statistics listed in User Story 5, scenario 1, and save them as a
  self-contained report file with charts that opens in a browser without a network
  connection (User Story 5, scenarios 2–3).
- **FR-022**: The tool MUST list the variables that could not be tagged.

**Independence**

- **FR-023**: The tool MUST be self-contained within its own folder of the repository, with
  its own setup, tests, documentation and dependencies. It MUST NOT import from, or be
  imported by, the site or the site's tests.
- **FR-024**: The tool MUST be usable by someone who has never seen the rest of this
  repository, following its own documentation alone.
- **FR-025**: The tool's tests MUST run without Ollama, using a stand-in model, and MUST run
  in CI.

**Processing script (in this repository, outside the tool)**

- **FR-026**: A processing script MUST export a cohort from the site data format (without
  topics) into the tool's input format, and merge the tool's output and scheme back into the
  cohort's site data, as described in User Story 6. The export leaves out the cohort's
  participant identifier; the merge tags it with the scheme's identifier topic (an option,
  default `identifiers`, which must exist in the scheme) at 100%.
- **FR-027**: The merge MUST change only the topic fields: the manifest's `topics`, each
  dictionary entry's `topics`, and element 5 of each index row. It MUST report tags for
  unknown variables and variables left untagged, without stopping.
- **FR-028**: The processing script MAY read the tool's documented formats but MUST NOT import
  the tool's code, so each can change without the other.

### Key Entities

- **Variable metadata**: One variable to tag: data file, name, label, value labels, and any
  other fields (such as sweep), kept only for grouping in the statistics.
- **Topic scheme**: Topic areas, each with topics (id, label, description), plus the
  guidance given to the model; named and versioned. Its version changes whenever its content
  does.
- **Topic tag**: One variable's assignment to one topic with a confidence (0–1).
- **Tag record**: All of one variable's tags, with the model, scheme version and time that
  produced them.
- **Run**: One invocation: settings, start and end time, counts of tagged, skipped, failed
  and retried, and speed.
- **Run statistics**: The end-of-run summary of how the topics came out, also saved as a
  report.
- **Tool input / output**: The tool's own documented formats: variables in, tag records and
  scheme out. The processing script is the only link between these and the site data.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A maintainer new to the tool can tag a small cohort (a few hundred variables)
  within 15 minutes of reading its documentation, given Ollama and a model already installed.
- **SC-002**: A run stopped at any point and restarted produces the same set of tagged
  variables as an uninterrupted run, and repeats no more than the batches that were in
  flight when it stopped.
- **SC-003**: 100% of stored tags name a topic in the scheme with a confidence from 0 to 1;
  tags from the tool, added to site data, pass the site's data checks with no topic errors.
- **SC-004**: The live display updates at least once a second, and its final counts match
  the stored result exactly.
- **SC-005**: Changing the scheme or the guidance requires editing only the scheme file, with
  no code change.
- **SC-006**: The tool's folder can be copied out of this repository and used on its own,
  with its tests passing, without any other file from the repository.
- **SC-007**: Every statistic in the final summary and the report is verified against a known
  stand-in run.
- **SC-008**: A cohort supplied without topics can be exported, tagged and merged with three
  commands, after which the site's data checks pass and the cohort's topic features appear.

## Assumptions

- The maintainer has Ollama installed and a suitable model pulled, and runs the tool on a
  machine able to serve it; installing Ollama and choosing hardware are outside this
  feature. Which model works best is the maintainer's choice; the tool recommends a default.
- Machine-assigned tags are a discovery aid, shown with their confidence, not an
  authoritative classification (as in spec 001).
- The data providers supply metadata in the documented site data format minus the topic
  fields (`topics` in the manifest, topic lists in the index and dictionaries).
- The tool is run occasionally (when a cohort arrives or the scheme changes), by one
  maintainer at a time, not on every change or in CI.
- Speed depends on the model and hardware; no speed target is set beyond the tool reporting
  it accurately.
- The PoC's tagger (`PoC/enrich/`, `PoC/schema/topics.yaml`) is the reference for behaviour
  this specification does not state, as the PoC was for spec 001.
- Measuring agreement with a hand-tagged sample is out of scope for this feature. Tag quality
  is judged from the statistics and by inspection. It is a candidate follow-up once a
  hand-tagged sample exists.
