# Feature Specification: Cohort Data Builder

**Feature Branch**: `001-cohort-data-builder`

**Created**: 2026-10-26

**Status**: Draft

**Input**: User description: "in this directory we have a directory called PoC. This is a PoC I have developed for a survey data search tool and boiler plate code builder. I would like you to review the entire directory to gain an understanding of what it is I would like to develop."

## Overview

Researchers using UK longitudinal cohort studies (initially the 1970 British Cohort Study,
BCS70, and Next Steps) face tens of thousands of variables spread across dozens of data
files and many collection rounds ("sweeps"). Finding the right variables, and then writing
the code to pull them out of each file and join them into one analysis file, is slow and
error-prone.

Cohort Data Builder is a public website that lets a researcher search a cohort's published
data dictionaries, pick the variables they need, and download a small, ready-to-run R and/or
Python project. The project reads those variables from the researcher's own copy of the data
(obtained separately from the UK Data Service) and merges them into one file, one row per
study participant. The site and the download contain **no study data**: only the metadata
from the published data dictionaries.

This specification describes the production version of the existing proof of concept in
`PoC/`, which demonstrates the intended behaviour.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Find variables in a cohort (Priority: P1)

A researcher chooses a cohort and searches its variables by name or by words in the label.
They narrow the results by sweep, by data file, by measurement level and by topic, and open
any variable to see its value labels, missing-value codes, source file and the same question
asked at other sweeps.

**Why this priority**: Discovery is the core value and is useful on its own: even without a
download, researchers can find out what was measured, when, and in which file.

**Independent Test**: Load the site, choose BCS70, search for "smoke", filter to one sweep,
open a result and confirm its value labels and file are shown.

**Acceptance Scenarios**:

1. **Given** the site is open, **When** the researcher picks a cohort, **Then** the page
   shows the cohort's name and description, its total variable and file counts, and a
   count of variables per sweep, in time order.
2. **Given** a cohort is open, **When** the researcher types part of a variable name or a
   word from a label, **Then** every variable whose name or label contains that text
   (ignoring case) is listed, with the matching text highlighted.
3. **Given** a search result list, **When** the researcher clicks a sweep in the per-sweep
   overview, **Then** only variables from that sweep are listed, and clicking it again
   removes that filter.
4. **Given** results are listed, **When** the researcher filters by measurement level or by
   data file, **Then** only matching variables are listed and each active filter is shown
   as a removable chip, with a single "Clear" action removing all filters.
5. **Given** a variable in the list, **When** the researcher opens its details, **Then**
   they see its value labels (answers first, missing-value codes separately), its source
   file and description, its position and measurement level, its topic tags with
   confidence, and links to variables with the identical label at other sweeps.
6. **Given** a search matches no variables, **When** the list is shown, **Then** a "no
   variables match" message is displayed with an option to clear the filters.
7. **Given** a sweep with zero matching variables, **When** the per-sweep overview is
   drawn, **Then** that sweep is still shown, marked as empty.

---

### User Story 2 - Build a selection (Priority: P1)

While searching, the researcher adds variables to a selection, which stays visible beside the
results. They can add one variable at a time, a range of results, or all current results, and
remove any of them. The selection is remembered if they leave and return.

**Why this priority**: The selection is what turns discovery into a download; without it
there is nothing to generate.

**Independent Test**: Add five variables from two files, reload the page, and confirm the
same five are still selected for that cohort.

**Acceptance Scenarios**:

1. **Given** a result list, **When** the researcher clicks a variable, **Then** it is added
   to the selection (or removed if already selected) and the selected count updates.
