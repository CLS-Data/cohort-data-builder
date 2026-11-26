/* The variable list: the search box, filters, result rows, and a variable opened in place.

   Each row carries what decides whether a variable is worth a look (name, label, sweep,
   file). Everything secondary opens under the row from its own ▸ button, a few lines rather
   than a pane, so many variables stay on screen at once.

   The list holds every chosen cohort's matches, cohort after cohort (feature 007). A row is
   {cohort, row}: the cohort's key and its index row; its key is listKey's
   `<cohort>:<fileIndex>:<name>`. */

import { colourSlot } from "../core/cohorts.js";
import { loadDict } from "../core/data.js";
import { describeVariable } from "../core/details.js";
import { PAGE, page, sameLabel, searchCohorts } from "../core/search.js";
import {
  addMany,
  canSelect,
  has,
  removeMany,
  selectableItems,
  toggle,
  toItem,
} from "../core/selection.js";
import { esc, highlight, levelName } from "../core/text.js";
import {
  ensure,
  flatten,
  mergeSchemes,
  rowTopics,
  schemeIndex,
  toggle as toggleTopic,
} from "../core/topics.js";
import { renderSpine, renderTopicGrid, wireOverview } from "./overview.js";
import { saveOptions, setSelection } from "./selected.js";
import {
  cohort,
  DRAG_MIME,
  listKey,
  manifestOf,
  RETRY_EVENT,
  readyCohorts,
  selectionOf,
  state,
} from "./state.js";
import { openSuggest } from "./suggest.js";
import { switchView } from "./views.js";

const $ = (sel) => document.querySelector(sel);
const n = (x) => x.toLocaleString("en-GB");
const SELECT_ALL_MAX = 500; // as core/selection.js: beyond this "select all" is a mistake
const keyOf = listKey;
const fileOf = (e) => manifestOf(e.cohort).files[e.row[2]];
const waveOf = (e) => manifestOf(e.cohort).wave.list[e.row[3]];
/* A row's topics are indices into its own cohort's scheme. */
const topicsOf = (key) => flatten(manifestOf(key).topics);
const domainOf = (key, t) => manifestOf(key).topics.domains[topicsOf(key)[t].domain];
const entryFor = (key) => state.list.find((e) => keyOf(e) === key);
const several = () => state.chosen.length > 1;
const catalogueEntry = (key) => state.catalogue.find((d) => d.key === key) || { name: key };
const nameOf = (key) => catalogueEntry(key).name;
const slotOf = (key) =>
  colourSlot(
    key,
    state.catalogue.map((d) => d.key),
  );
const cohTag = (key) =>
  `<span class="coh-tag" data-coh="${slotOf(key)}">${esc(nameOf(key))}</span>`;
const variables = (count) => `${n(count)} variable${count === 1 ? "" : "s"}`;

/* ── Searching ───────────────────────────────────────────────────────── */

/**
 * Run the search with the current filters and redraw the list, chart and filter bar.
 * @param {{keepPlace?: boolean}} [options] keepPlace: keep the rows already shown and the
 *   scroll position (used when only the drawing changes).
 */
export function runSearch({ keepPlace = false } = {}) {
  state.results = searchCohorts(readyCohorts(), {
    query: state.query,
    wave: state.waveFilter,
    file: state.fileFilter,
    level: state.levelFilter,
    topicSel: state.topicSel,
    topicMode: state.topicMode,
    minConf: state.options.minConf,
  });
  state.list = state.results.flatMap((r) => r.matches.map((row) => ({ cohort: r.cohort, row })));
  // Level counts by name, summed over the cohorts: each cohort numbers its own levels.
  state.levelCounts = new Map();
  for (const r of state.results) {
    const levels = manifestOf(r.cohort).levels || [];
    for (const [i, count] of r.perLevel) {
      const name = i === -1 ? -1 : levels[i];
      state.levelCounts.set(name, (state.levelCounts.get(name) || 0) + count);
    }
  }
  if (!keepPlace) {
    state.shown = PAGE;
    $("#vscroll").scrollTop = 0;
  }
  renderResults();
  renderSpine(isFiltered());
  renderTopicGrid();
  renderLevelSelect();
  renderFilters();
  renderSelectAll();
}

/** The selection changed but the matches did not: redraw what shows it, keeping place. */
export function refreshSelection() {
  if (!state.results.length) return;
  renderResults();
  renderSelectAll();
}

