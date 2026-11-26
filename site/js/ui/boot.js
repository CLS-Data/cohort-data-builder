/* Starting the page: loading the catalogue, choosing and loading cohorts, the theme.

   The chosen cohorts are named in the URL hash (#ncds+bcs70), so a link can point at them
   (contracts/cohort-choice.md); a single key (#bcs70) is the address of earlier versions. */

import {
  chooseInitial,
  colourSlot,
  formatChoice,
  parseChoice,
  toggleChoice,
} from "../core/cohorts.js";
import { loadCatalogue, loadCohort } from "../core/data.js";
import { buildLabelIndex } from "../core/search.js";
import { read, storeKey, write } from "../core/storage.js";
import { esc } from "../core/text.js";
import { renderAbout } from "./overview.js";
import { renderPanel, wirePanel } from "./panel.js";
import { mergeChosen, refreshSelection, resetFilters, runSearch, wireResults } from "./results.js";
import { wireReview } from "./review.js";
import {
  onSelectionChange,
  restoreOptions,
  restoreSelection,
  savedSelection,
  storage,
} from "./selected.js";
import { RETRY_EVENT, state } from "./state.js";
import { wireSuggest } from "./suggest.js";
import { switchView } from "./views.js";

const $ = (sel) => document.querySelector(sel);

/** Replace the page with a readable failure message. */
function fail(message, detail) {
  document.querySelector("main").innerHTML =
    `<div class="load-failure" role="alert"><p><strong>${esc(message)}</strong></p>` +
    `<p>${esc(detail)}</p><p>Try reloading the page.</p></div>`;
}

const keys = () => state.catalogue.map((d) => d.key);
const entry = (key) => state.catalogue.find((d) => d.key === key);
const n = (x) => x.toLocaleString("en-GB");

/* The header's toggle buttons, one per catalogue cohort; drawn once, updated after. */
function drawPicker() {
  const all = keys();
  $("#cohorts").innerHTML = state.catalogue
    .map(
      (d) => `<button type="button" data-cohort="${esc(d.key)}" data-coh="${colourSlot(d.key, all)}"
        aria-pressed="false" title="${esc(d.fullName || d.name)}"><span class="coh-mark" aria-hidden="true"></span>${esc(d.name)}</button>`,
    )
    .join("");
}

function updatePicker() {
  const only = state.chosen.length === 1;
  for (const b of document.querySelectorAll("#cohorts button")) {
    const key = b.dataset.cohort;
    const on = state.chosen.includes(key);
    b.setAttribute("aria-pressed", String(on));
    const last = on && only;
    if (last) b.setAttribute("aria-disabled", "true");
    else b.removeAttribute("aria-disabled");
    b.title = last ? "At least one cohort stays chosen" : entry(key).fullName || entry(key).name;
    if (state.cohorts.get(key)?.status === "loading") b.setAttribute("aria-busy", "true");
    else b.removeAttribute("aria-busy");
  }
}

/* Title, subtitle and footer name the chosen cohorts (contracts/cohort-choice.md). */
function showNames() {
  const chosen = state.chosen.map(entry);
  if (chosen.length === 1) {
    const c = state.cohorts.get(chosen[0].key);
    const m = c?.status === "ready" ? c.manifest : null;
    document.title = `${chosen[0].name} · Cohort Data Builder`;
    $("#mark-sub").textContent = chosen[0].fullName || chosen[0].name;
    $("#foot-counts").textContent = m
      ? `${n(m.counts.variables)} variables · ${m.counts.files} files · ` +
        `${m.wave.list.length} ${m.wave.plural} · built ${m.built}`
      : "—";
    return;
  }
  const names = chosen.map((d) => d.name).join(" + ");
  document.title = `${names} · Cohort Data Builder`;
  $("#mark-sub").textContent = names;
  const sum = (f) => chosen.reduce((a, d) => a + (d[f] || 0), 0);
  $("#foot-counts").textContent =
    `${n(sum("variables"))} variables · ${n(sum("files"))} files · ${chosen.length} cohorts`;
}

/* Everything that shows the chosen cohorts, drawn again. */
function refresh() {
  mergeChosen();
  updatePicker();
  showNames();
  renderAbout();
  runSearch();
  renderPanel();
}

