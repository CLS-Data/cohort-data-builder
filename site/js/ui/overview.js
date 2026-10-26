/* The top of the Variables view: what the cohort is, and every matching variable by sweep.

   Sweeps with no matches are drawn as gaps rather than left out: absence is usually the
   thing you need to know. */

import { esc } from "../core/text.js";
import { state } from "./state.js";

const $ = (sel) => document.querySelector(sel);

/** Write the line saying what the cohort is and how big it is. */
export function renderAbout() {
  const m = state.manifest;
  $("#ov-about").innerHTML =
    `<strong>${esc(m.fullName)}</strong>${m.description ? ` — ${esc(m.description)}` : ""} ` +
    `<span class="vm-dim">${m.counts.variables.toLocaleString("en-GB")} variables in ${m.counts.files} files.</span>`;
}

/**
 * Draw one bar per sweep, in manifest (time) order.
 * @param {number[]} perWave Matching variables per sweep.
 * @param {boolean} filtered Whether any filter or query is active.
 */
export function renderSpine(perWave, filtered) {
  const waves = state.manifest.wave.list;
  const max = Math.max(1, ...perWave);
  const total = perWave.reduce((a, b) => a + b, 0);
  $("#spine-title").textContent = filtered ? "Matching variables" : "All variables";
  $("#spine-note").textContent = total.toLocaleString("en-GB");
  $("#spine-track").innerHTML = waves
    .map((wave, i) => {
      const n = perWave[i];
      const pct = n ? Math.max(6, Math.round((n / max) * 100)) : 0;
      const what = `${n.toLocaleString("en-GB")} ${n === 1 ? "variable" : "variables"}`;
      return `<li><button class="node${n ? "" : " is-empty"}" data-wave="${i}"
          aria-pressed="${state.waveFilter === i}"
          title="${esc(wave.key)}${wave.label ? ` · ${esc(wave.label)}` : ""} — ${what}. Click to show only this ${esc(state.manifest.wave.term)}.">
        <span class="node-bar"><span class="node-fill" style="height:${pct}%"></span></span>
        <span class="node-age">${esc(wave.key)}</span>
        <span class="node-n">${n ? n.toLocaleString("en-GB") : "—"}</span>
      </button></li>`;
    })
    .join("");
}

/**
 * Make a click on a sweep bar call back with that sweep's index.
 * @param {(wave: number) => void} onWave Called with the clicked sweep.
 */
export function wireOverview(onWave) {
  $("#spine-track").addEventListener("click", (e) => {
    const btn = e.target.closest("[data-wave]");
    if (btn) onWave(Number(btn.dataset.wave));
  });
}