const isFiltered = () =>
  Boolean(state.query.trim()) ||
  state.waveFilter !== null ||
  state.fileFilter !== null ||
  state.levelFilter !== null ||
  state.topicSel.length > 0;

/** Forget the filters and open rows. */
export function resetFilters() {
  Object.assign(state, {
    query: "",
    waveFilter: null,
    fileFilter: null,
    levelFilter: null,
    topicSel: [],
    topicMode: "any",
    gridExpanded: new Set(),
    expanded: new Set(),
    allValues: new Set(),
    anchor: null,
  });
  $("#q").value = "";
}

/** Take the chosen cohorts' topics and levels together: call when the choice changes. */
export function mergeChosen() {
  const ready = readyCohorts();
  state.scheme = mergeSchemes(ready.map((c) => c.manifest.topics));
  state.topics = flatten(state.scheme);
  state.domains = state.scheme?.domains || [];
  state.levels = [...new Set(ready.flatMap((c) => c.manifest.levels || []))];
}

/* Measurement level is a refinement, not a way in: a dropdown, with counts. The options'
   values are positions in state.levels, the chosen cohorts' level names. */
function renderLevelSelect() {
  const levels = state.levels;
  const sel = $("#level");
  sel.hidden = !levels.length;
  const total = [...state.levelCounts.values()].reduce((a, b) => a + b, 0);
  const opt = (k) => {
    const name = k === -1 ? -1 : levels[k];
    const count = state.levelCounts.get(name) || 0;
    const usable = count || state.levelFilter === name;
    return `<option value="${k}"${usable ? "" : " disabled"}>${esc(levelName(levels, k))} (${n(count)})</option>`;
  };
  sel.innerHTML = `<option value="">Any level (${n(total)})</option>${[...levels.keys(), -1].map(opt).join("")}`;
  const f = state.levelFilter;
  sel.value = f === null ? "" : String(f === -1 ? -1 : levels.indexOf(f));
}

function renderFilters() {
  const chips = [];
  const w = state.waveFilter;
  const named = (key, text) => (several() ? `${nameOf(key)} · ${text}` : text);
  // With several cohorts a sweep or file chip carries its cohort's mark, beside its name.
  const chipAttrs = (key) =>
    several()
      ? ` data-cohort="${esc(key)}" data-coh="${slotOf(key)}"><span class="coh-mark" aria-hidden="true"></span`
      : "";
  if (w !== null) {
    const m = manifestOf(w.cohort);
    chips.push(
      `<button class="chip" data-clear="wave" title="Show every ${esc(m.wave.term)}"${chipAttrs(w.cohort)}>${esc(named(w.cohort, m.wave.list[w.i].key))} ✕</button>`,
    );
  }
  const f = state.fileFilter;
  if (f !== null) {
    chips.push(
      `<button class="chip" data-clear="file" title="Show every file"${chipAttrs(f.cohort)}>${esc(named(f.cohort, manifestOf(f.cohort).files[f.i].name))} ✕</button>`,
    );
  }
  const idx = schemeIndex(state.scheme);
  for (const s of state.topicSel) {
    const label =
      s.kind === "d"
        ? state.domains[idx.domain.get(s.id)]?.label
        : state.topics[idx.topic.get(s.id)]?.label;
    chips.push(
      `<button class="chip chip-topic" data-unselect="${s.kind}:${esc(s.id)}" title="Remove this topic">${esc(label || s.id)} ✕</button>`,
    );
  }
  // The any/all switch, once there is something for it to combine.
  if (state.topicSel.length > 1) {
    const all = state.topicMode === "all";
    chips.push(`<span class="match-mode" role="group" aria-label="Combine topics">
      <button data-mode="any" aria-pressed="${!all}" title="Variables with any of these topics">any</button>
      <button data-mode="all" aria-pressed="${all}" title="Variables with every one of these topics">all</button>
    </span>`);
  }
  $("#active-filters").innerHTML = chips.join("");
  $("#clear-filters").hidden = !isFiltered();
  // With several cohorts, a count per cohort, each a way to its group.
  const total = variables(state.list.length);
  $("#result-count").innerHTML = several()
    ? `${total}${state.results
        .map(
          (r) =>
            ` · <button class="link-btn count-goto" data-goto="${esc(r.cohort)}" title="Go to ${esc(nameOf(r.cohort))}">${esc(nameOf(r.cohort))} ${n(r.matches.length)}</button>`,
        )
        .join("")}`
    : total;
}

