# Feature Specification: A configurable classification pipeline for the Topic Tagger

**Feature Branch**: `005-configurable-classifier`

**Created**: 2026-11-16

**Status**: Draft

**Input**: User description: "Ultimately, we are building a classification pipeline controlled
by a prompt in a TOML file. I want this to be flexible. A user should be able to choose to
use a system one (decision) model or an LLM. The user should be able to define any taxonomy
of classifications, whether it is 1 tier, 2 tiers or 3 tiers, and it should be controllable
as to whether it is done flat or through iterative inference through each tier. Decision
models have a limit on the number of classes per question (26), which is fine as long as the
options asked about at once are under it."

## Context

Feature 004 added tiered tagging and decision models, but with three fixed limits:

- a taxonomy is always two tiers (topic areas, then topics);
- a decision model can only tag tiered;
- how a run classifies is chosen only on the command line.

This feature removes those limits. One TOML file describes the whole classification:
- the taxonomy, of one, two or three tiers;
- the prompt;
- how to classify: which kind of model, flat or tier by tier, and the thresholds.

Any combination works, as long as each question stays within what the model can answer.

Terms used here:
- **Category**: any entry in the taxonomy.
- **Leaf**: a category with no categories under it. Leaves are what variables are tagged
  with.
- **Group**: a category with categories under it.
- **Flat**: one question offers every leaf at once.
- **Tiered**: the top tier's groups are offered first, then the categories inside each group
  chosen, and so on down to the leaves.
- **LLM**: a chat model that answers in text.
- **Decision model**: a model, such as Clef, that answers a choice question with a
  probability for each option.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Any taxonomy of one to three tiers (Priority: P1)

A researcher writes a taxonomy file for their own purpose. It might be a single list of 12
categories, the two-tier CLOSER scheme, or a three-tier scheme (domain, then topic, then
subtopic). They run the tagger with it, and every variable is tagged with leaves from that
taxonomy.

**Why this priority**: The taxonomy is what the user owns. Without free depth, nothing else
in this feature matters: today only two tiers can be described.

**Independent Test**: Load a one-tier, a two-tier and a three-tier fixture file and tag the
fixture variables with a scripted fake model. Each run stores only that file's leaves. An
existing feature-004 scheme file still loads and tags exactly as before.

**Acceptance Scenarios**:

1. **Given** a one-tier file (a plain list of categories), **When** it is tagged, **Then**
   every stored tag is one of those categories.
2. **Given** a three-tier file, **When** it is tagged tier by tier, **Then** each stored tag
   is a tier-3 leaf, and its record shows the tier-1 and tier-2 categories it came through.
3. **Given** an existing two-tier scheme in the feature-004 format (areas holding topics),
   **When** it is loaded, **Then** it is accepted unchanged, and existing tags made with it
   are not out of date.
4. **Given** a file with mistakes, **When** it is loaded, **Then** every mistake is reported
   with its location before any request is made. Mistakes include:
   - more than three tiers;
   - a repeated id;
   - a group with no categories;
   - a fallback that names no leaf.

---

### User Story 2 - Choose flat or tiered, with either kind of model (Priority: P1)

The user chooses how to classify:
- with an LLM or a decision model;
- flat or tier by tier.

All four combinations are allowed. The tagger assumes no limit on the number of options in a
question. Some models have one: Clef takes at most 26 options per question, and other models
will differ. When a model refuses a question for having too many options, the run stops with
a clear error instead of failing variable by variable.

**Why this priority**: This is the flexibility asked for. It also removes 004's rule that a
decision model can only tag tiered.

**Independent Test**: With scripted fake models, run a two-tier fixture taxonomy four ways:
LLM flat, LLM tiered, decision flat and decision tiered. Each run stores tags. Each record
says which method made it. The decision-model runs ask choice questions with the expected
options.

**Acceptance Scenarios**:

1. **Given** a decision model and flat, **When** tagging, **Then**:
   - one choice question per variable offers every leaf;
   - the answer's probabilities become the tags' confidences.
2. **Given** a model that refuses a question because it has too many options, **When** that
   question is first asked, **Then** the run stops. The error:
   - names the question: the whole flat list, the top tier, or a named group;
   - gives its number of options;
   - repeats the model's own message;
   - suggests tagging tiered, or splitting the group.
