/* The single mutable state object every view reads and writes. Touches no DOM and imports
   nothing, so it can never take part in an import cycle. */

/** MIME type a dragged variable row carries. */
export const DRAG_MIME = "application/x-cohort-data-builder-variable";

/** Everything the interface knows about the current page. */
export const state = {
  catalogue: [], // data/datasets.json: every cohort on the site
  manifest: null, // data/<key>/manifest.json: the cohort being browsed
  vars: [], // index rows: [name, label, fileIdx, waveIdx, levelIdx, topics?]
  dictCache: new Map(), // dictionaries loaded so far, keyed "<key>/<file>"
  query: "",
  waveFilter: null, // sweep index, or null
  fileFilter: null, // file index, or null
  levelFilter: null, // level index, -1 for unrecorded, or null
  // The topic filter: items {kind: "d"|"t", i} combined by topicMode ("any" or "all").
  topicSel: [],
  topicMode: "any",
  gridExpanded: new Set(), // domains opened in the topic grid
  tally: null, // counts from the last search pass
  topics: [], // [{id, label, description, domain}] across all domains
  domains: [], // manifest.topics.domains
  levelCounts: new Map(),
  matches: [],
  shown: 200, // rows drawn; "show more" raises it
  expanded: new Set(), // rows opened in place, by "<fileIndex>:<name>"
  anchor: null, // the row a Shift-click range starts from, by the same key
  allValues: new Set(), // opened rows showing every value label
  labelIndex: new Map(), // normalised label -> rows, for "same label"
  // The selection, in the order picked: {name, label, file, wave, column}. Only `column`
  // (the output name) may be edited. Kept per cohort.
  bundle: [],
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