/* What a filter on one cohort's sweep or file is called, for the other cohorts' headings. */
function filterName() {
  const w = state.waveFilter;
  if (w) return `${nameOf(w.cohort)} · ${manifestOf(w.cohort).wave.list[w.i].key}`;
  const f = state.fileFilter;
  return f ? `${nameOf(f.cohort)} · ${manifestOf(f.cohort).files[f.i].name}` : "";
}

/* A chosen cohort's heading in the list: its mark, full name, and count or state. */
function groupHtml(key) {
  const c = cohort(key);
  const name = catalogueEntry(key).fullName || nameOf(key);
  let what;
  if (!c || c.status === "loading")
    what = `<span class="v-group-n">Loading ${esc(nameOf(key))}…</span>`;
  else if (c.status === "failed") {
    what = `<span class="v-group-n vm-warn">Could not load ${esc(nameOf(key))}.</span>
      <button class="link-btn" data-retry="${esc(key)}">Retry</button>`;
  } else {
    const r = state.results.find((x) => x.cohort === key);
    const count = r ? r.matches.length : 0;
    if (r?.filteredElsewhere) {
      what = `<span class="v-group-n">filtered to ${esc(filterName())}</span>
        <button class="link-btn" data-clear-filter>Clear filter</button>`;
    } else if (!count && r?.untagged && state.topicSel.length) {
      what = `<span class="v-group-n">no topic tags</span>`;
    } else {
      what = `<span class="v-group-n">${count ? variables(count) : "no matches"}</span>`;
    }
  }
  return `<li class="v-group" data-cohort="${esc(key)}" data-coh="${slotOf(key)}">
    <span class="coh-mark" aria-hidden="true"></span><strong>${esc(name)}</strong> ${what}</li>`;
}

/* ── The list ────────────────────────────────────────────────────────── */

function rowHtml(e, i, q) {
  const { row } = e;
  const m = manifestOf(e.cohort);
  const file = fileOf(e);
  const key = keyOf(e);
  const open = state.expanded.has(key);
  const wave = waveOf(e);
  const label = row[1] || "No label";
  const why = canSelect(row, file, m.identifier);
  const isId = why && file.hasId; // the identifier: in every download already
  const isIn = !why && has(selectionOf(e.cohort), file.name, row[0]);
  const mark = isIn || isId ? "✓" : why ? "" : "＋";
  const attrs = why
    ? `aria-disabled="true" title="${esc(why)}"`
    : `aria-pressed="${isIn}" title="Click to ${isIn ? "remove" : "select"} · Shift-click for a range" draggable="true"`;
  // Up to two topics, strongest first, and a stripe in the colour of the strongest's domain.
  const ts = m.topics ? rowTopics(row, state.options.minConf) : [];
  const topics = ts.length ? topicsOf(e.cohort) : [];
  const tags = ts
    .slice(0, 2)
    .map(([t]) => {
      const d = domainOf(e.cohort, t);
      return `<span class="topic-chip" data-domain="${esc(d.id)}"
       title="${esc(d.label)} › ${esc(topics[t].label)}">${esc(topics[t].label)}</span>`;
    })
    .join("");
  const stripe = ts.length ? ` data-domain="${esc(domainOf(e.cohort, ts[0][0]).id)}"` : "";
  return `<li class="vrow${open ? " is-open" : ""}${isIn ? " is-in" : ""}${why ? " is-fixed" : ""}" data-key="${esc(key)}" data-cohort="${esc(e.cohort)}"${stripe}>
    <div class="vrow-main">
      <button class="vrow-btn" data-i="${i}" ${attrs}>
        <span class="v-check" aria-hidden="true">${mark}</span>
        <span class="v-name" title="${esc(row[0])}">${highlight(row[0], q)}</span>
        <span class="v-label" title="${esc(label)}">${several() ? `${cohTag(e.cohort)} ` : ""}${highlight(label, q)}</span>
        <span class="v-wave" title="${esc(wave.label || "")}">${esc(wave.key)}</span>
        <span class="v-file" title="${esc(file.description || file.name)}">${esc(file.name)}</span>
        <span class="v-topics">${tags}</span>
      </button>
      <button class="v-expand" data-expand="${i}" aria-expanded="${open}"
          ${open ? `aria-controls="more-${esc(key)}"` : ""}
          aria-label="${open ? "Hide" : "Show"} details for ${esc(row[0])}"
          title="${open ? "Hide" : "Show"} details">${open ? "▾" : "▸"}</button>
    </div>
    ${open ? `<div class="vrow-more" id="more-${esc(key)}">${moreHtml(e)}</div>` : ""}
  </li>`;
}

