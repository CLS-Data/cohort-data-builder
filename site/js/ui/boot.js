/* Starting the page: loading the catalogue, choosing and opening a cohort, the theme.

   The cohort in view is named in the URL hash (#bcs70), so a link can point at one. */

import { loadCatalogue, loadCohort } from "../core/data.js";
import { read, storeKey, write } from "../core/storage.js";
import { esc } from "../core/text.js";
import { renderAbout } from "./overview.js";
import { renderPanel, wirePanel } from "./panel.js";
import { refreshSelection, resetForCohort, runSearch, wireResults } from "./results.js";
import { onSelectionChange, restoreOptions, restoreSelection, storage } from "./selected.js";
import { state } from "./state.js";
import { switchView } from "./views.js";

const $ = (sel) => document.querySelector(sel);

/** Replace the page with a readable failure message. */
function fail(message, detail) {
  document.querySelector("main").innerHTML =
    `<div class="load-failure" role="alert"><p><strong>${esc(message)}</strong></p>` +
    `<p>${esc(detail)}</p><p>Try reloading the page.</p></div>`;
}

/** The cohort to open: the one in the hash, else the last one used, else the first. */
function chooseCohort() {
  const keys = state.catalogue.map((d) => d.key);
  const fromHash = decodeURIComponent(location.hash.slice(1));
  if (keys.includes(fromHash)) return fromHash;
  const last = read(storage, storeKey("cohort"), null);
  return keys.includes(last) ? last : keys[0];
}

/** Load a cohort and show its name and counts. */
async function openCohort(key) {
  if (state.manifest?.key === key) return;
  const picker = $("#dataset");
  picker.value = key;
  picker.disabled = true;
  try {
    Object.assign(state, await loadCohort(fetch, key));
  } catch (err) {
    fail(`Could not load the ${key} data.`, err.message);
    return;
  } finally {
    picker.disabled = false;
  }
  if (location.hash.slice(1) !== key) history.replaceState(null, "", `#${key}`);
  write(storage, storeKey("cohort"), key);

  const m = state.manifest;
  document.title = `${m.name} · Cohort Data Builder`;
  $("#mark-sub").textContent = m.fullName;
  $("#foot-counts").textContent =
    `${m.counts.variables.toLocaleString("en-GB")} variables · ${m.counts.files} files · ` +
    `${m.wave.list.length} ${m.wave.plural} · built ${m.built}`;

  resetForCohort();
  renderAbout();
  runSearch();
  restoreSelection();
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

async function boot() {
  wireTheme();
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
  $("#dataset").innerHTML = state.catalogue
    .map((d) => `<option value="${esc(d.key)}">${esc(d.name)}</option>`)
    .join("");
  $("#dataset").addEventListener("change", (e) => openCohort(e.target.value));
  for (const tab of document.querySelectorAll(".view-tab")) {
    tab.addEventListener("click", () => switchView(tab.dataset.view));
  }
  restoreOptions();
  wireResults();
  wirePanel();
  onSelectionChange(() => {
    renderPanel();
    refreshSelection();
  });
  window.addEventListener("hashchange", () => {
    const key = decodeURIComponent(location.hash.slice(1));
    if (state.catalogue.some((d) => d.key === key)) openCohort(key);
  });
  await openCohort(chooseCohort());
}

boot();
