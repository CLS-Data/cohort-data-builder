# Feature Specification: Search several cohorts at once

**Feature Branch**: `007-multi-cohort-search`

**Created**: 2026-11-26

**Status**: Draft

**Input**: User description: "I would like for people to be able to select and search multiple cohorts at once. We will need to think how the title info stacks, the topic. How the aggregate metrics of variables in the top pannel stacks. Colour coding for each survey. How the variable download page shows selections for multiple cohorts and how the generated code is downloaded. How the tutorial looks."

## Clarifications

### Session 2026-11-26

- Q: Should the cohorts' sweep rows line up on one shared age axis, or each show its own sweeps? → A: One shared age axis; each sweep is placed at the cohort members' age at that sweep (FR-012a, FR-012b).
- Q: How should the code for a multi-cohort selection be downloaded? → A: One zip holding a top-level README and one complete project folder per cohort, each identical to that cohort's single-cohort download (FR-020).
- Q: With several cohorts chosen, how should each topic row lay out its per-cohort counts on the shared age axis? → A: ~~One sub-row per chosen cohort~~ Revised after review: one row per topic and domain, each cell a small bar stacked by cohort in their colours.
- Q (review of the built overview): How should the overview look with several cohorts? → A: One row of bars on the shared age axis, each bar stacked by cohort in proportion and in each cohort's colour; no description text (what a cohort is shows on hovering its toggle); the title never names the chosen cohorts.
- Q: With several cohorts chosen, how should the variable result list be ordered? → A: Grouped by cohort, in catalogue order, each block under a cohort heading with its count; today's order within each cohort.
- Q: On a first visit (no saved choice, no cohort in the page address), which cohorts are chosen? → A: Only the first cohort in the catalogue, as today; more are added from the header.

## User Scenarios & Testing *(mandatory)*

Today the builder shows one cohort at a time, chosen from a drop-down in the header. Every
part of the Variables view (the cohort description, the bar of variables by sweep, the
topic rows, the result list and the Selected panel) describes that one cohort, and the
Selection view downloads one project for it. A researcher comparing, say, smoking in
NCDS, BCS70 and Next Steps has to search each cohort in turn and download three projects
separately.

### User Story 1 - Choose and search several cohorts together (Priority: P1)

A researcher picks two or more cohorts in the header instead of one. One search and one
set of filters then runs across all of them: the result list holds variables from every
chosen cohort, each marked with its cohort's name and colour, and the result count says
how many come from each cohort.

**Why this priority**: It is the feature. Everything else (stacked overview, colour,
download) describes or completes what this makes possible.

**Independent Test**: Choose NCDS and BCS70, search "smok": the list shows matching
variables from both cohorts, each labelled with its cohort, and the count gives a number
per cohort that adds up to the total.

**Acceptance Scenarios**:

1. **Given** one cohort is open, **When** the researcher adds a second cohort in the
   header, **Then** the second cohort loads, the first stays open, and the result list
   now includes both cohorts' variables, with the current search and filters still applied.
2. **Given** two cohorts are chosen, **When** the researcher types a search, **Then** every
   matching variable from either cohort is listed, grouped under a heading per cohort,
   each showing its cohort's short name
   and colour beside its sweep and file.
3. **Given** two cohorts are chosen, **When** the researcher looks at the result count,
   **Then** it gives the total and the number from each cohort.
4. **Given** several cohorts are chosen, **When** the researcher removes one, **Then** its
   variables leave the result list and the overview, and the others are unchanged.
5. **Given** only one cohort is chosen, **When** the researcher uses the builder, **Then** it
   looks and behaves as it does today, apart from the cohort control itself.
6. **Given** a set of chosen cohorts, **When** the researcher copies the page address and
   opens it elsewhere, or reloads, **Then** the same cohorts are chosen.
7. **Given** the same variable name exists in two cohorts, **When** both are listed, **Then**
   they are two separate rows, each with its own cohort, details and selection state.

---

