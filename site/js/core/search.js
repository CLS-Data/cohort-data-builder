/* Searching a cohort's variable index. No DOM and no shared state: everything is passed
   in, so it runs under Node in tests.

   The search is a substring scan over the index the page already holds, so it finds a
   fragment of a half-remembered name as well as a word in a label, and needs no server. */

import {
  count,
  DEFAULT_CONF,
  flatten,
  localSel,
  newTally,
  passes,
  rowDomains,
  rowTopics,
} from "./topics.js";

/** Rows drawn at a time; "show more" draws the next lot. */
export const PAGE = 200;

const SAME_LABEL_SHOWN = 10; // other variables listed under "Same label"
const SAME_LABEL_MAX = 40; // a label shared this widely is boilerplate, not a question
const SAME_LABEL_MIN_LENGTH = 10; // shorter labels ("Area code") match by accident

/* A sweep, file or level index no row has: what another cohort's sweep or file filter, or
   a level this cohort does not record, means here. */
const NONE = -2;

/* A level name is looked up in this cohort's own list, since the lists differ. */
function levelIndex(level, manifest) {
  if (typeof level !== "string") return level;
  const i = (manifest.levels || []).indexOf(level);
  return i === -1 ? NONE : i;
}

/**
 * Filter the index rows and count what each filter choice would give, in one pass.
 * @param {Array[]} vars Index rows: [name, label, fileIdx, waveIdx, levelIdx, topics?].
 * @param {{wave: {list: object[]}, levels?: string[], topics?: object}} manifest The
 *   cohort manifest.
 * @param {{query: string, wave: number|null, file: number|null, level: number|string|null,
 *   topicSel?: {kind: string, id: string}[], topicMode?: "any"|"all", minConf?: number}}
 *   filters Each null (or an empty query or topic selection) means "any". `level` is an
 *   index into `manifest.levels` or a level name; -1 means no recorded level. A cohort
 *   without topics matches nothing while a topic filter is set.
 * @returns {{matches: Array[], perWave: number[], perLevel: Map<number, number>,
 *   tally: {topics: Uint32Array[], domains: Uint32Array[]}, untagged: boolean}} The
 *   matching rows in index
 *   order; per-sweep counts of the matches (one per sweep, zeros included); per-level counts
 *   with every filter applied except the level filter; and per-sweep counts for each topic
 *   and domain with every filter applied except the sweep and topic filters, because the
 *   topic overview is where those are chosen.
 */
export function filterVariables(vars, manifest, filters) {
  const q = (filters.query || "").trim().toLowerCase();
  const { wave, file } = filters;
  const level = levelIndex(filters.level, manifest);
  const sel = localSel(filters.topicSel || [], manifest.topics);
  const mode = filters.topicMode || "any";
  const minConf = filters.minConf ?? DEFAULT_CONF;
  const topics = flatten(manifest.topics);
  const tagged = topics.length > 0;
  const tally = newTally(manifest);
  const matches = [];
  const perWave = new Array(manifest.wave.list.length).fill(0);
  const perLevel = new Map();
  for (const row of vars) {
    if (file !== null && row[2] !== file) continue;
    if (q && !row[0].toLowerCase().includes(q) && !row[1].toLowerCase().includes(q)) continue;
    const rowLevel = row[4] ?? -1;
    const levelOk = level === null || rowLevel === level;
    let topicOk = !sel.length;
    if (tagged) {
      const ts = rowTopics(row, minConf).map(([t]) => t);
      const ds = rowDomains(ts, topics);
      topicOk = passes(sel, mode, ts, ds);
      if (levelOk) count(tally, ts, ds, row[3]);
    }
    if (wave !== null && row[3] !== wave) continue;
    if (!topicOk) continue;
    perLevel.set(rowLevel, (perLevel.get(rowLevel) || 0) + 1);
    if (!levelOk) continue;
    matches.push(row);
    perWave[row[3]] += 1;
  }
  return { matches, perWave, perLevel, tally, untagged: !tagged };
}