/* The sweep term heading the list: the chosen cohorts' own, or "sweep" when they differ. */
function sweepTerm() {
  const terms = new Set(readyCohorts().map((c) => c.manifest.wave.term));
  return terms.size === 1 ? [...terms][0] : "sweep";
}

/** Draw the result rows that fit, the "show more" button and the empty-state message. */
export function renderResults() {
  const q = state.query.trim();
  const { rows, left, next } = page(state.list, state.shown);
  const head = `<li class="vhead" aria-hidden="true"><span></span><span>Variable</span><span>Label</span>
         <span>${esc(sweepTerm())}</span><span class="v-file">File</span><span class="v-topics">${state.topics.length ? "Topics" : ""}</span><span></span></li>`;
  if (several()) {
    // A heading per chosen cohort, then its rows; a cohort whose rows start beyond those
    // shown waits for "show more".
    const parts = [head];
    let start = 0;
    for (const key of state.chosen) {
      if (start >= rows.length && start > 0 && left > 0) break;
      parts.push(groupHtml(key));
      const count = state.results.find((r) => r.cohort === key)?.matches.length || 0;
      for (let i = start; i < Math.min(start + count, rows.length); i++) {
        parts.push(rowHtml(rows[i], i, q));
      }
      start += count;
    }
    $("#results").innerHTML = parts.join("");
  } else if (!state.list.length) {
    const c = cohort(state.chosen[0]);
    $("#results").innerHTML =
      c?.status === "ready"
        ? `<li class="vempty">No variables match.
      <button class="link-btn" data-clear-all>Clear the filters</button></li>`
        : groupHtml(state.chosen[0]).replace('class="v-group"', 'class="v-group vempty"');
  } else {
    $("#results").innerHTML = head + rows.map((e, i) => rowHtml(e, i, q)).join("");
  }
  const more = $("#more");
  more.hidden = left <= 0;
  more.innerHTML =
    left > 0
      ? `<button class="btn" id="show-more">Show ${n(next)} more</button>
         <span>${n(rows.length)} of ${n(state.list.length)} shown</span>`
      : "";
  // Rows open before their dictionary arrived fill in now.
  for (const e of rows) if (state.expanded.has(keyOf(e))) fillMore(e);
}

/* ── A variable, opened ──────────────────────────────────────────────── */

const dictId = (e) => `${e.cohort}/${fileOf(e).name}`;
const failed = new Map(); // dictionaries that could not be loaded: id -> message

/* The row's dictionary entry; undefined while not loaded, null when it has none. */
function dictEntry(e) {
  const dict = state.dictCache.get(dictId(e));
  if (!dict) return failed.has(dictId(e)) ? null : undefined;
  return dict.variables.find((v) => v.variable === e.row[0]) || null;
}

async function fillMore(e) {
  if (dictEntry(e) !== undefined) return;
  try {
    await loadDict(fetch, e.cohort, fileOf(e).name, state.dictCache);
  } catch (err) {
    failed.set(dictId(e), err.message);
  }
  const el = document.getElementById(`more-${keyOf(e)}`);
  if (el && state.expanded.has(keyOf(e))) el.innerHTML = moreHtml(e);
}

const valueItem = (v) => `<li><span class="vm-code">${esc(v.code)}</span> ${esc(v.label)}</li>`;

