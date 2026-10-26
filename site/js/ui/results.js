/* The variable list: the search box, filters, result rows, and a variable opened in place.

   Each row carries what decides whether a variable is worth a look (name, label, sweep,
   file). Everything secondary opens under the row from its own ▸ button, a few lines rather
   than a pane, so many variables stay on screen at once. */

import { loadDict } from "../core/data.js";
import { describeVariable } from "../core/details.js";
import { buildLabelIndex, filterVariables, PAGE, page, sameLabel } from "../core/search.js";
import { esc, highlight, levelName } from "../core/text.js";
import { renderSpine, wireOverview } from "./overview.js";
import { state } from "./state.js";
import { switchView } from "./views.js";

const $ = (sel) => document.querySelector(sel);
const n = (x) => x.toLocaleString("en-GB");
const keyOf = (row) => `${row[2]}:${row[0]}`;
const waveKey = (i) => state.manifest.wave.list[i].key;
const fileOf = (row) => state.manifest.files[row[2]];

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
  });
  state.matches = r.matches;
  state.levelCounts = r.perLevel;
  if (!keepPlace) {
    state.shown = PAGE;
    $("#vscroll").scrollTop = 0;
  }
  renderResults();
  renderSpine(r.perWave, isFiltered());
  renderLevelSelect();
  renderFilters();
}

const isFiltered = () =>
  Boolean(state.query.trim()) ||
  state.waveFilter !== null ||
  state.fileFilter !== null ||
  state.levelFilter !== null;

/** Forget the filters and open rows: called when another cohort is opened. */
export function resetForCohort() {
  Object.assign(state, {
    query: "",
    waveFilter: null,
    fileFilter: null,
    levelFilter: null,
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
  return `<li class="vrow${open ? " is-open" : ""}" data-key="${esc(key)}">
    <div class="vrow-main">
      <div class="vrow-btn" data-i="${i}">
        <span class="v-check" aria-hidden="true"></span>
        <span class="v-name" title="${esc(row[0])}">${highlight(row[0], q)}</span>
        <span class="v-label" title="${esc(label)}">${highlight(label, q)}</span>
        <span class="v-wave" title="${esc(wave.label || "")}">${esc(wave.key)}</span>
        <span class="v-file" title="${esc(file.description || file.name)}">${esc(file.name)}</span>
        <span class="v-topics"></span>
      </div>
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
         <span>${esc(state.manifest.wave.term)}</span><span class="v-file">File</span><span class="v-topics"></span><span></span></li>` +
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

/* Go to another variable: search for its label, which brings the whole same-label family
   into the list together, and open it. */
async function jumpTo(key) {
  const row = state.vars.find((r) => keyOf(r) === key);
  if (!row) return;
  // Its details first, so the row is scrolled to at its full height.
  await fillMore(row);
  Object.assign(state, { query: row[1], waveFilter: null, fileFilter: null, levelFilter: null });
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

function clearAll() {
  Object.assign(state, { query: "", waveFilter: null, fileFilter: null, levelFilter: null });
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
    const jump = e.target.closest("[data-jump]");
    if (jump) return jumpTo(jump.dataset.jump);
    const file = e.target.closest("[data-file-open]");
    if (file) return filterToFile(Number(file.dataset.fileOpen));
    if (e.target.closest("[data-clear-all]")) clearAll();
  });

  $("#more").addEventListener("click", (e) => {
    if (!e.target.closest("#show-more")) return;
    state.shown += PAGE;
    renderResults();
  });

  wireOverview((wave) => {
    state.waveFilter = state.waveFilter === wave ? null : wave;
    runSearch();
  });

  $("#active-filters").addEventListener("click", (e) => {
    const chip = e.target.closest("[data-clear]");
    if (!chip) return;
    state[`${chip.dataset.clear}Filter`] = null;
    runSearch();
  });

  $("#level").addEventListener("change", (e) => {
    state.levelFilter = e.target.value === "" ? null : Number(e.target.value);
    runSearch();
  });
  $("#clear-filters").addEventListener("click", clearAll);
}
