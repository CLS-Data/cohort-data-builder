/* Topics: the flattened scheme, a row's tags, the topic filter and the overview counts.
   No DOM and no shared state.

   A selection is a list of items {kind: "d"|"t", i}, each a whole domain (topic area) or
   one topic. A row matches an item if it carries that topic (or any topic of that domain)
   at or above the confidence threshold. Items combine by "any" (the union: smoking or
   alcohol) or "all" (the intersection: smoking and pregnancy). */

/** The confidence thresholds offered, in percent. */
export const CONFIDENCES = [30, 50, 70, 90];

/** The threshold used until another is chosen. */
export const DEFAULT_CONF = 50;

/**
 * A usable confidence threshold.
 * @param {*} value A saved or chosen threshold.
 * @returns {number} The value if it is one of {@link CONFIDENCES}, else the default.
 */
export const validConf = (value) => (CONFIDENCES.includes(value) ? value : DEFAULT_CONF);

const flatCache = new WeakMap();

/**
 * Every topic of a scheme in one list, the order the index refers to them by.
 * @param {{domains: object[]}|undefined} scheme The manifest's `topics`, if any.
 * @returns {{id: string, label: string, description: string, domain: number}[]} Each
 *   topic with the index of its domain. Empty when there is no scheme.
 */
export function flatten(scheme) {
  if (!scheme) return [];
  if (!flatCache.has(scheme)) {
    flatCache.set(
      scheme,
      scheme.domains.flatMap((d, di) => d.topics.map((t) => ({ ...t, domain: di }))),
    );
  }
  return flatCache.get(scheme);
}

/**
 * A row's topics at or above the threshold, strongest first.
 * @param {Array} row An index row; element 5, if present, is `[topic, percent, ...]`.
 * @param {number} minConf The threshold, in percent.
 * @returns {Array<[number, number]>} `[topicIndex, percent]` pairs.
 */
export function rowTopics(row, minConf) {
  const flat = row[5];
  if (!flat) return [];
  const out = [];
  for (let i = 0; i < flat.length; i += 2) {
    if (flat[i + 1] >= minConf) out.push([flat[i], flat[i + 1]]);
  }
  return out.sort((a, b) => b[1] - a[1]);
}

/**
 * The domains a set of topics belong to.
 * @param {number[]} ts Topic indices.
 * @param {object[]} topics From {@link flatten}.
 * @returns {Set<number>} Domain indices.
 */
export const rowDomains = (ts, topics) => new Set(ts.map((t) => topics[t].domain));

const same = (a, b) => a.kind === b.kind && a.i === b.i;
const domainOf = (item, topics) => (item.kind === "d" ? item.i : topics[item.i].domain);

/**
 * Select an item, or deselect it if it is selected. A domain and its own topics are never
 * selected together: choosing a topic replaces its selected domain, and choosing a domain
 * replaces any of its selected topics.
 * @param {{kind: string, i: number}[]} sel The current selection; not changed.
 * @param {"d"|"t"} kind Domain or topic.
 * @param {number} i Its index.
 * @param {object[]} topics From {@link flatten}.
 * @returns {{kind: string, i: number}[]} The new selection.
 */
export function toggle(sel, kind, i, topics) {
  const item = { kind, i };
  if (sel.some((s) => same(s, item))) return sel.filter((s) => !same(s, item));
  const d = domainOf(item, topics);
  const clash = (s) =>
    kind === "t" ? s.kind === "d" && s.i === d : s.kind === "t" && domainOf(s, topics) === d;
  return [...sel.filter((s) => !clash(s)), item];
}

/**
 * Select an item if it is not selected already; never deselects.
 * @param {{kind: string, i: number}[]} sel The current selection; not changed.
 * @param {"d"|"t"} kind Domain or topic.
 * @param {number} i Its index.
 * @param {object[]} topics From {@link flatten}.
 * @returns {{kind: string, i: number}[]} The new selection, or `sel` itself if unchanged.
 */
export const ensure = (sel, kind, i, topics) =>
  sel.some((s) => same(s, { kind, i })) ? sel : toggle(sel, kind, i, topics);

/**
 * Whether a row with these topics passes the topic filter.
 * @param {{kind: string, i: number}[]} sel The selection; empty passes everything.
 * @param {"any"|"all"} mode How several items combine.
 * @param {number[]} ts The row's topics at or above the threshold.
 * @param {Set<number>} ds Their domains.
 * @returns {boolean} True if the row matches at least one item ("any") or every item ("all").
 */
export function passes(sel, mode, ts, ds) {
  if (!sel.length) return true;
  let k = 0;
  for (const s of sel) if (s.kind === "t" ? ts.includes(s.i) : ds.has(s.i)) k++;
  return mode === "all" ? k === sel.length : k > 0;
}

/**
 * Empty per-sweep counts for every topic and domain.
 * @param {object} manifest The cohort manifest.
 * @returns {{topics: Uint32Array[], domains: Uint32Array[]}} One row per topic and per
 *   domain, one cell per sweep; empty lists when the cohort has no topics.
 */
export function newTally(manifest) {
  const n = manifest.wave.list.length;
  return {
    topics: flatten(manifest.topics).map(() => new Uint32Array(n)),
    domains: (manifest.topics?.domains || []).map(() => new Uint32Array(n)),
  };
}

/**
 * Count one row in a tally.
 * @param {{topics: Uint32Array[], domains: Uint32Array[]}} t From {@link newTally}.
 * @param {number[]} ts The row's topics.
 * @param {Set<number>} ds Their domains.
 * @param {number} wave The row's sweep index.
 */
export function count(t, ts, ds, wave) {
  for (const i of ts) t.topics[i][wave]++;
  for (const d of ds) t.domains[d][wave]++;
}

/**
 * Per-sweep counts of the given rows for every topic and domain. The search does this as it
 * filters (see search.js); this is the same count for rows already chosen.
 * @param {Array[]} rows Index rows.
 * @param {object} manifest The cohort manifest.
 * @param {number} minConf The threshold, in percent.
 * @returns {{topics: Uint32Array[], domains: Uint32Array[]}} The counts.
 */
export function tally(rows, manifest, minConf) {
  const topics = flatten(manifest.topics);
  const t = newTally(manifest);
  for (const row of rows) {
    const ts = rowTopics(row, minConf).map(([i]) => i);
    count(t, ts, rowDomains(ts, topics), row[3]);
  }
  return t;
}

/**
 * How dark to draw an overview cell. Within a topic ("row"), against that row's busiest
 * sweep, which shows where in the life course it is measured. Across topics ("abs"), against
 * the busiest cell anywhere, on a log scale so a topic with dozens of variables is not
 * flattened by one with thousands.
 * @param {number} n The cell's count.
 * @param {number} rowMax The largest count in its row.
 * @param {number} allMax The largest count in the overview.
 * @param {"row"|"abs"} mode The shading chosen.
 * @returns {number} 0 for an empty cell, else 1 (lightest) to 4.
 */
export function shade(n, rowMax, allMax, mode) {
  if (!n) return 0;
  const r = mode === "abs" ? Math.log1p(n) / Math.log1p(allMax) : n / rowMax;
  return Math.min(4, Math.max(1, Math.ceil(r * 4)));
}
