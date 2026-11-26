/* The single mutable state object every view reads and writes, and a few read-only helpers
   over it. Touches no DOM and imports nothing, so it can never take part in an import cycle.

   Several cohorts can be chosen at once (feature 007). Each loaded cohort lives in
   `cohorts`; `chosen` lists the ones being searched, in catalogue order. */

/** The event fired, with a cohort key as detail, when a Retry button is pressed. */
export const RETRY_EVENT = "cohort-data-builder:retry";

/** MIME type a dragged variable row carries. */
export const DRAG_MIME = "application/x-cohort-data-builder-variable";

/** Everything the interface knows about the current page. */
export const state = {
  catalogue: [], // data/datasets.json: every cohort on the site
  // Loaded cohorts by key: {manifest, vars, labelIndex, status: "loading"|"ready"|"failed",
  // error?}. A cohort is loaded when first chosen, or when it has a saved selection.
  cohorts: new Map(),
  chosen: [], // the keys being searched, in catalogue order; never empty once started
  dictCache: new Map(), // dictionaries loaded so far, keyed "<key>/<file>"
  query: "",
  // {cohort, i}: one cohort's sweep; {col, label, sweeps: {cohort: i}}: one age on the
  // several-cohort axis, each cohort's sweep there; or null.
  waveFilter: null,
  fileFilter: null, // {cohort, i}: one cohort's file, or null
  levelFilter: null, // a level name, -1 for unrecorded, or null
  // The topic filter: items {kind: "d"|"t", id} combined by topicMode ("any" or "all").
  topicSel: [],
  topicMode: "any",
  gridExpanded: new Set(), // domain ids opened in the topic grid
  // The chosen cohorts' topic schemes merged by id (core/topics.js mergeSchemes), and its
  // flattened topics and domains: what the topic rows and filter chips list.
  scheme: undefined,
  topics: [],
  domains: [],
  levels: [], // the chosen cohorts' level names, merged in first-seen order
  levelCounts: new Map(), // level name (or -1) -> matches, ignoring the level filter
  // The last search: one result per chosen cohort (core/search.js searchCohorts), and every
  // matching row as {cohort, row} in list order.
  results: [],
  list: [],
  shown: 200, // rows drawn; "show more" raises it
  expanded: new Set(), // rows opened in place, by listKey
  anchor: null, // the row a Shift-click range starts from, by listKey
  allValues: new Set(), // opened rows showing every value label
  // The selection, per cohort, each in the order picked: {name, label, file, wave, column,
  // cohort}. Only `column` (the output name) may be edited. Kept for cohorts not chosen too.
  bundles: new Map(),
  // Missing codes stay as supplied unless asked: converting them can lose answers.
  options: {
    languages: ["r", "python"],
    missingToNa: false,
    minConf: 50,
    gridOpen: false,
    gridShade: "row",
    outputFormat: "csv",
    panelOpen: false,
    panelGroup: "wave",
  },
  view: "search",
};

/**
 * A loaded cohort.
 * @param {string} key The cohort key.
 * @returns {{manifest: object, vars: Array[], labelIndex: Map, status: string}|undefined}
 *   The cohort, if it has been asked for.
 */
export const cohort = (key) => state.cohorts.get(key);

/**
 * The chosen cohorts that have loaded, in catalogue order.
 * @returns {{key: string, manifest: object, vars: Array[], labelIndex: Map}[]} Each with
 *   its key.
 */
export const readyCohorts = () =>
  state.chosen
    .map((key) => ({ key, ...state.cohorts.get(key) }))
    .filter((c) => c.status === "ready");

/**
 * The manifest of a loaded cohort.
 * @param {string} key The cohort key.
 * @returns {object} Its manifest.
 */
export const manifestOf = (key) => state.cohorts.get(key).manifest;

/**
 * The key a result row is known by in the list.
 * @param {{cohort: string, row: Array}} entry A list entry.
 * @returns {string} `<cohort>:<fileIndex>:<name>`.
 */
export const listKey = ({ cohort: c, row }) => `${c}:${row[2]}:${row[0]}`;

/**
 * Every selected variable, cohort by cohort in catalogue order.
 * @returns {object[]} The entries of every cohort's selection.
 */
export function allSelected() {
  const order = state.catalogue.map((d) => d.key);
  return [...state.bundles.keys()]
    .sort((a, b) => order.indexOf(a) - order.indexOf(b))
    .flatMap((k) => state.bundles.get(k));
}

/**
 * One cohort's selection.
 * @param {string} key The cohort key.
 * @returns {object[]} Its selection; empty if it has none.
 */
export const selectionOf = (key) => state.bundles.get(key) || [];