### User Story 2 - The overview stacks by cohort (Priority: P1)

The top panel of the Variables view shows where the matching variables sit in time. With
several cohorts it is still one row of bars, on an axis of age: each bar is stacked by
cohort, in proportion and in each cohort's colour. The topic rows do the same in small, so
the researcher can see at a glance which cohorts measured smoking and when. What a cohort
is (full name, description, size) shows on hovering its toggle in the header.

**Why this priority**: Seeing coverage across cohorts is the main reason to search them
together; without it the researcher only gets a longer list.

**Independent Test**: Choose three cohorts with no search: the overview shows one row of
bars on an age axis, each bar stacked in the three cohorts' colours; opening Topics and the
Health behaviour domain shows each topic as one row of stacked cells.

**Acceptance Scenarios**:

1. **Given** several cohorts are chosen, **When** the researcher hovers a cohort's toggle,
   **Then** they see its full name, description and variable and file counts; there is no
   description text in the overview.
2. **Given** three cohorts are chosen, **When** the overview is drawn, **Then** there is one
   row of bars on one shared age axis: each sweep sits at the cohort members' age at that
   sweep, and each bar is stacked by cohort in proportion to its count, in its colour.
3. **Given** a search is active, **When** the overview is drawn, **Then** each bar shows only
   matching variables; a cohort with no matches has no segment.