function valuesHtml(e, d) {
  if (d.isIdentifier) {
    return `<p class="vm-note">The identifier every file is merged on: always the first column of a download.</p>`;
  }
  if (d.note) {
    return `<p class="vm-note">${d.note === "continuous" ? "A continuous measure: no value labels." : "No value labels recorded."}</p>`;
  }
  // Answers first; the missing codes after, on a quieter line of their own.
  const key = keyOf(e);
  const all = state.allValues.has(key);
  const answers = all ? [...d.answers, ...d.more] : d.answers;
  let more = "";
  if (d.more.length) {
    more = `<li><button class="link-btn" data-values="${esc(key)}">${all ? "fewer" : `+ ${d.more.length} more`}</button></li>`;
  }
  const naItem = (v) =>
    v.lossy
      ? `<li class="vm-lossy" title="Declared missing, but labelled like an answer: converting to NA loses it"><span class="vm-code">${esc(v.code)}</span> ${esc(v.label)} ⚠</li>`
      : valueItem(v);
  const kept = d.kept
    .map(([x, l]) => `<span class="vm-code">${esc(x)}</span> ${esc(l)}`)
    .join(", ");
  return `${answers.length ? `<ul class="vm-values">${answers.map(valueItem).join("")}${more}</ul>` : ""}
    ${d.missing.length ? `<ul class="vm-values is-na" title="Missing-value codes"><li class="vm-key">Missing</li>${d.missing.map(naItem).join("")}</ul>` : ""}
    ${kept ? `<p class="vm-note vm-kept" title="Negative, but labelled as an answer: never converted to NA">Kept as answers: ${kept}</p>` : ""}`;
}

function sameLabelHtml(e) {
  const { rows, more } = sameLabel(cohort(e.cohort).labelIndex, e.row);
  if (!rows.length) return "";
  const links = rows
    .map((row) => ({ cohort: e.cohort, row }))
    .map(
      (
        r,
      ) => `<button class="vm-also-link" data-jump="${esc(keyOf(r))}" title="${esc(fileOf(r).name)}">
        <span class="v-wave">${esc(waveOf(r).key)}</span> ${esc(r.row[0])}</button>`,
    )
    .join("");
  return `<div class="vm-also"><span class="vm-key">Same label</span>${links}${more ? `<span class="vm-dim">+ ${more} more</span>` : ""}</div>`;
}

/* Every topic in the dictionary entry, with its confidence; those under the threshold are
   dimmed rather than hidden. Clicking one filters by it. The tags come from a language
   model, so the line ends with a button to suggest better ones (see suggest.js). */
function topicsHtml(entry, e) {
  const scheme = manifestOf(e.cohort).topics;
  if (!scheme) return "";
  const topics = topicsOf(e.cohort);
  const byId = schemeIndex(scheme).topic;
  const tags = (entry.topics || [])
    .filter(([id]) => byId.has(id))
    .map(([id, conf]) => {
      const i = byId.get(id);
      const pct = Math.round(conf * 100);
      const domain = domainOf(e.cohort, i);
      return `<button class="vm-topic${pct < state.options.minConf ? " is-below" : ""}" data-topic-open="${esc(id)}"
        data-domain="${esc(domain.id)}" title="${esc(domain.label)} › ${esc(topics[i].label)} · filter by this topic">${esc(topics[i].label)} <span class="vm-pct">${pct}%</span></button>`;
    })
    .join("");
  const suggest = `<button class="link-btn vm-suggest" data-suggest="${esc(keyOf(e))}">${tags ? "Suggest a tag change" : "Suggest a tag"}</button>`;
  return `<div class="vm-topics">${tags ? `<span class="vm-key">Topics</span>${tags}` : ""}${suggest}</div>`;
}

function moreHtml(e) {
  const { row } = e;
  const m = manifestOf(e.cohort);
  const entry = dictEntry(e);
  if (entry === undefined) return `<p class="vm-note">Loading…</p>`;
  const file = fileOf(e);
  if (entry === null) {
    const why = failed.get(dictId(e)) || `${row[0]} is not in the ${file.name} dictionary.`;
    return `<p class="vm-note vm-warn">${esc(why)}</p>`;
  }
  const d = describeVariable(entry, file, m.identifier);
  const facts = d.isIdentifier
    ? esc(file.name)
    : d.facts
        .map((f) =>
          f.detail
            ? `${esc(f.value)} <span class="vm-dim">— ${esc(f.detail)}</span>`
            : esc(f.name === "Position" ? `position ${f.value}` : f.value),
        )
        .join(" · ");
  const whose = several()
    ? `<p class="vm-note vm-cohort">${cohTag(e.cohort)} ${esc(catalogueEntry(e.cohort).fullName || nameOf(e.cohort))}</p>`
    : "";
  return `${whose}${valuesHtml(e, d)}
    ${topicsHtml(entry, e)}
    ${sameLabelHtml(e)}
    ${file.hasId ? "" : `<p class="vm-note vm-warn">This file has no ${esc(m.identifier)} column, so it cannot be merged.</p>`}
    <div class="vm-meta"><span>${facts}</span>
      <button class="link-btn" data-file-open="${esc(e.cohort)}:${row[2]}">all in this file</button></div>`;
}

