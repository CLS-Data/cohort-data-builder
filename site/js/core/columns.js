/* Checking output column names before a download: what blocks it, and the one bulk fix. */

import { keyOf } from "./selection.js";

/* The intersection of a valid R name, a Python-friendly column and a CSV header that
   survives any tool. */
const NAME_OK = /^[A-Za-z][A-Za-z0-9_.]*$/;

/* What each output file type allows in a column name, beyond NAME_OK. */
const FORMAT_RULES = {
  csv: () => null,
  dta: (name) => {
    if (!/^[A-Za-z_][A-Za-z0-9_]*$/.test(name)) {
      return `Stata names use only letters, digits and _: try ${name.replace(/[^A-Za-z0-9_]/g, "_")}.`;
    }
    return name.length > 32 ? "Stata names are at most 32 characters." : null;
  },
  sav: (name) => {
    if (name.length > 64) return "SPSS names are at most 64 characters.";
    return name.endsWith(".") ? "SPSS names cannot end with a dot." : null;
  },
};

/**
 * Every column whose name would break the download, and why.
 * @param {object[]} selection The selection ({name, file, column, …}).
 * @param {string} identifier The cohort's identifier, always the first output column.
 * @param {"csv"|"dta"|"sav"} format The chosen output file type.
 * @returns {Map<string, string>} `<file>:<name>` to the problem; empty when all is well.
 */
export function problems(selection, identifier, format) {
  const out = new Map();
  const seen = new Map([[String(identifier).toLowerCase(), null]]);
  const rule = FORMAT_RULES[format] || FORMAT_RULES.csv;
  for (const b of selection) {
    if (!NAME_OK.test(b.column || "")) {
      out.set(keyOf(b), "Must start with a letter and use only letters, digits, _ or .");
      continue;
    }
    const formatProblem = rule(b.column);
    if (formatProblem) {
      out.set(keyOf(b), formatProblem);
      continue;
    }
    const lower = b.column.toLowerCase();
    if (seen.has(lower)) {
      const other = seen.get(lower);
      const msg =
        other === null
          ? `${b.column} is the identifier's name; the column would overwrite it.`
          : `Two columns would both be called ${b.column}.`;
      out.set(keyOf(b), msg);
      if (other) out.set(other, msg);
      continue;
    }
    seen.set(lower, keyOf(b));
  }
  return out;
}

/**
 * Make every column a Stata-safe name: anything but letters, digits and _ becomes _, and
 * a name that would then clash gets `_2`, `_3`… .
 * @param {object[]} selection The selection.
 * @param {string} identifier The cohort's identifier, whose name is taken.
 * @returns {object[]} A new selection with fixed columns.
 */
export function fixDots(selection, identifier) {
  const taken = new Set([String(identifier).toLowerCase()]);
  return selection.map((b) => {
    const base = b.column.replace(/[^A-Za-z0-9_]/g, "_");
    let name = base;
    for (let i = 2; taken.has(name.toLowerCase()); i++) name = `${base}_${i}`;
    taken.add(name.toLowerCase());
    return { ...b, column: name };
  });
}