3. **Given** a run stopped by that error, **When** the user fixes the taxonomy or the method
   and runs again, **Then** tags already stored are kept, and the run carries on from there.
4. **Given** a model that accepts the question, **When** tagging, **Then** the number of
   options never stops the run, however many there are.
5. **Given** a one-tier taxonomy, **When** tagging tiered, **Then** it behaves as flat. There
   is only one tier to ask about, and the run says so.

---

### User Story 3 - The TOML file controls the run (Priority: P2)

Besides the taxonomy and the prompt, the file can set how the run classifies:
- the kind of model and the model's name;
- flat or tiered;
- the threshold for following a category down to the next tier;
- the most categories to follow at each tier;
- the threshold for keeping a leaf.

A run with only the file and the variables does what the file says. Command-line options
still override each setting for one run.

**Why this priority**: The user wants one file that defines the pipeline, so a
classification can be shared and repeated. The command line already covers each setting,
so this is convenience and reproducibility, not new capability.

**Independent Test**:
1. Tag with a fixture file whose run section names a fake decision model, tiered, with
   thresholds. The run record shows those settings.
2. Repeat with `--method flat` on the command line. The run record shows flat, and that it
   came from the command line.

**Acceptance Scenarios**:

1. **Given** a file with a run section, **When** tagging with no method or model options,
   **Then** the file's settings are used and written to the run record. The end-of-run
   summary shows the method, the kind of model, the model and the number of tiers.
2. **Given** a file with a run section and a command-line option for the same setting,
   **When** tagging, **Then** the command line wins for that run, and the run record notes
   it.
3. **Given** a file with no run section, **When** tagging, **Then** today's defaults apply:
   - an LLM;
   - flat for an LLM, tiered for a decision model;
   - today's thresholds.
4. **Given** an unknown setting or an impossible value in the run section, **When** loading,
   **Then** the file is refused with its location. Impossible values include a threshold
   outside 0–1, or a negative number of categories to follow (0 means no cap, as in 004).

---

### User Story 4 - The prompt shapes each question (Priority: P2)

The file's prompt (the guidance) is given to whichever model runs.
- An LLM gets it as its instructions.
- A decision model gets it as the context of each choice question.

The user can also word the question asked at each tier, for example:
- "Which domain is this variable about?";
- "Which subtopic within *Health*?".

**Why this priority**: The prompt is how the user controls the classification without code.
Tier wording matters most for decision models, which see only the question and the options.

**Independent Test**: With a fixture file holding a guidance text and a question for tier 2,
a dry run shows the guidance and the tier-2 question in the request bodies for both kinds of
model.

**Acceptance Scenarios**:

1. **Given** a file with guidance, **When** tagging with either kind of model, **Then** the
   guidance is part of every request.
2. **Given** a file with a question for a tier, **When** tagging tiered, **Then** that tier's
   requests use it. Tiers without one use the built-in wording, as in 004.
3. **Given** a change to the guidance, a question or any category's text, **When** a run
   starts on an existing output folder, **Then** the affected tags are out of date and are
   redone, as today.

---

### User Story 5 - See what each run will ask, before paying for it (Priority: P3)

Before tagging, the user checks a taxonomy and its settings: how many tiers, how many leaves,
and the largest question each method would ask, so they can compare it with their model's
limit. A dry run shows an example request at every tier.

**Why this priority**: It saves wasted runs, but a run that hits a model's limit already
stops at the first refusal, keeping what it tagged.

**Independent Test**: Checking the three-tier fixture prints its tier counts, and the largest
option count flat and at each tier, without any model.

**Acceptance Scenarios**:

1. **Given** a taxonomy, **When** the user checks it, **Then** they see:
   - the number of tiers;
   - the number of categories per tier;
   - the largest set of options asked at once, flat and at each tier, and where it is.
2. **Given** a three-tier taxonomy, **When** the user dry-runs tiered, **Then** an example
   request is shown for each of the three tiers, and nothing is sent.

### Edge Cases

- **Uneven depth**: some groups at tier 2 hold tier-3 categories and others are leaves
  already. Tiered tagging stops descending at a leaf. Flat tagging offers every leaf, at
  whatever tier it sits.