2. **Given** a result list, **When** the researcher selects one variable and then
   range-selects another, **Then** every selectable variable between them is added (or
   removed, matching the clicked variable's new state), and the number changed is announced.
3. **Given** a filtered list of at most 500 selectable variables, **When** the researcher
   chooses "Select all", **Then** all of them are added; when all are already selected the
   action offers to remove them instead.
4. **Given** a cohort's participant identifier variable, **When** it appears in results,
   **Then** it is shown as always included and cannot be added or removed separately.
5. **Given** a data file that lacks the participant identifier, **When** its variables
   appear in results, **Then** they cannot be selected and the reason is shown.
6. **Given** a selection, **When** the researcher reloads the page or returns later on the
   same browser, **Then** the selection for that cohort is restored, dropping any variables
   that no longer exist in the current metadata.
7. **Given** a selection of hundreds of variables, **When** the researcher views the
   selection panel, **Then** it is grouped by sweep or by file (their choice), can be
   filtered by text, and clearing it requires a confirming second action.

---

### User Story 3 - Download a ready-to-run merge project (Priority: P1)

The researcher reviews the output columns, renames any that clash, chooses R, Python or both,
an output file type (CSV, Stata or SPSS) and whether missing-value codes become missing (NA),
then downloads a zip file containing a small project that reads their own data files and
writes the merged result.

**Why this priority**: The generated code is the tool's main time saving and the reason it
exists beyond a dictionary browser.

**Independent Test**: Select variables from at least two files (one with one row per
person, one with several), download the project, place fabricated data files in its data
folder in each supported input format, run both the R and the Python versions, and confirm
they produce identical, correct output.

**Acceptance Scenarios**:

1. **Given** a selection, **When** the researcher opens the review, **Then** they see every
   output column in output order, starting with the participant identifier, each with its
   label, source variable and file, and the list of data files they will need with a link to
   where to obtain them.
2. **Given** two selected variables from different files share a name, **When** they are
   added, **Then** the second is automatically given a distinct output name (qualified by
   its sweep), and the researcher can rename any column.
3. **Given** an output column name that is invalid, duplicates another (ignoring case),
   equals the identifier, or breaks the chosen output format's naming rules, **When** the
   review is shown, **Then** that column is flagged with the reason and the download is
   disabled until it is fixed.
4. **Given** a valid selection, **When** the researcher downloads, **Then** they receive a
   zip named after the cohort and date containing: a README explaining which data files to
   obtain and how to run the project; a codebook listing every output column's source,
   label, value labels, missing-value codes, negative codes kept as answers, and topics; an
   empty data folder with its own README; and the merge and data-loading scripts for each
   chosen language.
5. **Given** the downloaded project and the researcher's data files in any supported format
   (tab-delimited, Stata, SPSS or CSV, in any subfolder of the data folder), **When** the
   merge script is run, **Then** it locates each file by name regardless of extension,
   reads only the selected variables, and writes one merged file with one row per
   participant joined on the identifier.
6. **Given** a selected file with more than one row per participant (e.g. a household grid
   or activity history), **When** the merge runs, **Then** that file's variables are written
   to their own separate output file rather than joined.
7. **Given** a required data file is absent, **When** the merge script runs, **Then** it
   stops before reading anything and lists every missing file.
8. **Given** "convert missing codes to NA" is on, **When** the merge runs, **Then** each
   variable's declared missing-value codes, and any other negative code whose label
   indicates missingness, are replaced with NA, while negative codes labelled as genuine
   answers are kept. With the option off, every value is kept exactly as deposited.
9. **Given** Stata or SPSS output is chosen, **When** the merge runs, **Then** the output
   file carries each column's variable label and value labels from the dictionary.
10. **Given** the R and Python versions of the same download, **When** both are run on the
    same data, **Then** they produce the same output.

---

### User Story 4 - Browse by topic (Priority: P2)

The researcher explores what a cohort measures by topic area (e.g. Health › Smoking). An
overview shows, for each topic area and topic, how many variables exist at each sweep. They
filter results to one or more topics, combining them with "any" or "all", and set how
confident a topic tag must be to count.

**Why this priority**: Topic browsing helps researchers who don't know the variable names,
but search alone already delivers a usable product.

**Independent Test**: Open the topic overview for Next Steps, select two topics in "all"
mode, and confirm only variables tagged with both, above the confidence threshold, are
listed.

**Acceptance Scenarios**:

1. **Given** a cohort with topic tags, **When** the researcher expands the topic overview,
   **Then** each topic area is shown with per-sweep counts, expandable to its topics.
2. **Given** the topic overview, **When** the researcher selects a topic area or topic,
   **Then** results are filtered to variables tagged with it, and the selection is shown as
   a removable chip.
3. **Given** two or more topics selected, **When** the researcher switches between "any"
   and "all", **Then** results show variables with at least one, or every one, of the
   selected topics.
4. **Given** a confidence threshold (30%, 50%, 70% or 90%; default 50%), **When** it is
   changed, **Then** topic chips on results, topic counts and the topic filter use only tags
   at or above it.
5. **Given** a topic's cell for a particular sweep, **When** the researcher selects it,
   **Then** results are filtered to that topic at that sweep.
6. **Given** results, **When** each variable is listed, **Then** its strongest topics are
   shown and it is visually marked by its strongest topic area.

---

### User Story 5 - Publish supplied cohort data (Priority: P3)

The data team supplies each cohort's data (metadata, per-file dictionaries with missing
codes already derived, and topic tags) in the documented site-data format. A maintainer adds
or replaces those files in the repository; checks confirm they match the format, and the
site is republished.