/* Load a cohort into state.cohorts, once; a failed one is tried again. */
async function load(key) {
  const have = state.cohorts.get(key);
  if (have?.status === "ready" || have?.status === "loading") return;
  state.cohorts.set(key, { status: "loading" });
  updatePicker();
  try {
    const { manifest, vars } = await loadCohort(fetch, key);
    state.cohorts.set(key, { status: "ready", manifest, vars, labelIndex: buildLabelIndex(vars) });
    restoreSelection(key);
  } catch (err) {
    state.cohorts.set(key, { status: "failed", error: err.message });
  }
  if (state.chosen.includes(key)) refresh();
}

/**
 * Choose these cohorts: remember the choice, drop filters on cohorts no longer chosen,
 * and load the ones not loaded yet.
 * @param {string[]} next The keys, in catalogue order; not empty.
 */
async function choose(next) {
  if (!next.length || formatChoice(next, keys()) === formatChoice(state.chosen, keys())) return;
  state.chosen = next;
  for (const f of ["waveFilter", "fileFilter"]) {
    if (state[f] && !next.includes(state[f].cohort)) state[f] = null;
  }
  const hash = formatChoice(next, keys());
  if (decodeURIComponent(location.hash.slice(1)) !== hash)
    history.replaceState(null, "", `#${hash}`);
  write(storage, storeKey("cohorts"), next);
  refresh();
  await Promise.all(next.map(load));
}

/** Restore the stored theme and make the theme button switch it. */
function wireTheme() {
  const root = document.documentElement;
  const stored = read(storage, storeKey("theme"), null);
  if (stored) root.dataset.theme = stored;
  $("#theme").addEventListener("click", () => {
    const now =
      root.dataset.theme || (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
    root.dataset.theme = now === "dark" ? "light" : "dark";
    write(storage, storeKey("theme"), root.dataset.theme);
  });
}

const TEXT_SIZES = ["", "large", "larger"];

/* Show the text size and mark its button. "" is the browser's own size. */
function setTextSize(size) {
  const root = document.documentElement;
  if (size) root.dataset.text = size;
  else delete root.dataset.text;
  for (const b of document.querySelectorAll("[data-text-size]")) {
    b.setAttribute("aria-pressed", String(b.dataset.textSize === size));
  }
}

/** Restore the stored text size and make the Text size buttons set it. */
function wireTextSize() {
  const stored = read(storage, storeKey("text-size"), "");
  setTextSize(TEXT_SIZES.includes(stored) ? stored : "");
  for (const b of document.querySelectorAll("[data-text-size]")) {
    b.addEventListener("click", () => {
      setTextSize(b.dataset.textSize);
      write(storage, storeKey("text-size"), b.dataset.textSize);
    });
  }
}

async function boot() {
  wireTheme();
  wireTextSize();
  try {
    state.catalogue = await loadCatalogue(fetch);
  } catch (err) {
    fail("Could not load the site data.", err.message);
    return;
  }
  if (!state.catalogue.length) {
    fail("Could not load the site data.", "No cohorts are listed in data/datasets.json.");
    return;
  }
  drawPicker();
  $("#cohorts").addEventListener("click", (e) => {
    const b = e.target.closest("button[data-cohort]");
    if (b) choose(toggleChoice(state.chosen, b.dataset.cohort, keys()));
  });
  // A Retry button in the list (results.js) for a cohort that failed to load.
  document.addEventListener(RETRY_EVENT, (e) => load(e.detail));
  for (const tab of document.querySelectorAll(".view-tab")) {
    tab.addEventListener("click", () => switchView(tab.dataset.view));
  }
  restoreOptions();
  wireResults();
  wirePanel();
  wireReview();
  wireSuggest();
  onSelectionChange(() => {
    renderPanel();
    refreshSelection();
  });
  window.addEventListener("hashchange", () => choose(parseChoice(location.hash, keys())));
  resetFilters();
  // Cohorts not chosen but with a saved selection load in the background, so the selection
  // shows them all (research R6).
  for (const key of keys()) {
    const saved = savedSelection(key);
    if (Array.isArray(saved) && saved.length) load(key);
  }
  await choose(
    chooseInitial({
      hash: location.hash,
      stored: read(storage, storeKey("cohorts"), null),
      storedOld: read(storage, storeKey("cohort"), null),
      keys: keys(),
    }),
  );
}

boot();
