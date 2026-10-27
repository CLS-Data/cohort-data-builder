/* What an opened variable shows, as data: the interface turns it into HTML. */

import { capitalise } from "./text.js";

const ANSWERS_SHOWN = 8; // value labels before "+ N more"

/** "-1.0" -> "-1": the dictionaries store every code as a decimal. */
const code = (value) => String(value).replace(/\.0$/, "");

/**
 * Describe one variable from its dictionary entry.
 * @param {object} entry The variable's entry in `dict/<file>.json`.
 * @param {{name: string, description?: string, study?: string}} file The manifest file.
 * @param {string} identifier The cohort's person identifier.
 * @returns {{isIdentifier: true} | {answers: {code: string, label: string}[],
 *   more: {code: string, label: string}[], missing: {code: string, label: string,
 *   lossy: boolean}[], kept: Array[], lossy: Array[], note: "continuous"|"unlabelled"|null,
 *   facts: {name: string, value: string, detail?: string}[]}} For the identifier, only that
 *   fact. Otherwise value labels split into answers (the first 8, the rest in `more`) and
 *   missing codes (in `na.values` or an `na.ranges` range, null being an open end);
 *   `kept` and `lossy` as supplied, a missing code also in `lossy` flagged; a note when
 *   there are no value labels; and the facts that are present.
 */
export function describeVariable(entry, file, identifier) {
  if (String(entry.variable).toLowerCase() === String(identifier).toLowerCase()) {
    return { isIdentifier: true };
  }
  const na = entry.na || {};
  const naValues = new Set(na.values || []);
  const lossyCodes = new Set((na.lossy || []).map(([x]) => x));
  const isMissing = (x) =>
    naValues.has(x) ||
    (na.ranges || []).some(([lo, hi]) => (lo === null || x >= lo) && (hi === null || x <= hi));

  const answers = [];
  const missing = [];
  for (const v of entry.values || []) {
    const x = Number.parseFloat(v.value);
    if (!Number.isNaN(x) && isMissing(x)) {
      missing.push({ code: code(v.value), label: v.label, lossy: lossyCodes.has(x) });
    } else {
      answers.push({ code: code(v.value), label: v.label });
    }
  }

  let note = null;
  if (!entry.values?.length) note = entry.measurement === "SCALE" ? "continuous" : "unlabelled";

  const facts = [
    file.description
      ? { name: "File", value: file.name, detail: file.description }
      : { name: "File", value: file.name },
  ];
  if (file.study) facts.push({ name: "Study", value: `SN ${file.study}` });
  if (entry.pos) facts.push({ name: "Position", value: String(entry.pos) });
  if (entry.measurement) {
    facts.push({ name: "Level", value: capitalise(entry.measurement.toLowerCase()) });
  }
  if (entry.type) facts.push({ name: "Type", value: entry.type });

  return {
    answers: answers.slice(0, ANSWERS_SHOWN),
    more: answers.slice(ANSWERS_SHOWN),
    missing,
    kept: na.kept || [],
    lossy: na.lossy || [],
    note,
    facts,
  };
}