/* Redrawing a row replaces its buttons; a keyboard user stays where they were. */
function toggleRow(e) {
  const key = keyOf(e);
  const had = document.activeElement?.matches?.(".v-expand");
  if (state.expanded.has(key)) state.expanded.delete(key);
  else state.expanded.add(key);
  const li = document.querySelector(`.vrow[data-key="${CSS.escape(key)}"]`);
  if (li) li.outerHTML = rowHtml(e, state.list.indexOf(e), state.query.trim());
  if (state.expanded.has(key)) fillMore(e);
  if (had) {
    document
      .querySelector(`.vrow[data-key="${CSS.escape(key)}"] .v-expand`)
      ?.focus({ preventScroll: true });
  }
}

/* ── Selecting ───────────────────────────────────────────────────────── */

/* The selectable rows among some list entries, as selection items, cohort by cohort. */
function selectableByCohort(entries) {
  const out = new Map();
  for (const e of entries) {
    if (!out.has(e.cohort)) out.set(e.cohort, []);
    out.get(e.cohort).push(e.row);
  }
  return [...out].map(([key, rows]) => [key, selectableItems(rows, manifestOf(key))]);
}

/* Add or remove items, cohort by cohort; returns how many changed, and per cohort. */
function changeMany(groups, adding) {
  let changed = 0;
  const per = [];
  for (const [key, items] of groups) {
    const r = adding
      ? addMany(selectionOf(key), items, manifestOf(key))
      : removeMany(selectionOf(key), items);
    changed += r.changed;
    if (r.changed) per.push(`${nameOf(key)} ${n(r.changed)}`);
    setSelection(key, r.selection);
  }
  lastPer = per.length > 1 ? ` (${per.join(" · ")})` : "";
  return changed;
}
let lastPer = ""; // the per-cohort numbers of the last changeMany, for sayCount

function renderSelectAll() {
  const btn = $("#select-all");
  const groups = selectableByCohort(state.list);
  const count = groups.reduce((a, [, items]) => a + items.length, 0);
  btn.hidden = !count || count > SELECT_ALL_MAX;
  if (btn.hidden) return;
  const allIn = groups.every(([key, items]) =>
    items.every((it) => has(selectionOf(key), it.file, it.name)),
  );
  btn.dataset.mode = allIn ? "remove" : "add";
  btn.textContent = `${allIn ? "Remove" : "Select"} all ${n(count)}`;
}

/* Said beside the count, and to a screen reader, when one click changed several rows. */
let sayTimer;
function sayCount(change) {
  const el = $("#select-status");
  const m = Math.abs(change);
  el.textContent = change
    ? `${change > 0 ? "Added" : "Removed"} ${n(m)} variable${m === 1 ? "" : "s"}${lastPer}`
    : "";
  clearTimeout(sayTimer);
  sayTimer = setTimeout(() => {
    el.textContent = "";
  }, 5000);
}

function selectAll() {
  const adding = $("#select-all").dataset.mode !== "remove";
  const changed = changeMany(selectableByCohort(state.list), adding);
  sayCount(adding ? changed : -changed);
}

/* A click puts a row in the selection or takes it out (Cmd- or Ctrl-click the same: a
   click never clears the others). Shift-click carries every row between it and the last
   row clicked the way the clicked row goes: in, or out. */
function selectRow(btn, ev) {
  const e = state.list[Number(btn.dataset.i)];
  if (!e) return;
  const key = keyOf(e);
  const had = document.activeElement === btn;
  const anchor = state.anchor;
  state.anchor = key;
  if (btn.getAttribute("aria-disabled") === "true") return;
  const m = manifestOf(e.cohort);
  const item = toItem(e.row, m);
  const from = anchor ? state.list.findIndex((x) => keyOf(x) === anchor) : -1;
  if (ev.shiftKey && from >= 0 && anchor !== key) {
    window.getSelection()?.removeAllRanges(); // Shift-click also extends the text selection
    const to = state.list.indexOf(e);
    const range = state.list.slice(Math.min(from, to), Math.max(from, to) + 1);
    const adding = !has(selectionOf(e.cohort), item.file, item.name);
    const changed = changeMany(selectableByCohort(range), adding);
    if (changed) sayCount(adding ? changed : -changed);
  } else {
    setSelection(e.cohort, toggle(selectionOf(e.cohort), item, m).selection);
  }
  if (had) {
    document
      .querySelector(`.vrow[data-key="${CSS.escape(key)}"] .vrow-btn`)
      ?.focus({ preventScroll: true });
  }
}

