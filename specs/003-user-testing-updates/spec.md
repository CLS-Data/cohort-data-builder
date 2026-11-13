# Feature Specification: Updates from user testing

**Feature Branch**: `003-user-testing-updates`

**Created**: 2026-11-13

**Status**: Draft

**Input**: User description: "I want to make some updates after user testing. 1. On the selection tab, there are two panels both showing the list of variables selected, we only need 1 lets remove the one on the left. 2. On this same page can we have it so that the download configuration buttons and the download button are fixed on this screen and the selected variables are in a scrollable window i.e. so you dont have to scroll all the way down to the bottom to download the code. 3. Can we add a download stata boiler plate code option. 4. Can we add some functionality so that if a tag is incorrect a user can easily raise an issue to suggest a new tag."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - One list of selected variables (Priority: P1)

A researcher opens the Selection tab to check what they picked before downloading. Today
they see the same variables twice: a list on the left (where they can remove a variable)
and the column list on the right (where they can rename the output column). Testers found
this confusing. They see one list instead, and from it they can both rename and remove
each variable.

**Why this priority**: It is the first thing everyone sees on the Selection tab, and
testers named it as confusing. Every other change on this page builds on a single list.

**Independent Test**: Select three variables, open the Selection tab: each variable
appears exactly once, and each can be renamed and removed from that one place.

**Acceptance Scenarios**:

1. **Given** three variables are selected, **When** the researcher opens the Selection tab,
   **Then** each variable is listed once, with its output column name, label, sweep and file.
2. **Given** the Selection tab is open, **When** the researcher removes a variable from the
   list, **Then** it disappears from the list, the selection count in the header drops by
   one, and the variable is no longer selected on the Variables tab.
3. **Given** the Selection tab is open, **When** the researcher renames a variable's output
   column, **Then** the new name is kept and used in the download, as it is today.
4. **Given** nothing is selected, **When** the researcher opens the Selection tab, **Then**
   they see the existing "nothing selected yet" guidance, not an empty list.

---

### User Story 2 - Download always in reach (Priority: P1)

A researcher with a long selection (say 80 variables) wants to download without scrolling
past every variable to reach the options and the button. The download options and the
download button stay in view on the Selection tab; the list of variables scrolls on its
own.

**Why this priority**: Testers with large selections could not find the download button.
Downloading is the point of the tool.

**Independent Test**: Select 80 variables, open the Selection tab on a laptop-sized
screen: the download options and button are visible without scrolling the page, and the
variable list scrolls within its own area.

**Acceptance Scenarios**:

1. **Given** 80 variables are selected on a 1366×768 screen, **When** the researcher opens
   the Selection tab, **Then** the language, format and missing-value options and the
   download button are visible without scrolling the page.
2. **Given** the same selection, **When** the researcher scrolls the variable list, **Then**
   only the list moves; the options and button stay where they are.
3. **Given** a column name needs changing before download, **When** the researcher looks at
   the download area, **Then** they can see why the button is unavailable and reach the
   column that needs changing.
4. **Given** a phone-sized screen, **When** the researcher opens the Selection tab, **Then**
   the download button is still reachable without scrolling through the whole list, and
   nothing is cut off or overflows sideways.

---

### User Story 3 - Stata code (Priority: P2)

A researcher who works in Stata wants the downloaded project to include a Stata do-file
that does what the R and Python scripts do: read the needed files from their own copy of
the data, keep the selected variables, apply the output column names, treat missing-value
codes as chosen, and merge the sweeps into one dataset, one row per person.

**Why this priority**: Many cohort-study researchers use Stata; today they must translate
the R or Python code themselves. It is a new option, so it comes after fixing the page
everyone uses.

**Independent Test**: Choose Stata only, download, and run the do-file in Stata against the
test data: it writes the merged dataset with the same rows, columns and values as the R and
Python scripts produce for the same selection.

**Acceptance Scenarios**:

1. **Given** variables are selected, **When** the researcher ticks Stata (alone or with R
   and/or Python) and downloads, **Then** the project contains a Stata do-file and the
   README explains how to run it.
2. **Given** the same selection and options, **When** the do-file, the R script and the
   Python script are each run on the same data, **Then** they produce the same merged
   dataset.
3. **Given** "convert missing codes" is on, **When** the do-file runs, **Then** each
   variable's missing-value codes become Stata missing values; when it is off, the codes
   are kept as they are.
4. **Given** a file has several rows per person, **When** the do-file runs, **Then** that
   file is written to its own output file, as the R and Python scripts do.
5. **Given** no language is ticked, **When** the researcher looks at the download button,
   **Then** it is unavailable, as today.

---

### User Story 4 - Suggest a better topic tag (Priority: P3)

A researcher looking at a variable's details sees a topic tag that is wrong, or notices a
topic that is missing. From the variable's details they can raise a suggestion in a couple
of clicks, which opens a pre-filled issue for the maintainers saying which variable,
which cohort, the current tags, and what they think the tags should be.

**Why this priority**: Tags come from a large language model and will sometimes be wrong;
an easy way to report them improves the data over time. It does not block anyone's work.