/**
 * Run one search over several cohorts (feature 007).
 *
 * The query, level and topic filters apply to every cohort. A sweep or file filter names
 * its cohort: the others then have no matches (and are marked `filteredElsewhere`), though
 * their topic tally still ignores a sweep filter, as it does within a cohort. An age filter
 * (one column of the age axis) gives each cohort its own sweep there; a cohort without one
 * has no matches.
 * @param {{key: string, manifest: object, vars: Array[]}[]} cohorts The chosen cohorts,
 *   in the order to list them.
 * @param {{query: string,
 *   wave: {cohort: string, i: number}|{col: number, label: string, sweeps: Object<string, number>}|null,
 *   file: {cohort: string, i: number}|null, level: number|string|null,
 *   topicSel?: object[], topicMode?: "any"|"all", minConf?: number}} filters As
 *   {@link filterVariables}, with sweep and file filters naming their cohort.
 * @returns {{cohort: string, matches: Array[], perWave: number[],
 *   perLevel: Map<number, number>, tally: object, untagged: boolean,
 *   filteredElsewhere: boolean}[]} One result per cohort, in the order given.
 */
export function searchCohorts(cohorts, filters) {
  const own = (f, key) => {
    if (!f) return null;
    if (f.sweeps) return key in f.sweeps ? f.sweeps[key] : NONE;
    return f.cohort === key ? f.i : NONE;
  };
  return cohorts.map(({ key, manifest, vars }) => {
    const wave = own(filters.wave, key);
    const file = own(filters.file, key);
    const r = filterVariables(vars, manifest, { ...filters, wave, file });
    return { cohort: key, ...r, filteredElsewhere: wave === NONE || file === NONE };
  });
}

/**
 * The rows to draw, given how many are allowed on screen.
 * @param {Array[]} matches All matching rows.
 * @param {number} shown How many may be drawn: PAGE, raised by PAGE per "show more".
 * @returns {{rows: Array[], left: number, next: number}} The rows to draw, how many are
 *   not drawn, and how many the next "show more" would add.
 */
export function page(matches, shown) {
  const rows = matches.slice(0, shown);
  const left = matches.length - rows.length;
  return { rows, left, next: Math.min(PAGE, left) };
}

const normLabel = (s) =>
  String(s || "")
    .toLowerCase()
    .replace(/\s+/g, " ")
    .replace(/[\s.:;?]+$/, "")
    .trim();

/**
 * Group rows by normalised label (lower case, single spaces, no trailing `. : ; ?`).
 * Labels under 10 characters are left out.
 * @param {Array[]} vars Index rows.
 * @returns {Map<string, Array[]>} Normalised label to the rows that carry it.
 */
export function buildLabelIndex(vars) {
  const index = new Map();
  for (const row of vars) {
    const label = normLabel(row[1]);
    if (label.length < SAME_LABEL_MIN_LENGTH) continue;
    if (!index.has(label)) index.set(label, []);
    index.get(label).push(row);
  }
  return index;
}

/**
 * Other variables with exactly the same label (case and spacing aside). A shortcut, not a
 * claim that they measure the same thing: a reworded question is not linked.
 * @param {Map<string, Array[]>} index From {@link buildLabelIndex}.
 * @param {Array} row The variable's index row.
 * @returns {{rows: Array[], more: number}} Up to 10 other rows, by sweep then name, and
 *   how many more there are; nothing when the label is shared by more than 40 rows.
 */
export function sameLabel(index, row) {
  const group = index.get(normLabel(row[1]));
  if (!group || group.length > SAME_LABEL_MAX) return { rows: [], more: 0 };
  const others = group
    .filter((r) => r !== row)
    .sort((a, b) => a[3] - b[3] || (a[0] < b[0] ? -1 : a[0] > b[0] ? 1 : 0));
  return {
    rows: others.slice(0, SAME_LABEL_SHOWN),
    more: Math.max(0, others.length - SAME_LABEL_SHOWN),
  };
}