**Why this priority**: Needed to keep the tool current and to add cohorts, but researchers
get full value from the initial cohorts without it.

**Independent Test**: Add a small fictional cohort in the documented format, introduce one
deliberate format error, confirm the checks report it and block publishing, fix it, and
confirm the cohort appears on the site.

**Acceptance Scenarios**:

1. **Given** cohort data files in the documented format, **When** they are added to the
   repository, **Then** the cohort appears in the site's cohort list with no application
   code changes.
2. **Given** supplied data that breaks the format (missing required field, unknown sweep or
   file reference, malformed value labels or missing codes, topic not in the cohort's topic
   scheme, confidence outside 0–1), **When** the checks run, **Then** each problem is
   reported with the file and location, and publishing is blocked.
3. **Given** valid data, **When** a change is merged to the main branch, **Then** the public
   site is republished automatically.
4. **Given** a cohort supplied without topic tags, **When** it is opened, **Then** search,
   selection and download work and the topic features are hidden.

### Clarifications

#### Session 2026-10-26

- Q: Is topic tagging part of this rebuild? → A (superseded, see below): Yes, as a very
  simple maintainer-run tagging tool.
- Q: Is any data-preparation tooling (dictionary conversion, validation command, missing-code
  derivation, topic tagging) part of the project? → A: No. The data team supplies cohort data
  ready to use, in the site's documented data format, with missing codes and topic tags
  already included. The project only checks that supplied data matches the format.

---

### Edge Cases

- A variable has no supplied missing codes: nothing is converted for it, whatever the
  option.
- A negative code is supplied as kept-as-answer (e.g. "-1 Dislike"): it is never converted
  to NA, and the details and codebook say so.
- A supplied missing code is flagged as losing an answer: it is converted when asked, and
  the details mark it with a warning.
- How codes are derived (e.g. reading "-1 thru 8" as two codes, not a range) and which sweep
  a twice-deposited file belongs to are decided when the data is prepared, outside this
  project; the site shows the data as supplied.
- Value labels or variable labels contain quotes, backslashes, line breaks or other
  special characters: generated code remains valid and the text is preserved.
- A saved selection refers to variables removed by a metadata update: those are dropped on
  restore without error.
- Two selected columns differ only in letter case: treated as a clash.
- The identifier column is spelled with different case in different files: matched
  ignoring case.
- Identifier values differ in formatting between files (e.g. surrounding spaces): they are
  normalised before joining.
- A requested variable is missing from the researcher's data file (e.g. an older deposit):
  the script warns, skips it and continues.
- The browser blocks local storage (private browsing): the site works, but selections and
  settings are not remembered.
- The site data fails to load: a clear message is shown instead of a blank page.
- More than 500 matching results: "Select all" is not offered.

## Requirements *(mandatory)*

### Functional Requirements

**Cohorts and metadata**

- **FR-001**: The system MUST offer each available cohort for selection, initially BCS70
  and Next Steps, and MUST allow a cohort to be opened directly from a link.
- **FR-002**: For each cohort the system MUST present its name, full name, description,
  participant identifier, sweeps in time order (with labels), data files (with sweep and
  description) and, for each variable: name, label, data file, sweep, position, type,
  measurement level, value labels, declared missing-value codes and topic tags with
  confidence.
- **FR-003**: The system MUST NOT contain, transmit or require any study data; only
  published data-dictionary metadata.

**Search and filtering**

- **FR-004**: Users MUST be able to search variables by any substring of name or label,
  case-insensitively, with results updating as they type.