- **A group with one category**: no question is asked. The walk passes straight through, as
  in 004.
- **Nothing passes the threshold at a tier**: the strongest option is still followed, as in
  004, so every variable reaches a leaf or the fallback.
- **The fallback**:
  - In tiered runs it is offered at the top tier as an exit, as in 004, wherever it sits in
    the taxonomy.
  - In flat runs it is one of the leaves.
  - It counts as one of the options wherever it is offered.
- **Only some questions are too big**: in a tiered run, one group may exceed a model's
  limit while the others fit. The run stops when that group is first asked about, naming
  it. Fixing that group is enough.
- **Other errors**: a refusal that is not about the number of options (a timeout, a bad
  reply) keeps the existing retry ladder. Only a too-many-options refusal stops the run,
  because retrying it can never succeed.
- **One option**: no question is asked (above). A one-leaf taxonomy is refused when loaded.
- **Several categories followed at a tier**: a variable can end with leaves from several
  branches. All are stored, as in 004.
- **The same leaf id under two groups**: refused at load. Ids are what is stored, so they
  must be unique across the whole taxonomy.
- **Changing only the run settings** (model, thresholds) does not make existing tags out of
  date. Changing the method, the taxonomy or the prompt does, as today.

## Requirements *(mandatory)*

### Functional Requirements

**Taxonomy**

- **FR-001**: A taxonomy file MUST be able to describe one, two or three tiers of
  categories. Each category has:
  - an id;
  - a label;
  - an optional description;
  - optional categories under it.
- **FR-002**: A taxonomy MAY be uneven. A category at any tier with nothing under it is a
  leaf.
- **FR-003**: The tagger MUST refuse to load a file that has any of these:
  - more than three tiers;
  - a repeated id anywhere in the taxonomy;
  - an id in the wrong form;
  - a missing label;
  - a group with no categories;
  - fewer than two leaves;
  - a fallback that is not a leaf.

  It MUST list every problem with its location, before any request is made.
- **FR-004**: Scheme files in the feature-004 format MUST still load and mean the same. Their
  tags MUST NOT become out of date just because the file format grew.
- **FR-005**: Stored tags MUST be leaf ids. For tiered runs, each record MUST also store the
  path: the categories chosen at each tier above the leaf, with their confidences.

**Methods and models**

- **FR-006**: The user MUST be able to choose an LLM or a decision model, and flat or tiered,
  in any combination.
- **FR-007**: Flat MUST ask one question per batch for an LLM, or one per variable for a
  decision model, offering every leaf.
- **FR-008**: Tiered MUST ask, at each tier, only about the categories directly under the
  categories chosen at the tier above. It MUST continue until each followed branch reaches a
  leaf.
- **FR-009**: The tagger MUST NOT build in any limit on the number of options in a
  question, for either kind of model. The limit is the model's.
  - When a model refuses a question because it has too many options, the run MUST stop at
    once, without retrying it or splitting the batch.
  - The error MUST say:
    - which question it was (the whole flat list, the top tier, or a named group);
    - its number of options;
    - the model's own message;
    - that tagging tiered, or splitting the group, may fit.
  - Tags stored before the stop MUST be kept, so the next run resumes.
  - The run MUST exit with a distinct error status, and its run record MUST say why it
    stopped.
- **FR-010**: A one-tier taxonomy tagged tiered MUST behave as flat, and the run MUST say so.
- **FR-011**: The following MUST apply the same way at every tier, for both kinds of model:
  - the threshold to follow a category down;
  - the most categories to follow per tier.

  The threshold to keep a leaf MUST apply to decision models, as in 004. An LLM's leaves are
  kept as it states them.
- **FR-012**: The fallback category MUST be offered as an exit at the top tier in tiered
  runs, and as a leaf in flat runs. It MUST count as one of the options.

**Configuration**

- **FR-013**: The taxonomy file MAY contain a run section. It sets:
  - the kind of model;
  - the model name;
  - the method;
  - the three thresholds of FR-011.

  Without it, today's defaults apply.
- **FR-014**: A command-line option MUST override the file's setting of the same name for
  that run only. The run record MUST show:
  - the settings used;
  - for each, whether it came from the file, the command line or the default.
