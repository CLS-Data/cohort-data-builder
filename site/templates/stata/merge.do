* {{dataset}}: variables selected with Cohort Data Builder on {{created}}.
*
* Run this from the folder that holds README.md: in Stata, cd to that folder
* and type `do stata/merge.do`; or from a terminal, `stata-mp -b do stata/merge.do`
* (or stata-se, stata). Needs Stata 16 or later and no extra packages.
* It starts by clearing the data in memory. README.md lists the data files it
* needs.

version 16
clear
set more off

* ── Settings ─────────────────────────────────────────────────────────────

* The folder holding the data files. Subfolders are searched too.
local DATA_DIR "data"

* Where the results are written.
local OUTPUT_DIR "output"

* The file type written: "csv" or "dta" (Stata, with the variable and value
* labels below). "sav" (SPSS) is not something Stata can write: it gives .dta.
local OUTPUT_FORMAT "{{output_format}}"

* 1 replaces each variable's missing-value codes below with Stata's missing
* value (.). 0 keeps the codes exactly as deposited.
local MISSING_TO_NA {{missing_to_na}}

* The column that identifies a person in every file.
local IDENTIFIER "{{identifier}}"

* ── Your selection ───────────────────────────────────────────────────────

* For each data file: its name, the variables to take from it, and the output
* column each becomes, in the same order.
{{selection}}

* The codes MISSING_TO_NA replaces, per output column. Copied from the data
* dictionary's missing-value codes. Negative codes that are real answers are
* not here.
capture program drop cdb_missing_codes
program define cdb_missing_codes
{{missing_codes}}
end

* Labels written into .dta files, from the data dictionary: a label per output
* column, and the value labels of each column that has them.
capture program drop cdb_labels
program define cdb_labels
{{labels}}
end

capture program drop cdb_value_labels
program define cdb_value_labels
{{value_labels}}
end

* ── Merge ────────────────────────────────────────────────────────────────

capture confirm file "stata/load_data.do"
if _rc {
    display as error "Run this from the folder that holds README.md (cd there first)."
    exit 601
}
run "stata/load_data.do"

mata: st_local("found", strofreal(direxists(st_local("DATA_DIR"))))
if !`found' {
    display as error `"The data folder does not exist: `DATA_DIR'"'
    display as error "Put the data files there, or set DATA_DIR at the top of stata/merge.do."
    exit 601
}

* Check every file is present before reading any of them.
local absent ""
forvalues i = 1/`n_files' {
    cdb_find `"`DATA_DIR'"' "`f`i'_file'"
    local f`i'_path `"`r(path)'"'
    if `"`r(path)'"' == "" local absent `absent' `f`i'_file'
}
if "`absent'" != "" {
    display as error `"These data files were not found under `DATA_DIR':"'
    foreach f of local absent {
        display as error "  `f'"
    }
    display as error "See README.md for where to get them."
    exit 601
}

capture mkdir `"`OUTPUT_DIR'"'
local wide ""

forvalues i = 1/`n_files' {
    local file `f`i'_file'
    display as text `"Reading `f`i'_path'"'
    cdb_read `"`f`i'_path'"' "`IDENTIFIER'" "`f`i'_vars'"
    local skipped `r(missing)'
    if "`skipped'" != "" {
        display as text "Warning: `file': not found, skipped: `skipped'"
    }

    * Output column names, renamed all at once so names can be swapped.
    local from ""
    local to ""
    local n : word count `f`i'_vars'
    forvalues j = 1/`n' {
        local v : word `j' of `f`i'_vars'
        local c : word `j' of `f`i'_cols'
        if !`: list v in skipped' & "`v'" != "`c'" {
            local from `from' `v'
            local to `to' `c'
        }
    }
    if "`from'" != "" rename (`from') (`to')

    cdb_identifier `IDENTIFIER'
    if `MISSING_TO_NA' cdb_missing_codes

    * A file with more than one row per person (a household grid, a history)
    * cannot be joined one-to-one. It is written out on its own instead.
    quietly duplicates drop
    tempvar rows
    quietly bysort `IDENTIFIER': generate `rows' = _N
    quietly count if `rows' > 1
    local several = r(N)
    drop `rows'
    if `several' > 0 {
        cdb_labels
        cdb_value_labels
        cdb_write `"`OUTPUT_DIR'/`file'_long"' "`OUTPUT_FORMAT'"
        display as text `"`file' has several rows per `IDENTIFIER'; written separately to `r(file)'"'
        continue
    }
    tempfile w`i'
    quietly save "`w`i''"
    local wide `wide' `i'
}

if "`wide'" != "" {
    local first : word 1 of `wide'
    use "`w`first''", clear
    local rest : list wide - first
    foreach i of local rest {
        quietly merge 1:1 `IDENTIFIER' using "`w`i''", nogenerate
    }
    sort `IDENTIFIER'
    cdb_labels
    cdb_value_labels
    cdb_write `"`OUTPUT_DIR'/merged"' "`OUTPUT_FORMAT'"
    display as text `"Wrote `=_N' rows and `=c(k)' columns to `r(file)'"'
}
