/* Topics: the flattened scheme, a row's tags, the topic filter and the overview counts.
   No DOM and no shared state.

   A selection is a list of items {kind: "d"|"t", id}, each a whole domain (topic area) or
   one topic, by id; localSel turns it into one cohort's indices. A row matches an item if
   it carries that topic (or any topic of that domain) at or above the confidence threshold. Items combine by "any" (the union: smoking or
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

/* The topic filter is held by id, so one filter applies to every chosen cohort however
   each cohort's scheme orders its topics (feature 007). */
const same = (a, b) => a.kind === b.kind && a.id === b.id;
const domainOf = (item, domainOfTopic) =>
  item.kind === "d" ? item.id : domainOfTopic.get(item.id);

/**
 * Select an item, or deselect it if it is selected. A domain and its own topics are never
 * selected together: choosing a topic replaces its selected domain, and choosing a domain
 * replaces any of its selected topics.
 * @param {{kind: string, id: string}[]} sel The current selection; not changed.
 * @param {"d"|"t"} kind Domain or topic.
 * @param {string} id Its id.
 * @param {Map<string, string>} domainOfTopic Each topic id's domain id
 *   ({@link schemeIndex}`.domainOf`).
 * @returns {{kind: string, id: string}[]} The new selection.
 */
export function toggle(sel, kind, id, domainOfTopic) {
  const item = { kind, id };
  if (sel.some((s) => same(s, item))) return sel.filter((s) => !same(s, item));
  const d = domainOf(item, domainOfTopic);
  const clash = (s) =>
    kind === "t"
      ? s.kind === "d" && s.id === d
      : s.kind === "t" && domainOf(s, domainOfTopic) === d;
  return [...sel.filter((s) => !clash(s)), item];
}

/**
 * Select an item if it is not selected already; never deselects.
 * @param {{kind: string, id: string}[]} sel The current selection; not changed.
 * @param {"d"|"t"} kind Domain or topic.
 * @param {string} id Its id.
 * @param {Map<string, string>} domainOfTopic As for {@link toggle}.
 * @returns {{kind: string, id: string}[]} The new selection, or `sel` itself if unchanged.
 */
export const ensure = (sel, kind, id, domainOfTopic) =>
  sel.some((s) => same(s, { kind, id })) ? sel : toggle(sel, kind, id, domainOfTopic);

const indexCache = new WeakMap();
const NO_SCHEME = { topic: new Map(), domain: new Map(), domainOf: new Map() };

/**
 * A scheme's ids and where they are in it.
 * @param {{domains: object[]}|undefined} scheme A manifest's `topics`, if any.
 * @returns {{topic: Map<string, number>, domain: Map<string, number>,
 *   domainOf: Map<string, string>}} Topic id to its index in {@link flatten}'s list,
 *   domain id to its index, and topic id to its domain's id. Empty without a scheme.
 */
export function schemeIndex(scheme) {
  if (!scheme) return NO_SCHEME;
  if (!indexCache.has(scheme)) {
    const topic = new Map();
    const domainOfTopic = new Map();
    flatten(scheme).forEach((t, i) => {
      topic.set(t.id, i);
      domainOfTopic.set(t.id, scheme.domains[t.domain].id);
    });
    const domain = new Map(scheme.domains.map((d, i) => [d.id, i]));
    indexCache.set(scheme, { topic, domain, domainOf: domainOfTopic });
  }
  return indexCache.get(scheme);
}

/**
 * The topic filter in one scheme's indices, as {@link passes} and the tally use them.
 * @param {{kind: string, id: string}[]} sel The filter, by id.
 * @param {{domains: object[]}|undefined} scheme One cohort's scheme.
 * @returns {{kind: string, i: number}[]} The same items by index; -1 where the scheme has no
 *   such topic or domain, which no row carries.
 */
export function localSel(sel, scheme) {
  const idx = schemeIndex(scheme);
  return sel.map((s) => ({
    kind: s.kind,
    i: (s.kind === "d" ? idx.domain : idx.topic).get(s.id) ?? -1,
  }));
}

/**
 * One scheme holding every domain and topic of several, matched by id: what the overview
 * lists when several cohorts are chosen.
 * @param {({domains: object[]}|undefined)[]} schemes The chosen cohorts' schemes.
 * @returns {{domains: object[]}|undefined} Domains in first-seen order, each with its
 *   topics in first-seen order; labels and descriptions from the first scheme that has
 *   them. Undefined when no cohort has a scheme.
 */
export function mergeSchemes(schemes) {
  const present = schemes.filter(Boolean);
  if (!present.length) return undefined;
  if (present.length === 1) return present[0];
  const domains = new Map();
  for (const scheme of present) {
    for (const d of scheme.domains) {
      if (!domains.has(d.id)) domains.set(d.id, { ...d, topics: [] });
      const into = domains.get(d.id);
      for (const t of d.topics) {
        if (!into.topics.some((x) => x.id === t.id)) into.topics.push(t);
      }
    }
  }
  return { name: present[0].name, domains: [...domains.values()] };
}

/**
 * Whether a row with these topics passes the topic filter.
 * @param {{kind: string, i: number}[]} sel The selection in this scheme's indices
 *   ({@link localSel}); empty passes everything.
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
