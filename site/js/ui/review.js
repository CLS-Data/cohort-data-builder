/* The Selection view: what was picked, as one list of output columns (where a variable is
   renamed or removed), the data files needed, the download options, and the download.

   One list, not two: user testing found a second list of the same variables confusing.
   The columns list is also where a name clash between two files becomes visible (two files
   both calling something `sex` is normal). */

import { buildProject, FORMATS } from "../core/codegen.js";
import { fixDots, problems } from "../core/columns.js";
import { loadDict } from "../core/data.js";
import { addMany, keyOf, remove } from "../core/selection.js";
import { esc } from "../core/text.js";
import { zip } from "../core/zip.js";
import { filterToFile } from "./results.js";
import { onSelectionChange, saveOptions, setSelection } from "./selected.js";
import { DRAG_MIME, state } from "./state.js";
import { onShow } from "./views.js";

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => [...document.querySelectorAll(sel)];
const n = (x) => x.toLocaleString("en-GB");
const plural = (k, word) => `${n(k)} ${word}${k === 1 ? "" : "s"}`;

const TEMPLATE_FILES = [
  "README.md",
  "data-README.md",
  "project.Rproj",
  "r/load_data.R",
  "r/merge.R",
  "python/load_data.py",
  "python/merge.py",
  "python/requirements.txt",
];
let templates = null; // fetched on the first download: most visitors never download

const waveOrder = () => state.manifest.wave.list.map((w) => w.key);
const currentProblems = () =>
  problems(state.bundle, state.manifest.identifier, state.options.outputFormat);

/* ── Drawing ─────────────────────────────────────────────────────────── */

/* Drawn only while the view is showing: with thousands selected these panes are the
   slowest thing on the page, and every click in the list would otherwise redraw them. */
function render() {
  if (state.view !== "basket" || !state.manifest) return;
  renderDetail();
}

function colRow(b, bad) {
  const problem = bad.get(keyOf(b));
  return `<li class="col-row${problem ? " is-bad" : ""}">
    <button class="add is-in basket-x" data-remove="${esc(keyOf(b))}"
        aria-label="Remove ${esc(b.name)}" title="Remove"><span class="add-yes">✓</span><span class="add-no">✕</span></button>
    <span class="col-kind col-kind-raw" title="${esc(b.wave)}">${esc(b.wave)}</span>
    <span class="col-body">
      <input class="col-input" type="text" value="${esc(b.column)}" data-rename="${esc(keyOf(b))}"
          spellcheck="false" autocomplete="off" aria-label="Output column name for ${esc(b.name)}"
          aria-invalid="${problem ? "true" : "false"}">
      <span class="col-note">${esc(b.label || "no label")} ·
        ${b.column === b.name ? "" : `<code>${esc(b.name)}</code> in `}<code>${esc(b.file)}</code></span>
      ${problem ? `<span class="col-problem">${esc(problem)}</span>` : ""}
    </span>
  </li>`;
}

function emptyHtml(m) {
  return `<div class="empty">
    <h2>Build a merge script</h2>
    <p>Pick variables in <strong>Variables</strong>, then download a small R or Python project
      that reads them from your own copy of the ${esc(m.name)} data and merges them into one
      file, one row per person.</p>
    <p>No study data is in the download or on this site: only the data dictionaries, which
      describe what each variable is.</p>
  </div>`;
}

function optionsHtml(languages, format, missingToNa) {
  const help =
    format === "csv"
      ? "Plain text that opens anywhere. Labels go in <code>codebook.csv</code> alongside it."
      : `Carries each column's label and value labels from the data dictionary. Needs
         <code>haven</code> in R${format === "sav" ? " and <code>pyreadstat</code> in Python" : ""}.`;
  const radio = (value, label) =>
    `<label><input type="radio" name="opt-format" value="${value}" ${format === value ? "checked" : ""}> ${label}</label>`;
  return `<div class="options">
    <div class="option-row">
      <span class="option-name">Language</span>
      <label><input type="checkbox" data-lang="r" ${languages.includes("r") ? "checked" : ""}> R</label>
      <label><input type="checkbox" data-lang="python" ${languages.includes("python") ? "checked" : ""}> Python</label>
    </div>
    <div class="option-row">
      <span class="option-name">Output file</span>
      ${radio("csv", "CSV")} ${radio("dta", "Stata (.dta)")} ${radio("sav", "SPSS (.sav)")}
      <p class="option-help">${help}</p>
    </div>
    <div class="option-row">
      <span class="option-name">Missing codes</span>
      <label><input type="checkbox" id="opt-na" ${missingToNa ? "checked" : ""}> Convert to NA</label>
      <p class="option-help">Replaces each variable's missing-value codes from the data
        dictionary with NA. Negative codes that are real answers are kept. Off keeps every code
        as deposited. Either way it is one setting at the top of the script, and
        <code>codebook.csv</code> lists the codes.</p>
    </div>
  </div>`;
}

