# Feature Specification: Tiered tagging (decision model) for the Topic Tagger

**Feature Branch**: `004-tiered-tagger`
**Created**: 2026-11-13
**Status**: Draft
**Input**: "Upgrade the tagger to allow for decision models. It will be one call for each tier
within the taxonomy, so first classify layer 1 and then within layer 2 and so on. We will use
Ollama's clef model to test. I want to test the outputs during this development, we can do
this ad hoc testing in the adhoc dir." Then: "I want to use this decision model:
https://ollama.com/library/clef. We may need to add that to Ollama."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Tag tier by tier (Priority: P1)

The maintainer runs the Topic Tagger with the tiered method. For each batch of variables,
the model first chooses the topic areas (tier 1) that each variable belongs to. Then, for
each chosen area, it is asked again with only that area's topics (tier 2), and so on down
the taxonomy. Each request shows the model a short list of options instead of every topic
at once.

**Why this priority**: This is the feature. With about 100 topics in one prompt the model
skims; choosing an area first narrows each decision.

**Independent Test**: With a scripted fake model, tag the fixture variables with the tiered
method: tier-1 requests list only areas, tier-2 requests list only one area's topics, and
the stored tags are topics from the areas chosen at tier 1.

**Acceptance Scenarios**:

1. **Given** a two-tier scheme and a batch, **When** tagging tiered, **Then** one request
   picks areas for the batch, then one request per chosen area tags that area's variables
   with that area's topics only.
2. **Given** a variable whose tier-1 reply names two areas above the threshold, **When**
   tagging, **Then** it is asked about at tier 2 in both, and its tags combine both answers.
3. **Given** a variable the model says fits no area, **When** tagging, **Then** it gets the
   scheme's fallback topic, as the flat method would give it.
4. **Given** a failed or invalid reply at any tier, **When** tagging, **Then** the same retry
   ladder as the flat method applies (retries, then one variable at a time, then failed).
5. **Given** no method option, **When** tagging, **Then** the flat method runs as today and
   its output is unchanged.

---

### User Story 2 - See how it decided (Priority: P2)

Each tiered tag records the path it came by (the areas chosen and their confidence), and
the run record and report say which method was used and how many requests each tier took.

**Independent Test**: After a tiered run with the fake model, each `tags.jsonl` record has
`method: "tiered"` and a `path`, and `run.json` has the method and the requests per tier.

**Acceptance Scenarios**:

1. **Given** a tiered run, **When** it ends, **Then** each record carries its path and
   the method, and the summary prints requests per tier.
2. **Given** tags made with the flat method, **When** a tiered run starts on the same folder,
   **Then** they count as out of date and are redone (and vice versa).

---

### User Story 3 - Compare the methods ad hoc (Priority: P2)

During development the maintainer runs both methods on a hand-labelled set of fictional
variables, with Ollama's cloud model, and gets a comparison: how often each method finds
the expected topics, the extra topics it adds, and how many requests and seconds each took.

**Independent Test**: The comparison script runs on two finished output folders and a
labelled set and prints a table, with no model needed.

**Acceptance Scenarios**:

1. **Given** the labelled set, **When** the maintainer runs the ad hoc comparison, **Then**
   it tags the set both ways with the cloud model and prints, per method: top-1 hits, recall
   and precision against the expected topics, requests and time; plus the variables where
   the methods disagree.

### User Story 4 - Use the Clef decision model (Priority: P1)

The maintainer tags tiered with Clef, Cloudflare's decision model served by Ollama. It
does not chat. It takes a state (the variable) and typed questions, and returns a
probability for each. At each tier the tagger asks Clef one yes/no (`noul`) question per
option ("does this variable belong to area X?", then "is it about topic Y?"), and uses the
probabilities as confidences.

**Why this priority**: Clef is the model the maintainer wants to test the tiered method
with. Its fixed, structured answers suit one decision per tier.

**Independent Test**: Against a local fake `/v1/systemone` server, tag the fixture with
`--provider ollama-decision --method tiered`. Each request carries one variable as the
state and one `noul` question per option of that tier. The stored tags are the topics whose
probability passed the keep threshold, inside areas whose probability passed the descend
threshold.

**Acceptance Scenarios**:

1. **Given** Clef is pulled in Ollama, **When** tagging with
   `--provider ollama-decision --model clef:cloud --method tiered`, **Then** each variable is
   tagged by asking tier 1, then tier 2 for each followed area.
2. **Given** a tier with more than 64 options, **When** asking Clef, **Then** the questions are
   split across requests and the answers combined.
3. **Given** Clef is not pulled, **When** the run starts, **Then** it stops before tagging
   and says to run `ollama pull clef:cloud` (or the model given).