- **FR-005**: Users MUST be able to filter by sweep, data file, measurement level
  (including "unrecorded") and topic, in any combination, and clear filters individually or
  all at once.
- **FR-006**: The system MUST show the number of matching variables overall, per sweep
  (including sweeps with none) and per measurement level option.
- **FR-007**: Results MUST be shown in pages (initially 200), with a way to show more.
- **FR-008**: Users MUST be able to open any variable's details in place, showing value
  labels (answers before missing codes, with long lists truncated and expandable), negative
  codes kept as answers, declared codes that would lose an answer, topic tags with
  confidence, file information, and other variables with the identical label (up to 10
  shown; not shown when the label is shared by more than 40 variables).
- **FR-009**: Users MUST be able to filter to all variables in a variable's data file from
  its details.

**Topics**

- **FR-010**: The system MUST present a two-level topic scheme (topic areas and topics,
  initially 15 areas and about 100 topics based on the CLOSER Discovery vocabulary) with
  per-sweep variable counts for each.
- **FR-011**: Users MUST be able to filter by one or more topic areas and/or topics,
  combined by "any" or "all", and by a topic at a specific sweep.
- **FR-012**: Users MUST be able to set a minimum topic confidence (30, 50, 70 or 90%,
  default 50%) that governs every topic display and filter.

**Selection**

- **FR-013**: Users MUST be able to add and remove variables individually, by range and
  (for up to 500 selectable results) all at once.
- **FR-014**: The system MUST always include the participant identifier in every download
  and MUST prevent selection of variables from files without it, stating why.
- **FR-015**: The system MUST keep the current selection visible alongside search results,
  grouped by sweep or by file, filterable by text.
- **FR-016**: The system MUST remember each cohort's selection and the user's settings
  between visits on the same browser, without any account.
- **FR-017**: The system MUST give each selected variable a default output column name
  (its own name, qualified by sweep and then by a number only if needed to avoid a clash)
  and let users rename columns.
- **FR-018**: The system MUST block the download, and explain each problem, while any
  column name is invalid (must start with a letter; letters, digits, `_` or `.` only),
  duplicates another or the identifier ignoring case, or breaks the chosen output format's
  rules (Stata: letters, digits and `_` only, at most 32 characters; SPSS: at most 64
  characters, not ending in `.`), and MUST offer a one-step fix for Stata-invalid dots.

**Download**

- **FR-019**: Users MUST be able to choose R, Python or both; output file type CSV, Stata
  or SPSS; and whether missing-value codes are converted to NA (default: off).
- **FR-020**: The download MUST be a single zip file, generated entirely in the browser,
  containing a README, a codebook, a data folder with instructions, and the loading and
  merge scripts (and an RStudio project file when R is chosen) for each chosen language.
- **FR-021**: The generated merge MUST find each required data file by name within the
  data folder and its subfolders regardless of extension, read tab-delimited, CSV, Stata
  and SPSS files, read only the needed columns, and stop with a list of every missing file
  before reading any.
- **FR-022**: The generated merge MUST join one-row-per-participant files on the
  identifier (keeping participants present in any file), and write files with several rows
  per participant to their own output files.
- **FR-023**: The generated merge MUST, when asked, replace exactly the codes listed in
  the codebook for each column with NA, following the missing-code rules (FR-024), and
  MUST otherwise leave values unchanged.
- **FR-024**: The system MUST use each variable's missing codes exactly as supplied in the
  cohort data (codes and ranges to convert, negative codes kept as answers, and declared
  codes that would lose an answer) and MUST NOT derive or alter them.
- **FR-025**: Stata and SPSS output MUST carry variable labels and, for whole-number codes,
  value labels from the dictionary.
- **FR-026**: The settings that govern output (output format, missing-code conversion,
  data folder) MUST be editable at the top of each generated merge script, without
  regenerating.
- **FR-027**: The R and Python versions of a download MUST produce identical results on the
  same input.
- **FR-028**: All text from dictionaries embedded in generated code MUST be escaped so the
  code is always valid.

**Maintenance and publishing**

- **FR-029**: The project MUST NOT include tools to prepare cohort data (dictionary
  conversion, missing-code derivation or topic tagging); cohort data is supplied ready to
  use.
- **FR-030**: The project MUST check all supplied cohort data against the documented format
  and refuse to publish if any problem is found, reporting each with its file and location.
