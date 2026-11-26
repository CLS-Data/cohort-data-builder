# Several cohorts: {{count}}

Variables from several cohorts, selected with Cohort Data Builder on {{created}}.
{{languages}}

**This archive contains no study data.** You supply the data files; each
project's scripts read them and write that cohort's merged result.

## What is in it

Each folder is a complete project for one cohort, exactly as that cohort's own
download would be:

{{cohorts}}

## How to use it

1. Put each cohort's data files in that folder's `data/` folder. Its
   `data/README.md` lists the files it needs and where to get them.
2. Run each folder's code on its own, as its `README.md` says.
3. Each produces that cohort's merged dataset, one row per person, keyed on
   that cohort's own identifier.

**The cohorts are different people and are not merged with each other.** A
variable with the same name in two cohorts need not mean the same thing, and
harmonising variables across cohorts is up to you.