4. **Given** the decision provider with `--method flat`, **When** the run starts, **Then** it
   stops with an error: a decision model is used one tier at a time.
5. **Given** a model ending `:cloud` or `-cloud`, **When** the run starts, **Then** it asks
   before sending metadata off the machine (unless `--yes`).

### Edge Cases

- A tier-1 reply names an area that does not exist → the reply fails the check and is retried.
- A tier-2 reply names a topic outside the area it was asked about → fails the check.
- An area chosen at tier 1 gets no topics at tier 2 → the variable keeps the topics from its
  other areas; if none, it is retried alone, then gets the fallback topic only if the model
  says nothing fits, otherwise it is recorded as failed.
- A scheme with one area → tier 1 is skipped (there is nothing to choose).
- Stopping mid-run (Ctrl-C) → variables whose tiers have all finished are stored; the rest
  are done by the next run.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The `tag` command MUST accept `--method flat|tiered`, default `flat`.
- **FR-002**: Tiered tagging MUST ask one request per tier per group of variables: tier 1 for
  the batch over the scheme's areas, then for each chosen area one request over that area's
  children, recursing while children have children.
- **FR-003**: Each request MUST list only the options for its tier, and the reply MUST be
  checked against exactly those options.
- **FR-004**: An area is followed when its tier-1 confidence is at least the descend threshold
  (`--descend-at`, default 0.5), up to `--max-areas` (default 3) per variable; the strongest
  area is always followed.
- **FR-005**: A variable's stored confidence for a topic MUST be its tier-2 confidence; its
  path records each chosen area with its tier-1 confidence.
- **FR-006**: Records MUST store `method`; a record made with another method counts as stale.
- **FR-007**: `run.json` MUST record the method, its settings, and requests per tier; the
  printed summary MUST show them.
- **FR-008**: `--dry-run` with the tiered method MUST print the tier-1 request and one
  example tier-2 request.
- **FR-009**: The flat method's prompts, records and output MUST be unchanged, apart from
  the new `method` field.
- **FR-010**: `docs/formats.md` and the tagger README MUST describe the method, the new
  options and the new fields.
- **FR-012**: A provider `ollama-decision` MUST call Ollama's `POST /v1/systemone` with
  `state` = one variable (name, label, value labels) and `questions` = one `noul` question per
  option, keyed by option id, at most 64 per request.
- **FR-013**: With the decision provider, a leaf is kept when its probability is at least
  `--keep-at` (default 0.3). If no leaf passes, the strongest one is kept, so every tagged
  variable has a topic.
- **FR-014**: A model name ending `:cloud` or `-cloud` MUST count as remote for every
  Ollama provider.
- **FR-015**: The decision provider MUST be refused with `--method flat`.
- **FR-011**: The ad hoc comparison MUST live in `adhoc/` (never committed: it may hold
  real data) and use only fictional variables unless the maintainer chooses otherwise.

### Key Entities

- **Tier**: one level of the taxonomy; the scheme today has two (areas, then topics).
- **Decision path**: the areas chosen for a variable at each tier, with confidences.
- **Labelled set**: fictional variables each with the topics a person expects.

## Success Criteria *(mandatory)*

- **SC-001**: On the labelled set, the tiered method's recall of expected topics is at least
  the flat method's, measured with the same cloud model (decides whether it becomes default;
  either result is a valid outcome of this feature).
- **SC-002**: A tiered run needs at most (1 + max areas) requests per batch on average when
  no request fails.
- **SC-003**: All existing tagger tests pass unchanged except for the added `method` field.
- **SC-005**: Clef tiered tagging stores a tag for every fixture variable with no failures.
- **SC-004**: The comparison of both methods on the labelled set runs with one command and
  finishes in under 10 minutes with the cloud model.

## Assumptions

- The decision model is Clef (https://ollama.com/library/clef, Apache 2.0, 27B). Its cloud
  tag `clef:cloud` is used, since the 18–20 GB local model would be slow on the maintainer's
  Mac. It needs Ollama 0.40.6 or later, sign-in, and a paid plan or credits.
  `ollama pull clef:cloud` adds it. Chat models (e.g. `gpt-oss:20b-cloud`) also work with
  the tiered method, for comparison.
- The scheme format keeps two tiers (areas → topics). The tier walk is written for any
  depth, so a deeper scheme format can follow later without changing it; that format is out
  of scope here.
- The site and `scripts/topics.py` read only `topics` from each record, so the new fields
  need no change there.
- Ad hoc testing uses a new hand-labelled set of fictional variables, so no study metadata
  is sent to a cloud model.