**Independent Test**: Open a variable's details, choose "suggest a tag change": an issue
form opens in a new tab with the cohort, variable name, label, file and current tags
already filled in, leaving only the suggestion to write.

**Acceptance Scenarios**:

1. **Given** a variable's details are open, **When** the researcher chooses to suggest a tag
   change, **Then** a new tab opens on the project's issue tracker with a new issue whose
   title names the variable and cohort, and whose body lists the variable's file, label,
   current tags with their confidence, and a place to write the suggestion.
2. **Given** a variable with no tags, **When** the researcher opens its details, **Then** the
   option is still offered, as a suggestion to add a tag.
3. **Given** the researcher has opened the suggestion, **When** they come back to the
   builder, **Then** their search, filters and selection are unchanged.
4. **Given** suggestions arrive, **When** a maintainer views the issue tracker, **Then** they
   can list every tag suggestion together.

### Edge Cases

- A selection of several hundred variables: the list scrolls smoothly and the download area
  stays fixed.
- The browser window is very short (under 600px tall): the download area must not cover the
  whole list; the page may scroll as a whole rather than hide either part.
- A Stata user's output column name is not a valid Stata name (too long, starts with a
  digit, contains a dot): the existing column-name checks must cover Stata, and the
  download stays unavailable until it is fixed.
- A variable with many tags, or a long label: the pre-filled issue stays within the length
  the issue tracker accepts; if it would not, it is shortened, keeping the variable name,
  cohort and tags.
- The researcher does not have an account on the issue tracker: they are asked to sign in
  there; the builder itself needs no account.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The Selection tab MUST show each selected variable exactly once.
- **FR-002**: From that one list, users MUST be able to rename a variable's output column
  and remove the variable from the selection.
- **FR-003**: The existing column-name problem messages (clashes, invalid names) MUST still
  appear against the variable they concern.
- **FR-004**: On screens at least 1024px wide and 700px tall, the download options and the
  download button MUST stay visible while the variable list scrolls within its own area.
- **FR-005**: On smaller screens the download button MUST be reachable without scrolling
  through the whole list, and the page MUST not scroll sideways.
- **FR-006**: The download options MUST offer Stata alongside R and Python as a code
  language; any combination of the three may be chosen, and at least one is required.
  The language option is labelled so it cannot be mistaken for the Stata (.dta) output
  format.
- **FR-007**: When Stata is chosen, the downloaded project MUST include a do-file that
  reads the needed data files, keeps the selected variables, applies the output column
  names, applies the missing-value choice, merges the sweeps on the person identifier,
  writes files with several rows per person separately, and writes the result in the
  chosen output format.
- **FR-008**: For the same selection, options and data, the Stata do-file MUST produce the
  same merged data as the R and Python scripts.
- **FR-009**: The project README MUST explain how to run the Stata do-file and which Stata
  version it needs.
- **FR-010**: Each variable's details MUST offer a way to suggest a tag change, whether or
  not it has tags.
- **FR-011**: Suggesting a tag change MUST open, in a new tab, a pre-filled new issue on the
  project's public issue tracker containing the cohort, variable name, label, file and
  current tags with confidence, and a labelled place for the suggestion.
- **FR-012**: Tag suggestions MUST be marked so that maintainers can list them together.
- **FR-013**: Suggesting a tag change MUST NOT change the researcher's search, filters or
  selection.
- **FR-014**: All new and changed controls MUST be usable by keyboard and screen reader and
  meet the site's existing accessibility checks in light and dark themes.
- **FR-015**: The site MUST still hold and send no study data: a tag suggestion contains
  only metadata already published on the site.

### Key Entities

- **Selected variable**: a variable in the selection, with its output column name, label,
  sweep and source file.
- **Download options**: the chosen code languages (now R, Python and/or Stata), output
  format and missing-value handling.
- **Tag suggestion**: an issue raised by a user about one variable's topic tags: cohort,
  variable, file, label, current tags with confidence, and the user's suggestion.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In a repeat of the user test, no tester reports seeing the selected variables
  twice.
- **SC-002**: With 80 variables selected, a user reaches and starts the download from the
  Selection tab with no page scrolling, in under 10 seconds.
- **SC-003**: The Stata do-file, run on the test data, reproduces the R and Python output
  exactly (same rows, columns and values) for every selection in the test suite.
- **SC-004**: A user can raise a tag suggestion from a variable's details in 2 clicks plus
  typing their suggestion, with the variable's details already filled in.
- **SC-005**: Accessibility checks report no serious or critical problems on the changed
  pages, in light and dark themes, and the Selection tab fits a 390px-wide phone screen.

## Assumptions

- "Remove the one on the left" means removing the duplicate list, not its ability to
  remove variables: removing moves into the remaining list.
- Dragging variables onto the Selection tab to add them keeps working.
- "Stata boilerplate code" means a do-file that does the same job as the existing R and
  Python scripts, not just a stub; it targets Stata 16 or later.
- The project's issue tracker is its public GitHub repository, which the beta bar already
  links to; raising an issue there needs a GitHub account, which is acceptable for a beta.
- Tag suggestions are reviewed by maintainers by hand; nothing in this feature changes tags
  automatically.
- The Stata data format (.dta) is already an output format; this feature adds Stata as a
  code language.