4. **Given** several cohorts, **When** the researcher clicks a bar, **Then** the list narrows
   to that age in every cohort (each cohort's sweep there), and the filter chip reads
   "age 11".
5. **Given** several cohorts and Topics open, **When** the researcher looks at a topic,
   **Then** they see its total and one row of cells, each stacked by cohort; a cell narrows
   to that topic at that age; clicking the topic name filters every chosen cohort by it.
6. **Given** a cohort has no topic tags, **When** topics are shown, **Then** a note above
   the topic rows says so, rather than showing zeros as if it had been tagged.

---

### User Story 3 - One selection across cohorts, downloaded together (Priority: P1)

The researcher selects variables from several cohorts and opens the Selection view. Their
selection is grouped by cohort, each group headed with the cohort's name, colour and
count, and within a cohort by sweep or file as today. One download gives a single project
that builds one merged dataset per cohort, because each cohort is a different group of
people with its own identifier and cannot be merged with another.

**Why this priority**: Without it the researcher can search across cohorts but still has
to download each one by hand, which is the problem today.

**Independent Test**: Select three variables from NCDS and two from BCS70, open the
Selection view: two groups headed NCDS (3) and BCS70 (2); download in R: the project
builds one NCDS dataset with three columns plus its identifier and one BCS70 dataset with
two columns plus its identifier.

**Acceptance Scenarios**:

1. **Given** variables from two cohorts are selected, **When** the researcher opens the
   Selected panel or the Selection view, **Then** the variables are grouped by cohort first,
   each group showing the cohort's name, colour and count, then by sweep or file.
2. **Given** variables from two cohorts are selected, **When** the researcher removes a
   cohort from the header, **Then** its selected variables are kept, still shown in the
   Selection view, and still downloaded, until the researcher removes them.
3. **Given** two cohorts each have a variable whose output column is `sex`, **When** the
   column names are checked, **Then** this is not a clash, because they go to different
   datasets; a clash within one cohort is reported against that cohort's variable as today.
4. **Given** variables from two cohorts are selected, **When** the researcher downloads,
   **Then** they get one download holding a top-level README and one folder per cohort;
   each folder is a complete project, the same as that cohort's single-cohort download,
   whose code reads only that cohort's files and writes its own merged dataset, one row
   per person, keyed on that cohort's identifier.
5. **Given** a multi-cohort download, **When** the researcher reads its README, **Then** it
   lists each cohort with its variable count, says where to put each cohort's data and how
   to run each cohort's code, and says plainly that the cohorts are separate datasets that
   are not merged with each other.
6. **Given** variables from only one cohort are selected, **When** the researcher downloads,
   **Then** the project is the same as today's single-cohort project.
7. **Given** a download for several cohorts, **When** the researcher looks at the download
   button, **Then** it says how many variables from how many cohorts it will include.

---

### User Story 4 - A colour for each cohort (Priority: P2)

Each cohort has its own colour, used everywhere that cohort appears: the header control,
the overview lines and rows, each result row, the variable details, the Selected panel,
the Selection view and the tutorial. A researcher learns once that, say, BCS70 is teal and
recognises it across the site.

**Why this priority**: It makes a mixed list readable, but the cohort name is always shown
too, so the feature works without it.

**Independent Test**: Choose all cohorts, then check the header, overview, results,
Selected panel, Selection view and tutorial: each cohort uses the same colour in every
place, in light and dark themes, and its name is always shown beside the colour.

**Acceptance Scenarios**:

1. **Given** any cohort, **When** it appears anywhere on the site, **Then** it has the same
   colour each time and in both themes it has a light and dark version that is the same hue.
2. **Given** a cohort shown in colour, **When** a reader cannot tell colours apart, **Then**
   the cohort is still identified by its name or short name next to the colour.
3. **Given** cohort colours and topic-domain colours on the same page, **When** both are
   shown, **Then** a cohort marker cannot be mistaken for a domain marker (they differ in
   shape or placement, not only colour).
4. **Given** a cohort is added to the site later, **When** it has no colour assigned, **Then**
   it still gets a distinct colour from the site's palette.

---

### User Story 5 - The tutorial covers several cohorts (Priority: P3)

A first-time visitor reads the tutorial and learns that they can search several cohorts
together. Its working panels use two cohorts at once, show the cohort colours and their
key, and its download and run steps explain the one-dataset-per-cohort project.

**Why this priority**: The tutorial explains the builder; it must match it, but it follows
the builder rather than leading it.

**Independent Test**: Open the tutorial: it says in its introduction that cohorts can be
searched together, the search and explore panels show two cohorts in their colours, and
the download step shows a project with a folder or dataset per cohort.

**Acceptance Scenarios**:

1. **Given** the tutorial, **When** the visitor reads the introduction, **Then** it lists the
   cohorts in their colours and says they can be searched one at a time or together.
2. **Given** the Search and Explore steps, **When** the visitor uses their panels, **Then**
   the panels run across two cohorts and show the stacked overview as the builder does.
3. **Given** the Download and Run steps, **When** the visitor reads them, **Then** they show
   what a multi-cohort download contains and how each cohort's code is run.
4. **Given** the builder's cohort colours change, **When** the tutorial is shown, **Then** it
   uses the same colours, from the same source.

### Edge Cases

- All cohorts chosen with no search: the list and overview stay usable; the result list
  keeps drawing in pages as it does now.
- A cohort fails to load: the other chosen cohorts still work; the failed one is named in a
  message with a way to retry, rather than the whole page failing.
- The researcher tries to remove the last chosen cohort: at least one cohort must stay
  chosen; the control does not allow none.
- A saved page address or stored choice names a cohort that is no longer on the site: it is
  dropped and the rest open.
- A sweep or file filter is active for one cohort: the other chosen cohorts show "no
  matches" (their headings stay, with a "Clear filter" link) until it is cleared. This also
  applies to a cohort added while the filter is on. If the filtered cohort is removed, the
  filter is cleared.
- Sweeps of different cohorts at nearly the same age (NCDS 11, BCS70 10): they sit close
  on the age axis but stay separate bars with their own labels; bars never overlap, even
  at phone width.
- A sweep spans a range of ages (e.g. a sweep fielded over two years): it is placed at its
  typical age and its label gives the range.
- Cohorts use different person identifiers (e.g. NSID in Next Steps) and different sweep
  terms ("sweep", "wave", age or year): each cohort keeps its own term and identifier in
  every place it is shown.
- Two cohorts' topic schemes differ in version: a topic is shown for each cohort that has
  it, matched by topic identity; a cohort without that topic shows no count for it.
- "Select all" across several cohorts: the existing upper limit applies to the total, and
  the message says how many from each cohort.
- A selection from an earlier visit, stored per cohort: all stored selections are
  restored, including those of cohorts not currently chosen.
- A phone-width screen with four cohorts chosen: the stacked overview, result rows and
  cohort control fit without sideways scrolling.

## Requirements *(mandatory)*

### Functional Requirements

**Choosing cohorts**

- **FR-001**: The header MUST let the researcher choose any combination of one or more of
  the site's cohorts, and add or remove one in a single action.
- **FR-002**: At least one cohort MUST always be chosen.
- **FR-003**: The chosen cohorts MUST be kept in the page address and remembered for the
  next visit; an address naming cohorts opens exactly those (unknown ones are ignored).
  With neither, only the first cohort in the catalogue is chosen.
- **FR-004**: Cohorts MUST always be listed in one fixed order (the site's catalogue order)
  wherever several are shown, whatever order they were chosen in.
- **FR-005**: With one cohort chosen, the builder MUST behave as it does today.

**Searching and filtering**

- **FR-006**: The search, the measurement-level filter, the topic filter and the
  topic-confidence threshold MUST apply to every chosen cohort at once.
- **FR-007**: Sweep and file filters MUST belong to one cohort, and their filter chips MUST
  name it.
- **FR-008**: Each result row MUST show its cohort's short name and colour; the variable
  details MUST name the cohort in full.
- **FR-009**: The result count MUST give the total and the count per chosen cohort.
- **FR-009a**: With several cohorts chosen, results MUST be grouped by cohort in catalogue
  order, each group under a heading giving the cohort's name, colour and match count, with
  today's order within each group; a chosen cohort with no matches shows its heading and
  "no matches".
- **FR-010**: A variable MUST be identified by cohort, file and name together, so that equal
  names in different cohorts are separate results and separate selections.

**The overview (top panel)**

- **FR-011**: Hovering a cohort's toggle MUST show its full name, description and variable
  and file counts. The overview MUST NOT show description text.
- **FR-012**: With several cohorts the overview MUST show one row of bars, one per age
  column, each stacked by cohort in proportion to its count and in its colour, with the
  total across cohorts.
- **FR-012a**: With two or more cohorts chosen, the sweep rows and the topic rows' sweep
  cells MUST share one age axis: each sweep is placed at the cohort members' age at that
  sweep, and the axis is labelled in years of age. With one cohort chosen, its sweeps are
  spaced as today.
- **FR-012b**: Each sweep MUST be placed by its age (or age range) when it is known. A
  sweep without a known age MUST still be shown, in a clearly labelled "age not known"
  position, never dropped.
- **FR-013**: An age with no matching variables in any cohort MUST still show, as an empty
  bar; a cohort with none at an age simply has no segment there.
- **FR-014**: Each topic and domain row MUST show the total across chosen cohorts and one
  cell per age column, each a small bar stacked by cohort; a click on a cell narrows to
  that topic at that age. With one cohort chosen the cells are shaded as today.
- **FR-015**: A cohort without topic tags MUST be named as untagged above the topic rows,
  not shown as having zero matches.
- **FR-016**: The page title and header MUST NOT change with the chosen cohorts; the footer
  counts MUST sum them.

**Selection and download**

- **FR-017**: The selection MUST hold variables from any number of cohorts, and keep each
  cohort's selected variables when that cohort is removed from the header.
- **FR-018**: The Selected panel and the Selection view MUST group variables by cohort
  first, each group with its name, colour and count, then by sweep or file.
- **FR-019**: Output column names MUST be checked within each cohort only; the same name in
  two cohorts MUST NOT be reported as a clash.
- **FR-020**: One download action MUST produce one file holding a top-level README and
  one folder per cohort in the selection; each folder MUST be a complete project that runs
  on its own and is the same as that cohort's single-cohort download.
- **FR-021**: Each cohort's generated code MUST read only that cohort's files, merge only on
  that cohort's identifier, and write that cohort's own merged dataset; the code MUST NOT
  merge different cohorts with each other.
- **FR-022**: The download options (languages, output format, missing-value handling) MUST
  apply to every cohort in the download.
- **FR-023**: The project README MUST list each cohort in the download, where its data goes,
  how to run its code, and state that cohorts are separate datasets.
- **FR-024**: A download containing one cohort MUST be the same as today's download.
- **FR-025**: The download button MUST state how many variables from how many cohorts it
  will include.

**Colour, accessibility and tutorial**

- **FR-026**: Each cohort MUST have one colour, used in every place the cohort is shown, with
  a version for light and for dark theme; a cohort without an assigned colour MUST get a
  distinct one from the site's palette.
- **FR-027**: Colour MUST never be the only way a cohort is identified: its name or short
  name MUST appear with it.
- **FR-028**: Cohort markers MUST be distinguishable from topic-domain markers by more than
  colour.
- **FR-029**: All new and changed controls MUST be usable by keyboard and screen reader and
  pass the site's existing accessibility checks in light and dark themes and at every
  text size.
- **FR-030**: The tutorial MUST explain choosing several cohorts, show the cohort colours,
  run its working panels across two cohorts, and describe the multi-cohort download.
- **FR-031**: The site MUST still hold and send no study data; nothing in this feature
  adds a server or account.

### Key Entities

- **Cohort**: one study on the site (NCDS, BCS70, Next Steps, MCS): key, short and full
  name, description, person identifier, sweeps and sweep term, files, topic scheme, and now
  a colour.
- **Cohort choice**: the set of cohorts currently searched, in catalogue order; at least one.
- **Selected variable**: a variable picked for download, now identified by cohort, file and
  name, with its output column name.
- **Selection**: all selected variables, across cohorts, grouped by cohort for display and
  download.
- **Multi-cohort download**: the generated project for a selection; per cohort, the code
  and README section that build that cohort's merged dataset.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A researcher can find a topic's variables in three cohorts and download code
  for all three in one session, with one download, in under 3 minutes, against over
  10 minutes today.
- **SC-002**: With every cohort chosen, results for a new search appear in under 1 second
  on a mid-range laptop, once the cohorts have loaded.
- **SC-003**: Adding a cohort to the choice shows its variables in under 3 seconds on a
  typical home connection.
- **SC-004**: In a user test, at least 9 in 10 testers correctly say which cohort a result
  belongs to, and which cohorts measured a chosen topic at a chosen age, from the overview
  alone.
- **SC-005**: For every selection in the test suite, each cohort's dataset from a
  multi-cohort download is identical to the dataset from downloading that cohort on its
  own.
- **SC-006**: Accessibility checks report no serious or critical problems on the changed
  pages in light and dark themes, and nothing scrolls sideways at 390px wide with all
  cohorts chosen.

## Assumptions

- Cohorts are different groups of people, so "searching together" never means merging
  people across cohorts: each cohort is downloaded as its own dataset. Harmonising
  variables across cohorts (making NCDS and BCS70 smoking the same column) is out of scope.
- Every cohort's topics come from the same topic scheme, so topics are matched across
  cohorts by topic identity; differences between scheme versions are handled as in the
  edge cases.
- Selections are already stored per cohort; restoring keeps them and now shows them all.
- The confidence threshold, shading and other interface options stay site-wide, not per
  cohort.
- The cohort colours are chosen by the project, not the researcher.
- Variable details, tag suggestions and the "Suggest tags" issue gain the cohort name but
  otherwise work as today.
- The four cohorts now on the site are the scale to design for; more may be added.
- Each sweep's age at interview is known from the study documentation; where the site's
  data does not yet carry it (e.g. sweeps keyed by year), it is added to the cohort's
  published metadata as part of this feature.
- The top-level README of a multi-cohort download is new; each cohort folder needs no
  change from today's project apart from its name.