- **FR-015**: Unknown settings and impossible values in the run section MUST be refused when
  the file is loaded, with their location.
- **FR-016**: The file's guidance MUST be given to every request, for both kinds of model.
- **FR-017**: The file MAY word the question for each tier. Tiers without wording MUST use the
  built-in question.
- **FR-018**: Tags MUST count as out of date when any of these changes:
  - the method;
  - the taxonomy (ids, labels, descriptions, structure);
  - the guidance;
  - a tier's question.

  Changing only the model, the thresholds or other run settings MUST NOT, as today.

**Visibility**

- **FR-019**: The user MUST be able to check a taxonomy without a model. The check shows:
  - the number of tiers;
  - the number of categories per tier;
  - the number of options in the largest question, flat and at each tier, and which group
    it is.
- **FR-020**: A dry run MUST show one example request for each tier the method would ask,
  for the chosen kind of model, without sending anything.
- **FR-021**: The run record and summary MUST report:
  - the method;
  - the kind of model;
  - the number of tiers;
  - the requests made at each tier.
- **FR-022**: The format of the taxonomy file, the run section and the stored records MUST be
  documented alongside the tool. A bundled example of each depth MUST be provided.

### Key Entities

- **Taxonomy**: a named, versioned tree of categories, one to three tiers deep, with one
  fallback leaf. It is what tags are drawn from.
- **Category**: an id, a label, an optional description and optional child categories. It is
  a group when it has children, and a leaf when it has none.
- **Guidance**: the user's instructions, given to the model with every question.
- **Tier question**: optional wording of the question asked at one tier.
- **Run settings**: the kind of model and its name, the method, and the three thresholds.
  They are set by the file, the command line or the defaults.
- **Tag record**: one variable's leaf tags with confidences, plus the method, and for tiered
  runs the path through the tiers.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can tag the same variables with a 1-, 2- and 3-tier taxonomy, each flat
  and tiered, with each kind of model where it fits. That is 12 configurations, all made only
  by editing the TOML file or passing options, with no code change.
- **SC-002**: When a model refuses a question as too big, the run stops at the first such
  refusal, with a message that names the question and its size. No variable is marked
  failed for it, and no request is retried for it. Re-running after a fix loses no tags.
- **SC-003**: Every existing feature-004 scheme file and output folder keeps working.
  Re-running on a finished folder with the same settings redoes no variables.
- **SC-004**: A user who has not seen the tool before can write a working three-tier
  taxonomy from the documentation and bundled examples in under 15 minutes.
- **SC-005**: Two runs from the same file and variables, with the same model, record
  identical settings and method, so a classification can be repeated from the file alone.

## Assumptions

- **Depth**: "1, 2 or 3 tiers" is a ceiling the user chose. Deeper taxonomies are refused,
  not silently cut. The code need not be specific to three, but only up to three is tested
  and supported.
- **Option limits** differ by model, and are not known in advance. Clef takes 26 per
  question (found in 004), but that is Clef's limit, not the tagger's. The tagger relies on
  the model's service to refuse a question that is too big, with a recognisable error. The
  plan will find out how each supported service reports this.
  - A model that silently ignores options beyond its limit cannot be detected this way.
  - The user can see each question's size with the check in story 5.
- **Batching**: flat with a decision model asks one variable per request. Decision models
  answer one choice per request (004, research R11).
- **Defaults**: LLM flat when nothing is set, decision model tiered, and the 004 thresholds
  (follow at 0.5, at most 3 categories per tier, keep leaves at 0.3 for decision models).
  The comparison in 004 has not yet chosen better ones (task T027).
- **Run section scope**: the run section holds classification settings only. Provider
  credentials, worker counts, retries and output paths stay on the command line, so a shared
  file carries no secrets or machine-specific choices.
- **Format**: the 004 file format (`domains` holding `topics`) remains valid. The general
  nested form is added beside it, not instead of it.
- **Out of scope**:
  - more than three tiers;
  - different thresholds per tier;
  - splitting an oversized question into several smaller ones;
  - new model providers;
  - any change to the website, which keeps reading leaf tags as today.
- This remains a standalone tool in `tools/topic-tagger/`, under the same rules as features
  002 and 004.