/**
 * Add a variable dragged from the list: the item {@link toItem} made, with its cohort.
 * Without a cohort it goes to the one chosen cohort, if only one is chosen.
 * @param {{cohort: string, name: string, file: string}} item The dropped item.
 */
export function addDropped(item) {
  // An item without a cohort (from an older page) can only mean the one being searched.
  const key = item?.cohort ?? (state.chosen.length === 1 ? state.chosen[0] : undefined);
  if (cohort(key)?.status !== "ready") return;
  setSelection(key, addMany(selectionOf(key), [item], manifestOf(key)).selection);
}

/* Drag a row onto the Selection tab to add it. */
function wireDrag() {
  $("#results").addEventListener("dragstart", (e) => {
    const btn = e.target.closest?.(".vrow-btn");
    const entry = btn && state.list[Number(btn.dataset.i)];
    if (!entry) return;
    e.dataTransfer.setData(DRAG_MIME, JSON.stringify(toItem(entry.row, manifestOf(entry.cohort))));
    e.dataTransfer.effectAllowed = "copy";
  });
  const tab = $('.view-tab[data-view="basket"]');
  tab.addEventListener("dragover", (e) => {
    if (e.dataTransfer.types.includes(DRAG_MIME)) e.preventDefault();
  });
  tab.addEventListener("drop", (e) => {
    e.preventDefault();
    try {
      addDropped(JSON.parse(e.dataTransfer.getData(DRAG_MIME)));
    } catch {
      // not one of our rows
    }
  });
}

/* Go to another variable: search for its label, which brings the whole same-label family
   into the list together, and open it. */
async function jumpTo(key) {
  const [c] = key.split(":");
  const row = cohort(c)?.vars.find((r) => keyOf({ cohort: c, row: r }) === key);
  if (!row) return;
  // Its details first, so the row is scrolled to at its full height.
  await fillMore({ cohort: c, row });
  Object.assign(state, {
    query: row[1],
    waveFilter: null,
    fileFilter: null,
    levelFilter: null,
    topicSel: [],
  });
  state.expanded = new Set([key]);
  $("#q").value = row[1];
  runSearch();
  document
    .querySelector(`.vrow[data-key="${CSS.escape(key)}"]`)
    ?.scrollIntoView({ block: "nearest" });
}

/* Scroll to a cohort's heading, showing rows up to it first if need be. */
function goToGroup(key) {
  let start = 0;
  for (const r of state.results) {
    if (r.cohort === key) break;
    start += r.matches.length;
  }
  if (start >= state.shown) {
    state.shown = start + PAGE;
    renderResults();
  }
  document
    .querySelector(`#results .v-group[data-cohort="${CSS.escape(key)}"]`)
    ?.scrollIntoView({ block: "start" });
}

/**
 * Show every variable in one file.
 * @param {string} key The cohort.
 * @param {number} fileIdx Index into its manifest's files.
 */
export function filterToFile(key, fileIdx) {
  switchView("search");
  Object.assign(state, {
    query: "",
    waveFilter: null,
    fileFilter: { cohort: key, i: fileIdx },
    levelFilter: null,
  });
  $("#q").value = "";
  runSearch();
  $("#filterbar").scrollIntoView({ block: "start" });
}

/* Change the topic filter with `change` (toggle or ensure from core/topics.js) and search
   again. A domain with one of its topics chosen opens, so the choice is never hidden. */
function selectTopic(change, kind, id) {
  const { domainOf: domainOfTopic } = schemeIndex(state.scheme);
  state.topicSel = change(state.topicSel, kind, id, domainOfTopic);
  if (kind === "t" && state.topicSel.some((s) => s.kind === "t" && s.id === id)) {
    state.gridExpanded.add(domainOfTopic.get(id));
  }
  runSearch();
}

