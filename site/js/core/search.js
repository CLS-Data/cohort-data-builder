/* Searching a cohort's variable index. No DOM and no shared state: everything is passed
   in, so it runs under Node in tests.

   The search is a substring scan over the index the page already holds, so it finds a
   fragment of a half-remembered name as well as a word in a label, and needs no server. */

import { count, DEFAULT_CONF, flatten, newTally, passes, rowDomains, rowTopics } from "./topics.js";

/** Rows drawn at a time; "show more" draws the next lot. */
export const PAGE = 200;

const SAME_LABEL_SHOWN = 10; // other variables listed under "Same label"
const SAME_LABEL_MAX = 40; // a label shared this widely is boilerplate, not a question
const SAME_LABEL_MIN_LENGTH = 10; // shorter labels ("Area code") match by accident

/**
 * Filter the index rows and count what each filter choice would give, in one pass.
 * @param {Array[]} vars Index rows: [name, label, fileIdx, waveIdx, levelIdx, topics?].
 * @param {{wave: {list: object[]}, topics?: object}} manifest The cohort manifest.
 * @param {{query: string, wave: number|null, file: number|null, level: number|null,
 *   topicSel?: object[], topicMode?: "any"|"all", minConf?: number}} filters Each null (or
 *   an empty query or topic selection) means "any"; level -1 means no recorded level. The
 *   topic filter (see topics.js) is ignored when the cohort has no topics.
 * @returns {{matches: Array[], perWave: number[], perLevel: Map<number, number>,
 *   tally: {topics: Uint32Array[], domains: Uint32Array[]}}} The matching rows in index
 *   order; per-sweep counts of the matches (one per sweep, zeros included); per-level counts
 *   with every filter applied except the level filter; and per-sweep counts for each topic
 *   and domain with every filter applied except the sweep and topic filters, because the
 *   topic overview is where those are chosen.
 */
export function filterVariables(vars, manifest, filters) {
  const q = (filters.query || "").trim().toLowerCase();
  const { wave, file, level } = filters;
  const sel = filters.topicSel || [];
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
    let topicOk = true;
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
  return { matches, perWave, perLevel, tally };
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