function renderDetail() {
  const el = $("#basket-detail");
  const m = state.manifest;
  const count = state.bundle.length;
  if (!count) {
    el.innerHTML = emptyHtml(m);
    return;
  }
  const bad = currentProblems();
  const fileInfo = new Map(m.files.map((f) => [f.name, f]));
  const order = waveOrder();
  const files = [...new Set(state.bundle.map((b) => b.file))].sort(
    (a, b) =>
      order.indexOf(fileInfo.get(a).wave) - order.indexOf(fileInfo.get(b).wave) ||
      a.localeCompare(b),
  );
  const { languages, missingToNa, outputFormat: format } = state.options;
  const ext = FORMATS[format]?.ext || "csv";
  const dotted = format === "dta" && state.bundle.some((b) => /[^A-Za-z0-9_]/.test(b.column));

  el.innerHTML = `
    <div class="detail-head">
      <div class="detail-eyebrow">${esc(m.name)} · ${plural(count, "variable")} from ${plural(files.length, "file")}
        · <button class="link-btn" id="basket-clear">Clear</button></div>
      <h1 class="detail-name">output/merged.${ext}</h1>
      <p class="detail-label">One row per person, joined on <code>${esc(m.identifier)}</code>.
        A file with several rows per person is written to its own file instead.</p>
    </div>
    ${
      bad.size
        ? `<div class="warn"><span>⚠</span><div><strong>${plural(bad.size, "column name")} ${bad.size === 1 ? "needs" : "need"} changing</strong>
        before downloading; each says why below.${dotted ? ` <button class="link-btn" id="fix-dots">Replace every . with _</button>` : ""}</div></div>`
        : ""
    }
    <h2 class="section-title">Columns</h2>
    <p class="note">In the order they are written. Rename any of them here.</p>
    <ol class="cols" id="basket-cols">
      <li class="col-row is-fixed">
        <span class="basket-x" aria-hidden="true"></span>
        <span class="col-kind col-kind-id" title="The identifier">·</span>
        <span class="col-body"><span class="col-name">${esc(m.identifier)}</span>
          <span class="col-note">always included: the key the files are merged on</span></span>
      </li>
      ${files
        .flatMap((f) => state.bundle.filter((b) => b.file === f))
        .map((b) => colRow(b, bad))
        .join("")}
    </ol>
    <h2 class="section-title">Data files it needs</h2>
    <ul class="linklist">${files
      .map(
        (f) => `<li><button data-file="${esc(f)}" title="Show every variable in ${esc(f)}">
        <span class="ll-name">${esc(f)}</span>
        <span class="ll-desc">${esc(fileInfo.get(f).description || "")}</span>
        <span class="ll-meta">${esc(fileInfo.get(f).wave)}</span></button></li>`,
      )
      .join("")}</ul>
    <p class="note">Put them all in the project's <code>data/</code> folder, in any format (<code>.tab</code>, <code>.csv</code>, <code>.dta</code>, <code>.sav</code>): the scripts pick the read call from the extension.${m.ukdsUrl ? ` Download them from the <a href="${esc(m.ukdsUrl)}" target="_blank" rel="noopener">UK Data Service</a>.` : ""}</p>
    <h2 class="section-title">Download</h2>
    ${optionsHtml(languages, format, missingToNa)}
    <div class="detail-actions"><button class="btn btn-primary" id="basket-download">Download</button></div>
    <p class="draft-status" id="basket-status" role="status"></p>`;

  const button = $("#basket-download");
  button.disabled = bad.size > 0 || !languages.length;
  button.textContent = `Download ${languages.map((l) => (l === "r" ? "R" : "Python")).join(" + ") || "…"} code`;
}

/* ── Changing things ─────────────────────────────────────────────────── */