- **FR-031**: The project MUST document the supplied-data format fully enough for the data
  team to produce it and for a maintainer to add a cohort without code changes.
- **FR-032**: Supplied topic tags MUST name only topics in the cohort's supplied topic
  scheme, each with a confidence between 0 and 1.
- **FR-033**: The public site MUST be republished automatically when changes reach the main
  branch, only after all checks pass.

**General**

- **FR-034**: The site MUST be usable by keyboard and screen reader (labelled controls,
  announced changes in counts and selection, visible focus) and MUST support light and dark
  appearance.
- **FR-035**: The site MUST work on phone-width screens as well as desktop.
- **FR-036**: The site MUST display a notice that it is in beta, with a link for reporting
  problems.

### Key Entities

- **Cohort (dataset)**: A longitudinal study. Key, name, full name, description,
  participant identifier, where to obtain the data, what a collection round is called, and
  its ordered sweeps.
- **Sweep (wave)**: One round of data collection. Short key (e.g. "16y"), label (e.g.
  "Age 16, 1986"); a final cross-sweep entry may hold files spanning sweeps.
- **Data file**: One file in the deposit. Name (without extension), sweep, description,
  deposit study number; whether it contains the identifier.
- **Variable**: One column in a data file. Name, label, position, type, measurement level,
  declared missing values, value labels, derived missing codes (converted, kept as answers,
  lossy) and topic tags.
- **Value label**: A code and its meaning for one variable.
- **Topic scheme**: Topic areas, each with topics (id, label, description); named and
  versioned, supplied per cohort.
- **Topic tag**: A variable's assignment to a topic in its cohort's scheme, with a
  confidence (0–1).
- **Selection**: A user's chosen variables for one cohort, each with its output column
  name; stored only in the user's browser.
- **Download options**: Languages, output format, missing-code conversion.
- **Generated project**: The zip produced from a selection and options: README, codebook,
  data folder, scripts.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A researcher can go from opening the site to downloading a merge project for
  10 variables from 3 files in under 5 minutes, without reading external documentation.
- **SC-002**: Search results update within half a second of typing for a cohort of 35,000
  variables, on a typical laptop.
- **SC-003**: For every supported input format and output format, the generated R and
  Python projects produce identical, correct merged output on test data, verified on every
  change.
- **SC-004**: 100% of generated projects run without modification once the required data
  files are placed in the data folder.
- **SC-005**: Generated scripts convert exactly the missing codes supplied for each
  variable and nothing else: no code listed as kept-as-answer is ever converted (verified
  against known examples in the supplied data such as BCS70 `T01FACE`, `e022b` and
  `bd3inc`'s income bands).
- **SC-006**: Every variable in the published dictionaries for each cohort (32,452 for
  BCS70 and 11,430 for Next Steps at the time of the PoC) is searchable on the site.
- **SC-007**: The first view of a cohort is usable within 3 seconds on a typical broadband
  connection.
- **SC-008**: A maintainer can add a new supplied cohort by following the documentation
  alone, with the checks catching 100% of the documented format violations.
- **SC-009**: The site passes an automated accessibility check with no serious or critical
  issues.

## Assumptions

- Users are researchers who already have, or can obtain, access to the cohort data through
  the UK Data Service; the tool does not handle data access or licensing.
- The production version should match the PoC's user-facing behaviour; the PoC is the
  reference for anything this specification does not state.
- Initial cohorts are BCS70 and Next Steps, supplied in the documented format (the PoC's
  built site data is an example of it). Further cohorts are supplied the same way.
- Preparing cohort data (from UK Data Service dictionaries, deriving missing codes, topic
  tagging) happens outside this project; its correctness is the data team's responsibility.
- No user accounts, sign-in, analytics or server-side storage: selections and settings
  live only in the user's browser.
- Generated scripts target the researcher's own machine with a standard R or Python
  installation; Stata and SPSS input/output may need commonly available add-on packages,
  which the generated README names.
- The site is in English (UK) and targets current versions of mainstream browsers.
- Matching variables "with the same label" across sweeps is a convenience based on exact
  wording, not a claim that they measure the same thing.
- Topic tags are machine-assigned and shown with their confidence; they are a discovery
  aid, not an authoritative classification.
