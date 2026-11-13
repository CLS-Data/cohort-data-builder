* Reading deposited data files, for merge.do.
*
* Nothing in here names a study: merge.do says which files and variables it
* wants, and these programs find and read them. The read command is chosen
* from each file's extension, so it works with whichever format you
* downloaded from the UK Data Service:
*
*   .tab .txt .dat   tab-delimited      import delimited
*   .csv             comma-separated    import delimited
*   .dta             Stata              use
*   .sav .zsav       SPSS               import spss
*
* Files are found by name anywhere under the data folder, subfolders
* included, so a UKDS download can be unzipped into it as it is. No data file
* is ever changed.

version 16

* cdb_find <folder> <name>
* The path of the data file called <name> (any supported extension, any case)
* in <folder> or its subfolders, in r(path); "" when there is none. When the
* same file is there in several formats, the first in the list above is used.
capture program drop cdb_find
program define cdb_find, rclass
    args folder name
    local exts "tab txt dat csv dta sav zsav"
    local best ""
    local rank 99
    local files : dir `"`folder'"' files "*", respectcase
    foreach f of local files {
        forvalues i = 1/7 {
            local e : word `i' of `exts'
            if lower(`"`f'"') == lower(`"`name'.`e'"') & `i' < `rank' {
                local best `"`folder'/`f'"'
                local rank `i'
            }
        }
    }
    local subs : dir `"`folder'"' dirs "*", respectcase
    foreach s of local subs {
        cdb_find `"`folder'/`s'"' `"`name'"'
        if `"`r(path)'"' != "" & r(rank) < `rank' {
            local best `"`r(path)'"'
            local rank = r(rank)
        }
    }
    return local path `"`best'"'
    return scalar rank = `rank'
end

* cdb_read <path> <identifier> <variables>
* Load one file, keeping only the identifier and the wanted variables, in that
* order. Names are matched ignoring case, because the same file can spell them
* differently in different formats, and come back spelt as asked. Values are
* the codes as deposited: value labels are dropped. Wanted variables the file
* lacks are listed in r(missing); a missing identifier stops the run.
capture program drop cdb_read
program define cdb_read, rclass
    args path id wanted
    local ext = lower(substr(`"`path'"', strrpos(`"`path'"', ".") + 1, .))

    * The file's variable names, read without loading the data where possible.
    if "`ext'" == "dta" {
        quietly describe using `"`path'"', varlist
        local header `r(varlist)'
    }
    else {
        if inlist("`ext'", "tab", "txt", "dat") {
            quietly import delimited using `"`path'"', delimiters(tab) ///
                varnames(1) case(preserve) asdouble bindquotes(nobind) clear
        }
        else if "`ext'" == "csv" {
            quietly import delimited using `"`path'"', delimiters(",") ///
                varnames(1) case(preserve) asdouble clear
        }
        else {
            * Plain quotes: import spss misreads a compound-quoted path.
            quietly import spss using "`path'", clear
        }
        quietly ds
        local header `r(varlist)'
    }

    local keep ""
    local from ""
    local to ""
    local missing ""
    foreach w in `id' `wanted' {
        local hit ""
        if `: list w in header' local hit `w'
        else {
            foreach v of local header {
                if lower("`v'") == lower("`w'") local hit `v'
            }
        }
        if "`hit'" == "" local missing `missing' `w'
        else {
            local keep `keep' `hit'
            if "`hit'" != "`w'" {
                local from `from' `hit'
                local to `to' `w'
            }
        }
    }
    if `: list id in missing' {
        display as error `"`path' has no `id' column, so it cannot be merged."'
        exit 111
    }

    if "`ext'" == "dta" quietly use `keep' using `"`path'"', clear
    else keep `keep'
    if "`from'" != "" rename (`from') (`to')
    local found : list wanted - missing
    order `id' `found'

    quietly ds, has(type numeric)
    if "`r(varlist)'" != "" label values `r(varlist)'
    label drop _all
    return local missing `missing'
end

* cdb_identifier <identifier>
* Trimmed and upper-cased text, so the same person links across files that
* formatted the identifier differently.
capture program drop cdb_identifier
program define cdb_identifier
    args id
    capture confirm string variable `id'
    if _rc quietly tostring `id', replace format(%20.0g)
    quietly replace `id' = upper(strtrim(`id'))
end

* cdb_write <path> <format>
* Write the data in memory as <path>.csv or <path>.dta (<path> has no
* extension). Stata cannot write SPSS files, so "sav" writes .dta with a note.
* A .dta file carries the variable and value labels; a CSV has the codes only.
capture program drop cdb_write
program define cdb_write, rclass
    args path format
    if "`format'" == "csv" {
        quietly export delimited using `"`path'.csv"', nolabel replace
        return local file `"`path'.csv"'
    }
    else if inlist("`format'", "dta", "sav") {
        if "`format'" == "sav" {
            display as text "Stata cannot write .sav files: writing .dta instead."
        }
        quietly save `"`path'.dta"', replace
        return local file `"`path'.dta"'
    }
    else {
        display as error `"OUTPUT_FORMAT must be "csv", "dta" or "sav", not "`format'"."'
        exit 198
    }
end