/* Committed on blur or Enter, not per keystroke: a redraw replaces the input being typed in. */
function rename(input) {
  const key = input.dataset.rename;
  const item = state.bundle.find((b) => keyOf(b) === key);
  // As typed: an invalid name is flagged with its reason rather than silently changed.
  const next = input.value.trim();
  if (!item || next === item.column) {
    if (item && input.value !== item.column) render();
    return;
  }
  setSelection(state.bundle.map((b) => (keyOf(b) === key ? { ...b, column: next } : b)));
}

function setOption(change) {
  Object.assign(state.options, change);
  saveOptions();
  renderDetail();
}

let sayTimer;
function say(msg) {
  const el = $("#basket-status");
  if (!el) return;
  el.textContent = msg;
  clearTimeout(sayTimer);
  sayTimer = setTimeout(() => {
    el.textContent = "";
  }, 15000);
}

/* Today in the visitor's own time zone, YYYY-MM-DD. */
function today() {
  const d = new Date();
  const pad = (x) => String(x).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

async function loadTemplates() {
  const texts = await Promise.all(
    TEMPLATE_FILES.map(async (t) => {
      const res = await fetch(`templates/${t}`);
      if (!res.ok) throw new Error(`Could not load templates/${t} (HTTP ${res.status})`);
      return [t, await res.text()];
    }),
  );
  return Object.fromEntries(texts);
}

async function download() {
  const { languages } = state.options;
  if (!state.bundle.length || currentProblems().size || !languages.length) return;
  const button = $("#basket-download");
  button.disabled = true;
  say("Packaging…");
  try {
    templates ??= await loadTemplates();
    const dicts = {};
    for (const file of new Set(state.bundle.map((b) => b.file))) {
      dicts[file] = await loadDict(fetch, state.manifest.key, file, state.dictCache);
    }
    const { name, files } = buildProject(
      state.bundle,
      state.manifest,
      dicts,
      templates,
      state.options,
      today(),
    );
    const blob = new Blob([zip(files)], { type: "application/zip" });
    const url = URL.createObjectURL(blob);
    const link = Object.assign(document.createElement("a"), { href: url, download: `${name}.zip` });
    document.body.append(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 30000);
    say(
      `${name}.zip: ${Math.max(1, Math.round(blob.size / 1024))} KB. Its README says what to do next.`,
    );
  } catch (err) {
    say(`Could not build the download: ${err.message}`);
  } finally {
    button.disabled = currentProblems().size > 0 || !state.options.languages.length;
  }
}

/** Attach the Selection view's event handlers. Call once. */
export function wireReview() {
  onShow("basket", render);
  onSelectionChange(render);

  const detail = $("#basket-detail");
  detail.addEventListener("click", (e) => {
    const gone = e.target.closest("[data-remove]");
    if (gone) return setSelection(remove(state.bundle, gone.dataset.remove).selection);
    if (e.target.closest("#basket-clear")) return setSelection([]);
    if (e.target.closest("#basket-download")) return download();
    if (e.target.closest("#fix-dots")) {
      return setSelection(fixDots(state.bundle, state.manifest.identifier));
    }
    const file = e.target.closest("[data-file]");
    if (file) filterToFile(state.manifest.files.findIndex((f) => f.name === file.dataset.file));
  });
  detail.addEventListener("change", (e) => {
    const t = e.target;
    if (t.matches("[data-lang]")) {
      const on = $$("#basket-detail [data-lang]")
        .filter((b) => b.checked)
        .map((b) => b.dataset.lang);
      setOption({ languages: on });
    } else if (t.matches("[name=opt-format]")) {
      setOption({ outputFormat: t.value });
    } else if (t.id === "opt-na") {
      state.options.missingToNa = t.checked;
      saveOptions();
    }
  });
  detail.addEventListener(
    "blur",
    (e) => {
      if (e.target.matches?.("[data-rename]")) rename(e.target);
    },
    true,
  );
  detail.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && e.target.matches?.("[data-rename]")) {
      e.preventDefault();
      rename(e.target);
    }
  });

  // The whole view takes a variable dragged from the Variables view.
  const drop = $('section.view[data-view="basket"]');
  drop.addEventListener("dragover", (e) => {
    if (e.dataTransfer.types.includes(DRAG_MIME)) e.preventDefault();
  });
  drop.addEventListener("drop", (e) => {
    e.preventDefault();
    try {
      const item = JSON.parse(e.dataTransfer.getData(DRAG_MIME));
      setSelection(addMany(state.bundle, [item], state.manifest).selection);
    } catch {
      // not one of our rows
    }
  });
}