function clearAll() {
  Object.assign(state, {
    query: "",
    waveFilter: null,
    fileFilter: null,
    levelFilter: null,
    topicSel: [],
  });
  $("#q").value = "";
  runSearch();
}

/** Attach the list's event handlers. Call once. */
export function wireResults() {
  let timer;
  $("#q").addEventListener("input", (e) => {
    clearTimeout(timer);
    timer = setTimeout(() => {
      state.query = e.target.value;
      runSearch();
    }, 120);
  });

  $("#results").addEventListener("click", (e) => {
    const expand = e.target.closest("[data-expand]");
    if (expand) return toggleRow(state.list[Number(expand.dataset.expand)]);
    const vals = e.target.closest("[data-values]");
    if (vals) {
      const key = vals.dataset.values;
      if (state.allValues.has(key)) state.allValues.delete(key);
      else state.allValues.add(key);
      const entry = entryFor(key);
      const el = document.getElementById(`more-${key}`);
      if (entry && el) el.innerHTML = moreHtml(entry);
      return;
    }
    const tag = e.target.closest("[data-topic-open]");
    if (tag) return selectTopic(ensure, "t", tag.dataset.topicOpen);
    const jump = e.target.closest("[data-jump]");
    if (jump) return jumpTo(jump.dataset.jump);
    const file = e.target.closest("[data-file-open]");
    if (file) {
      const [key, i] = file.dataset.fileOpen.split(":");
      return filterToFile(key, Number(i));
    }
    const suggest = e.target.closest("[data-suggest]");
    if (suggest) {
      const entry = entryFor(suggest.dataset.suggest);
      if (entry && dictEntry(entry)) {
        openSuggest(dictEntry(entry), fileOf(entry).name, manifestOf(entry.cohort), suggest);
      }
      return;
    }
    if (e.target.closest("[data-clear-all]")) return clearAll();
    if (e.target.closest("[data-clear-filter]")) {
      Object.assign(state, { waveFilter: null, fileFilter: null });
      return runSearch();
    }
    const retry = e.target.closest("[data-retry]");
    if (retry) {
      document.dispatchEvent(new CustomEvent(RETRY_EVENT, { detail: retry.dataset.retry }));
      return;
    }
    const btn = e.target.closest(".vrow-btn");
    if (btn) selectRow(btn, e);
  });
  $("#select-all").addEventListener("click", selectAll);
  $("#result-count").addEventListener("click", (e) => {
    const b = e.target.closest("[data-goto]");
    if (b) goToGroup(b.dataset.goto);
  });
  wireDrag();

  $("#more").addEventListener("click", (e) => {
    if (!e.target.closest("#show-more")) return;
    state.shown += PAGE;
    renderResults();
  });

  const sameWave = (key, i) => state.waveFilter?.cohort === key && state.waveFilter.i === i;
  wireOverview({
    onWave: (key, i) => {
      state.waveFilter = sameWave(key, i) ? null : { cohort: key, i };
      runSearch();
    },
    onTopic: (kind, id) => selectTopic(toggleTopic, kind, id),
    // A cell: that topic at that sweep. The same cell again lets go of the sweep only.
    onCell: (kind, id, key, i) => {
      const already =
        sameWave(key, i) && state.topicSel.some((s) => s.kind === kind && s.id === id);
      state.waveFilter = already ? null : { cohort: key, i };
      selectTopic(ensure, kind, id);
    },
    onOptions: () => {
      saveOptions();
      runSearch();
    },
  });

  $("#active-filters").addEventListener("click", (e) => {
    const chip = e.target.closest("[data-clear]");
    if (chip) {
      state[`${chip.dataset.clear}Filter`] = null;
      return runSearch();
    }
    const un = e.target.closest("[data-unselect]");
    if (un) {
      const [kind, ...id] = un.dataset.unselect.split(":");
      return selectTopic(toggleTopic, kind, id.join(":"));
    }
    const mode = e.target.closest("[data-mode]");
    if (mode) {
      state.topicMode = mode.dataset.mode;
      runSearch();
    }
  });

  $("#level").addEventListener("change", (e) => {
    const v = e.target.value;
    state.levelFilter = v === "" ? null : v === "-1" ? -1 : state.levels[Number(v)];
    runSearch();
  });
  $("#clear-filters").addEventListener("click", clearAll);
}
