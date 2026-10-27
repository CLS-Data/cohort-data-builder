/* The variable list: the search box, filters, result rows, and a variable opened in place.

   Each row carries what decides whether a variable is worth a look (name, label, sweep,
   file). Everything secondary opens under the row from its own ▸ button, a few lines rather
   than a pane, so many variables stay on screen at once. */

import { loadDict } from "../core/data.js";
import { describeVariable } from "../core/details.js";
import { buildLabelIndex, filterVariables, PAGE, page, sameLabel } from "../core/search.js";
import {
  addMany,
  canSelect,
  has,
  rangeBetween,
  removeMany,
  rowKey,
  selectAllState,
  selectableItems,
  toggle,
  toItem,
} from "../core/selection.js";
import { esc, highlight, levelName } from "../core/text.js";
import { ensure, flatten, rowTopics, toggle as toggleTopic } from "../core/topics.js";
import { renderSpine, renderTopicGrid, wireOverview } from "./overview.js";
import { saveOptions, setSelection } from "./selected.js";
import { DRAG_MIME, state } from "./state.js";
import { switchView } from "./views.js";

const $ = (sel) => document.querySelector(sel);
const n = (x) => x.toLocaleString("en-GB");
const keyOf = rowKey;
const waveKey = (i) => state.manifest.wave.list[i].key;
const fileOf = (row) => state.manifest.files[row[2]];
const domainOf = (t) => state.domains[state.topics[t].domain];

/* ── Searching ───────────────────────────────────────────────────────── */

/**
 * Run the search with the current filters and redraw the list, chart and filter bar.
 * @param {{keepPlace?: boolean}} [options] keepPlace: keep the rows already shown and the
 *   scroll position (used when only the drawing changes).
 */
export function runSearch({ keepPlace = false } = {}) {
  const r = filterVariables(state.vars, state.manifest, {
    query: state.query,
    wave: state.waveFilter,
    file: state.fileFilter,
    level: state.levelFilter,
    topicSel: state.topicSel,
    topicMode: state.topicMode,
    minConf: state.options.minConf,
  });
  state.matches = r.matches;
  state.levelCounts = r.perLevel;
  state.tally = r.tally;
  if (!keepPlace) {
    state.shown = PAGE;
    $("#vscroll").scrollTop = 0;
  }
  renderResults();
  renderSpine(r.perWave, isFiltered());
  renderTopicGrid();
  renderLevelSelect();
  renderFilters();
  renderSelectAll();
}

/** The selection changed but the matches did not: redraw what shows it, keeping place. */
export function refreshSelection() {
  if (!state.manifest) return;
  renderResults();
  renderSelectAll();
}

const isFiltered = () =>
  Boolean(state.query.trim()) ||
  state.waveFilter !== null ||
  state.fileFilter !== null ||
  state.levelFilter !== null ||
  state.topicSel.length > 0;

/** Forget the filters and open rows: called when another cohort is opened. */
export function resetForCohort() {
  Object.assign(state, {
    query: "",
    waveFilter: null,
    fileFilter: null,
    levelFilter: null,
    topicSel: [],
    topicMode: "any",
    gridExpanded: new Set(),
    domains: state.manifest.topics?.domains || [],
    topics: flatten(state.manifest.topics),
    expanded: new Set(),
    allValues: new Set(),
    anchor: null,
    labelIndex: buildLabelIndex(state.vars),
  });
  $("#q").value = "";
}

/* Measurement level is a refinement, not a way in: a dropdown, with counts. */
function renderLevelSelect() {
  const levels = state.manifest.levels || [];
  const sel = $("#level");
  sel.hidden = !levels.length;
  const total = [...state.levelCounts.values()].reduce((a, b) => a + b, 0);
  const opt = (k) => {
    const count = state.levelCounts.get(k) || 0;
    const usable = count || state.levelFilter === k;
    return `<option value="${k}"${usable ? "" : " disabled"}>${esc(levelName(levels, k))} (${n(count)})</option>`;
  };
  sel.innerHTML = `<option value="">Any level (${n(total)})</option>${[...levels.keys(), -1].map(opt).join("")}`;
  sel.value = state.levelFilter === null ? "" : String(state.levelFilter);
}

function renderFilters() {
  const chips = [];
  if (state.waveFilter !== null) {
    chips.push(
      `<button class="chip" data-clear="wave" title="Show every ${esc(state.manifest.wave.term)}">${esc(waveKey(state.waveFilter))} ✕</button>`,
    );
  }
  if (state.fileFilter !== null) {
    chips.push(
      `<button class="chip" data-clear="file" title="Show every file">${esc(state.manifest.files[state.fileFilter].name)} ✕</button>`,
    );
  }
  for (const s of state.topicSel) {
    const label = s.kind === "d" ? state.domains[s.i].label : state.topics[s.i].label;
    chips.push(
      `<button class="chip chip-topic" data-unselect="${s.kind}:${s.i}" title="Remove this topic">${esc(label)} ✕</button>`,
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
  const count = state.matches.length;
  $("#result-count").textContent = `${n(count)} variable${count === 1 ? "" : "s"}`;
}

/* ── The list ────────────────────────────────────────────────────────── */

function rowHtml(row, i, q) {
  const file = fileOf(row);
  const key = keyOf(row);
  const open = state.expanded.has(key);
  const wave = state.manifest.wave.list[row[3]];
  const label = row[1] || "No label";
  const why = canSelect(row, file, state.manifest.identifier);
  const isId = why && file.hasId; // the identifier: in every download already
  const isIn = !why && has(state.bundle, file.name, row[0]);
  const mark = isIn || isId ? "✓" : why ? "" : "＋";
  const attrs = why
    ? `aria-disabled="true" title="${esc(why)}"`
    : `aria-pressed="${isIn}" title="Click to ${isIn ? "remove" : "select"} · Shift-click for a range" draggable="true"`;
  // Up to two topics, strongest first, and a stripe in the colour of the strongest's domain.
  const ts = state.topics.length ? rowTopics(row, state.options.minConf) : [];
  const tags = ts
    .slice(0, 2)
    .map(
      ([t]) => `<span class="topic-chip" data-domain="${esc(domainOf(t).id)}"
       title="${esc(domainOf(t).label)} › ${esc(state.topics[t].label)}">${esc(state.topics[t].label)}</span>`,
    )
    .join("");
  const stripe = ts.length ? ` data-domain="${esc(domainOf(ts[0][0]).id)}"` : "";
  return `<li class="vrow${open ? " is-open" : ""}${isIn ? " is-in" : ""}${why ? " is-fixed" : ""}" data-key="${esc(key)}"${stripe}>
    <div class="vrow-main">
      <button class="vrow-btn" data-i="${i}" ${attrs}>
        <span class="v-check" aria-hidden="true">${mark}</span>
        <span class="v-name" title="${esc(row[0])}">${highlight(row[0], q)}</span>
        <span class="v-label" title="${esc(label)}">${highlight(label, q)}</span>
        <span class="v-wave" title="${esc(wave.label || "")}">${esc(wave.key)}</span>
        <span class="v-file" title="${esc(file.description || file.name)}">${esc(file.name)}</span>
        <span class="v-topics">${tags}</span>
      </button>
      <button class="v-expand" data-expand="${i}" aria-expanded="${open}"
          ${open ? `aria-controls="more-${esc(key)}"` : ""}
          aria-label="${open ? "Hide" : "Show"} details for ${esc(row[0])}"
          title="${open ? "Hide" : "Show"} details">${open ? "▾" : "▸"}</button>
    </div>
    ${open ? `<div class="vrow-more" id="more-${esc(key)}">${moreHtml(row)}</div>` : ""}
  </li>`;
}

/** Draw the result rows that fit, the "show more" button and the empty-state message. */
export function renderResults() {
  const q = state.query.trim();
  const { rows, left, next } = page(state.matches, state.shown);
  if (!state.matches.length) {
    $("#results").innerHTML = `<li class="vempty">No variables match.
      <button class="link-btn" data-clear-all>Clear the filters</button></li>`;
  } else {
    $("#results").innerHTML =
      `<li class="vhead" aria-hidden="true"><span></span><span>Variable</span><span>Label</span>
         <span>${esc(state.manifest.wave.term)}</span><span class="v-file">File</span><span class="v-topics">${state.topics.length ? "Topics" : ""}</span><span></span></li>` +
      rows.map((row, i) => rowHtml(row, i, q)).join("");
  }
  const more = $("#more");
  more.hidden = left <= 0;
  more.innerHTML =
    left > 0
      ? `<button class="btn" id="show-more">Show ${n(next)} more</button>
         <span>${n(rows.length)} of ${n(state.matches.length)} shown</span>`
      : "";
  // Rows open before their dictionary arrived fill in now.
  for (const row of rows) if (state.expanded.has(keyOf(row))) fillMore(row);
}

/* ── A variable, opened ──────────────────────────────────────────────── */

const dictId = (row) => `${state.manifest.key}/${fileOf(row).name}`;
const failed = new Map(); // dictionaries that could not be loaded: id -> message

/* The row's dictionary entry; undefined while not loaded, null when it has none. */
function dictEntry(row) {
  const dict = state.dictCache.get(dictId(row));
  if (!dict) return failed.has(dictId(row)) ? null : undefined;
  return dict.variables.find((v) => v.variable === row[0]) || null;
}

async function fillMore(row) {
  if (dictEntry(row) !== undefined) return;
  try {
    await loadDict(fetch, state.manifest.key, fileOf(row).name, state.dictCache);
  } catch (err) {
    failed.set(dictId(row), err.message);
  }
  const el = document.getElementById(`more-${keyOf(row)}`);
  if (el && state.expanded.has(keyOf(row))) el.innerHTML = moreHtml(row);
}

const valueItem = (v) => `<li><span class="vm-code">${esc(v.code)}</span> ${esc(v.label)}</li>`;

function valuesHtml(row, d) {
  if (d.isIdentifier) {
    return `<p class="vm-note">The identifier every file is merged on: always the first column of a download.</p>`;
  }
  if (d.note) {
    return `<p class="vm-note">${d.note === "continuous" ? "A continuous measure: no value labels." : "No value labels recorded."}</p>`;
  }
  // Answers first; the missing codes after, on a quieter line of their own.
  const key = keyOf(row);
  const all = state.allValues.has(key);
  const answers = all ? [...d.answers, ...d.more] : d.answers;
  let toggle = "";
  if (d.more.length) {
    toggle = `<li><button class="link-btn" data-values="${esc(key)}">${all ? "fewer" : `+ ${d.more.length} more`}</button></li>`;
  }
  const naItem = (v) =>
    v.lossy
      ? `<li class="vm-lossy" title="Declared missing, but labelled like an answer: converting to NA loses it"><span class="vm-code">${esc(v.code)}</span> ${esc(v.label)} ⚠</li>`
      : valueItem(v);
  const kept = d.kept
    .map(([x, l]) => `<span class="vm-code">${esc(x)}</span> ${esc(l)}`)
    .join(", ");
  return `${answers.length ? `<ul class="vm-values">${answers.map(valueItem).join("")}${toggle}</ul>` : ""}
    ${d.missing.length ? `<ul class="vm-values is-na" title="Missing-value codes"><li class="vm-key">Missing</li>${d.missing.map(naItem).join("")}</ul>` : ""}
    ${kept ? `<p class="vm-note vm-kept" title="Negative, but labelled as an answer: never converted to NA">Kept as answers: ${kept}</p>` : ""}`;
}

function sameLabelHtml(row) {
  const { rows, more } = sameLabel(state.labelIndex, row);
  if (!rows.length) return "";
  const links = rows
    .map(
      (
        r,
      ) => `<button class="vm-also-link" data-jump="${esc(keyOf(r))}" title="${esc(fileOf(r).name)}">
        <span class="v-wave">${esc(waveKey(r[3]))}</span> ${esc(r[0])}</button>`,
    )
    .join("");
  return `<div class="vm-also"><span class="vm-key">Same label</span>${links}${more ? `<span class="vm-dim">+ ${more} more</span>` : ""}</div>`;
}

/* Every topic in the dictionary entry, with its confidence; those under the threshold are
   dimmed rather than hidden. Clicking one filters by it. */
function topicsHtml(entry) {
  const byId = new Map(state.topics.map((t, i) => [t.id, i]));
  const tags = (entry.topics || [])
    .filter(([id]) => byId.has(id))
    .map(([id, conf]) => {
      const i = byId.get(id);
      const pct = Math.round(conf * 100);
      const domain = domainOf(i);
      return `<button class="vm-topic${pct < state.options.minConf ? " is-below" : ""}" data-topic-open="${i}"
        data-domain="${esc(domain.id)}" title="${esc(domain.label)} › ${esc(state.topics[i].label)} · filter by this topic">${esc(state.topics[i].label)} <span class="vm-pct">${pct}%</span></button>`;
    })
    .join("");
  return tags ? `<div class="vm-topics"><span class="vm-key">Topics</span>${tags}</div>` : "";
}

function moreHtml(row) {
  const entry = dictEntry(row);
  if (entry === undefined) return `<p class="vm-note">Loading…</p>`;
  const file = fileOf(row);
  if (entry === null) {
    const why = failed.get(dictId(row)) || `${row[0]} is not in the ${file.name} dictionary.`;
    return `<p class="vm-note vm-warn">${esc(why)}</p>`;
  }
  const d = describeVariable(entry, file, state.manifest.identifier);
  const facts = d.isIdentifier
    ? esc(file.name)
    : d.facts
        .map((f) =>
          f.detail
            ? `${esc(f.value)} <span class="vm-dim">— ${esc(f.detail)}</span>`
            : esc(f.name === "Position" ? `position ${f.value}` : f.value),
        )
        .join(" · ");
  return `${valuesHtml(row, d)}
    ${topicsHtml(entry)}
    ${sameLabelHtml(row)}
    ${file.hasId ? "" : `<p class="vm-note vm-warn">This file has no ${esc(state.manifest.identifier)} column, so it cannot be merged.</p>`}
    <div class="vm-meta"><span>${facts}</span>
      <button class="link-btn" data-file-open="${row[2]}">all in this file</button></div>`;
}

/* Redrawing a row replaces its buttons; a keyboard user stays where they were. */
function toggleRow(row) {
  const key = keyOf(row);
  const had = document.activeElement?.matches?.(".v-expand");
  if (state.expanded.has(key)) state.expanded.delete(key);
  else state.expanded.add(key);
  const li = document.querySelector(`.vrow[data-key="${CSS.escape(key)}"]`);
  if (li) li.outerHTML = rowHtml(row, state.matches.indexOf(row), state.query.trim());
  if (state.expanded.has(key)) fillMore(row);
  if (had) {
    document
      .querySelector(`.vrow[data-key="${CSS.escape(key)}"] .v-expand`)
      ?.focus({ preventScroll: true });
  }
}

/* ── Selecting ───────────────────────────────────────────────────────── */

function renderSelectAll() {
  const btn = $("#select-all");
  const mode = selectAllState(state.matches, state.manifest, state.bundle);
  btn.hidden = mode === "hidden";
  if (btn.hidden) return;
  const count = selectableItems(state.matches, state.manifest).length;
  btn.dataset.mode = mode;
  btn.textContent = `${mode === "remove" ? "Remove" : "Select"} all ${n(count)}`;
}

/* Said beside the count, and to a screen reader, when one click changed several rows. */
let sayTimer;
function sayCount(change) {
  const el = $("#select-status");
  const m = Math.abs(change);
  el.textContent = change
    ? `${change > 0 ? "Added" : "Removed"} ${n(m)} variable${m === 1 ? "" : "s"}`
    : "";
  clearTimeout(sayTimer);
  sayTimer = setTimeout(() => {
    el.textContent = "";
  }, 5000);
}

function selectAll() {
  const items = selectableItems(state.matches, state.manifest);
  if ($("#select-all").dataset.mode === "remove") {
    const r = removeMany(state.bundle, items);
    setSelection(r.selection);
    sayCount(-r.changed);
  } else {
    const r = addMany(state.bundle, items, state.manifest);
    setSelection(r.selection);
    sayCount(r.changed);
  }
}

/* A click puts a row in the selection or takes it out (Cmd- or Ctrl-click the same: a
   click never clears the others). Shift-click carries every row between it and the last
   row clicked the way the clicked row goes: in, or out. */
function selectRow(btn, e) {
  const row = state.matches[Number(btn.dataset.i)];
  if (!row) return;
  const key = keyOf(row);
  const had = document.activeElement === btn;
  const anchor = state.anchor;
  state.anchor = key;
  if (btn.getAttribute("aria-disabled") === "true") return;
  const item = toItem(row, state.manifest);
  if (e.shiftKey && anchor && anchor !== key) {
    window.getSelection()?.removeAllRanges(); // Shift-click also extends the text selection
    const range = rangeBetween(state.matches, anchor, key, state.manifest);
    if (range.length) {
      const adding = !has(state.bundle, item.file, item.name);
      const r = adding
        ? addMany(state.bundle, range, state.manifest)
        : removeMany(state.bundle, range);
      setSelection(r.selection);
      sayCount(adding ? r.changed : -r.changed);
    }
  } else {
    setSelection(toggle(state.bundle, item, state.manifest).selection);
  }
  if (had) {
    document
      .querySelector(`.vrow[data-key="${CSS.escape(key)}"] .vrow-btn`)
      ?.focus({ preventScroll: true });
  }
}

/* Drag a row onto the Selection tab to add it. */
function wireDrag() {
  $("#results").addEventListener("dragstart", (e) => {
    const btn = e.target.closest?.(".vrow-btn");
    const row = btn && state.matches[Number(btn.dataset.i)];
    if (!row) return;
    e.dataTransfer.setData(DRAG_MIME, JSON.stringify(toItem(row, state.manifest)));
    e.dataTransfer.effectAllowed = "copy";
  });
  const tab = $('.view-tab[data-view="basket"]');
  tab.addEventListener("dragover", (e) => {
    if (e.dataTransfer.types.includes(DRAG_MIME)) e.preventDefault();
  });
  tab.addEventListener("drop", (e) => {
    e.preventDefault();
    try {
      const item = JSON.parse(e.dataTransfer.getData(DRAG_MIME));
      setSelection(addMany(state.bundle, [item], state.manifest).selection);
    } catch {
      // not one of our rows
    }
  });
}

/* Go to another variable: search for its label, which brings the whole same-label family
   into the list together, and open it. */
async function jumpTo(key) {
  const row = state.vars.find((r) => keyOf(r) === key);
  if (!row) return;
  // Its details first, so the row is scrolled to at its full height.
  await fillMore(row);
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

/**
 * Show every variable in one file.
 * @param {number} fileIdx Index into the manifest's files.
 */
export function filterToFile(fileIdx) {
  switchView("search");
  Object.assign(state, { query: "", waveFilter: null, fileFilter: fileIdx, levelFilter: null });
  $("#q").value = "";
  runSearch();
  $("#filterbar").scrollIntoView({ block: "start" });
}

/* Change the topic filter with `change` (toggle or ensure from core/topics.js) and search
   again. A domain with one of its topics chosen opens, so the choice is never hidden. */
function selectTopic(change, kind, i) {
  state.topicSel = change(state.topicSel, kind, i, state.topics);
  if (kind === "t" && state.topicSel.some((s) => s.kind === "t" && s.i === i)) {
    state.gridExpanded.add(state.topics[i].domain);
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
    if (expand) return toggleRow(state.matches[Number(expand.dataset.expand)]);
    const vals = e.target.closest("[data-values]");
    if (vals) {
      const key = vals.dataset.values;
      if (state.allValues.has(key)) state.allValues.delete(key);
      else state.allValues.add(key);
      const row = state.matches.find((r) => keyOf(r) === key);
      const el = document.getElementById(`more-${key}`);
      if (row && el) el.innerHTML = moreHtml(row);
      return;
    }
    const tag = e.target.closest("[data-topic-open]");
    if (tag) return selectTopic(ensure, "t", Number(tag.dataset.topicOpen));
    const jump = e.target.closest("[data-jump]");
    if (jump) return jumpTo(jump.dataset.jump);
    const file = e.target.closest("[data-file-open]");
    if (file) return filterToFile(Number(file.dataset.fileOpen));
    if (e.target.closest("[data-clear-all]")) return clearAll();
    const btn = e.target.closest(".vrow-btn");
    if (btn) selectRow(btn, e);
  });
  $("#select-all").addEventListener("click", selectAll);
  wireDrag();

  $("#more").addEventListener("click", (e) => {
    if (!e.target.closest("#show-more")) return;
    state.shown += PAGE;
    renderResults();
  });

  wireOverview({
    onWave: (wave) => {
      state.waveFilter = state.waveFilter === wave ? null : wave;
      runSearch();
    },
    onTopic: (kind, i) => selectTopic(toggleTopic, kind, i),
    // A cell: that topic at that sweep. The same cell again lets go of the sweep only.
    onCell: (kind, i, wave) => {
      const already =
        state.waveFilter === wave && state.topicSel.some((s) => s.kind === kind && s.i === i);
      state.waveFilter = already ? null : wave;
      selectTopic(ensure, kind, i);
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
      const [kind, i] = un.dataset.unselect.split(":");
      return selectTopic(toggleTopic, kind, Number(i));
    }
    const mode = e.target.closest("[data-mode]");
    if (mode) {
      state.topicMode = mode.dataset.mode;
      runSearch();
    }
  });

  $("#level").addEventListener("change", (e) => {
    state.levelFilter = e.target.value === "" ? null : Number(e.target.value);
    runSearch();
  });
  $("#clear-filters").addEventListener("click", clearAll);
}
