/* The top of the Variables view: what the cohort is, every matching variable by sweep, and
   the topic rows beneath, which are the topic filter.

   Sweeps with no matches are drawn as gaps rather than left out: absence is usually the
   thing you need to know.

   The topic rows are a tree: domains, each opening onto its topics. A name toggles that
   domain or topic in the filter; the cells beside it are the same thing by sweep, and a
   cell narrows to that topic at that sweep. */

import { esc } from "../core/text.js";
import { schemeIndex, shade } from "../core/topics.js";
import { manifestOf, state } from "./state.js";

const $ = (sel) => document.querySelector(sel);

/** Write the line saying what the cohort is and how big it is. */
export function renderAbout() {
  const m = manifestOf(state.chosen[0]);
  $("#ov-about").innerHTML =
    `<strong>${esc(m.fullName)}</strong>${m.description ? ` — ${esc(m.description)}` : ""} ` +
    `<span class="vm-dim">${m.counts.variables.toLocaleString("en-GB")} variables in ${m.counts.files} files.</span>`;
}

/**
 * Draw one bar per sweep, in manifest (time) order, from the last search.
 * @param {boolean} filtered Whether any filter or query is active.
 */
export function renderSpine(filtered) {
  const r = state.results[0];
  if (!r) return;
  const m = manifestOf(r.cohort);
  const { perWave } = r;
  const waves = m.wave.list;
  const max = Math.max(1, ...perWave);
  const total = perWave.reduce((a, b) => a + b, 0);
  $("#spine-title").textContent = filtered ? "Matching variables" : "All variables";
  $("#spine-note").textContent = total.toLocaleString("en-GB");
  $("#spine-track").innerHTML = waves
    .map((wave, i) => {
      const n = perWave[i];
      const pct = n ? Math.max(6, Math.round((n / max) * 100)) : 0;
      const what = `${n.toLocaleString("en-GB")} ${n === 1 ? "variable" : "variables"}`;
      const on = state.waveFilter?.cohort === r.cohort && state.waveFilter.i === i;
      return `<li><button class="node${n ? "" : " is-empty"}" data-cohort="${esc(r.cohort)}" data-wave="${i}"
          aria-pressed="${on}"
          title="${esc(wave.key)}${wave.label ? ` · ${esc(wave.label)}` : ""} — ${what}. Click to show only this ${esc(m.wave.term)}.">
        <span class="node-bar"><span class="node-fill" style="height:${pct}%"></span></span>
        <span class="node-age">${esc(wave.key)}</span>
        <span class="node-n">${n ? n.toLocaleString("en-GB") : "—"}</span>
      </button></li>`;
    })
    .join("");
}

/* ── The topic rows ──────────────────────────────────────────────────── */

const isSelected = (kind, id) => state.topicSel.some((s) => s.kind === kind && s.id === id);

/* A cohort's per-sweep counts for one topic or domain of the merged scheme, from its tally
   (which counts by the cohort's own indices); null when the cohort's scheme lacks it. */
function countsFor(r, kind, id) {
  const idx = schemeIndex(manifestOf(r.cohort).topics);
  const i = (kind === "d" ? idx.domain : idx.topic).get(id);
  if (i === undefined) return null;
  return (kind === "d" ? r.tally.domains : r.tally.topics)[i];
}

function topicRow(kind, item, r, allMax, expanded) {
  const { id, label } = item;
  const counts = countsFor(r, kind, id) || new Uint32Array(manifestOf(r.cohort).wave.list.length);
  const on = isSelected(kind, id);
  const domainOfTopic = schemeIndex(state.scheme).domainOf;
  const partly =
    kind === "d" &&
    !on &&
    state.topicSel.some((s) => s.kind === "t" && domainOfTopic.get(s.id) === id);
  const rowMax = Math.max(1, ...counts);
  const waves = manifestOf(r.cohort).wave.list;
  const total = counts.reduce((a, b) => a + b, 0);
  const cells = [...counts]
    .map((c, w) => {
      const what = `${esc(label)} at ${esc(waves[w].key)}: ${c.toLocaleString("en-GB")}`;
      const col = state.waveFilter?.cohort === r.cohort && state.waveFilter.i === w;
      return `<button class="tg-cell${col ? " is-col" : ""}"
          data-l="${shade(c, rowMax, allMax, state.options.gridShade)}" data-cell="${kind}:${esc(id)}:${esc(r.cohort)}:${w}"
          title="${what} variable${c === 1 ? "" : "s"}" aria-label="${what}"></button>`;
    })
    .join("");
  const chevron =
    kind === "d"
      ? `<button class="tg-chev" data-expand="${esc(id)}" aria-expanded="${expanded}"
         aria-label="${expanded ? "Hide" : "Show"} the topics in ${esc(label)}">${expanded ? "▾" : "▸"}</button>`
      : "";
  const swatch =
    kind === "d"
      ? `<span class="dom-swatch" data-domain="${esc(id)}" aria-hidden="true"></span>`
      : "";
  return `<div class="ov-row tg-row${kind === "t" ? " is-topic" : ""}${on ? " is-on" : ""}${partly ? " is-part" : ""}">
    <div class="ov-label">${chevron}<button class="tg-name" data-row="${kind}:${esc(id)}" aria-pressed="${on}"
        title="${esc(item.description || "")}"><span class="tg-box" aria-hidden="true"></span>${swatch}<span class="tg-text">${esc(label)}</span></button>
      <span class="ov-count">${total ? total.toLocaleString("en-GB") : "—"}</span></div>
    <div class="tg-cells">${cells}</div></div>`;
}

/** Draw the topic rows from the last search's tally; hidden when the cohort has no topics. */
export function renderTopicGrid() {
  const has = state.domains.length > 0;
  $("#tgrid").hidden = !has;
  if (!has) return;
  $("#min-conf").value = String(state.options.minConf);
  $("#shade").value = state.options.gridShade;
  // The threshold and the shading sit with the topic rows, out of the way until opened.
  const open = state.options.gridOpen;
  $("#tg-tools").hidden = !open;
  $("#tgrid-toggle").setAttribute("aria-expanded", String(open));
  $("#tgrid-toggle .tg-caret").textContent = open ? "▾" : "▸";
  const body = $("#tgrid-body");
  body.hidden = !open;
  if (!open) return;

  const r = state.results[0];
  if (!r) return;
  const allMax = Math.max(1, ...r.tally.domains.flatMap((row) => [...row]));
  const parts = [];
  for (const d of state.domains) {
    const expanded = state.gridExpanded.has(d.id);
    parts.push(topicRow("d", d, r, allMax, expanded));
    if (!expanded) continue;
    for (const t of d.topics) parts.push(topicRow("t", t, r, allMax, false));
  }
  body.innerHTML = parts.join("");
}

/**
 * Make clicks in the overview call back. Opening and closing the topic rows is handled here.
 * @param {{onWave: (cohort: string, wave: number) => void,
 *   onTopic: (kind: string, id: string) => void,
 *   onCell: (kind: string, id: string, cohort: string, wave: number) => void,
 *   onOptions: () => void}} on Called with a clicked sweep bar (its cohort and sweep index),
 *   topic name or topic cell, and after the threshold or shading changes (state.options
 *   already updated).
 */
export function wireOverview({ onWave, onTopic, onCell, onOptions }) {
  $("#spine-track").addEventListener("click", (e) => {
    const btn = e.target.closest("[data-wave]");
    if (btn) onWave(btn.dataset.cohort, Number(btn.dataset.wave));
  });
  $("#tgrid-toggle").addEventListener("click", () => {
    state.options.gridOpen = !state.options.gridOpen;
    renderTopicGrid();
  });
  $("#min-conf").addEventListener("change", (e) => {
    state.options.minConf = Number(e.target.value);
    onOptions();
  });
  $("#shade").addEventListener("change", (e) => {
    state.options.gridShade = e.target.value;
    onOptions();
  });
  $("#tgrid-body").addEventListener("click", (e) => {
    const exp = e.target.closest("[data-expand]");
    if (exp) {
      const d = exp.dataset.expand;
      if (state.gridExpanded.has(d)) state.gridExpanded.delete(d);
      else state.gridExpanded.add(d);
      return renderTopicGrid();
    }
    const name = e.target.closest("[data-row]");
    if (name) {
      const [kind, id] = name.dataset.row.split(":");
      return onTopic(kind, id);
    }
    const cell = e.target.closest("[data-cell]");
    if (cell) {
      const [kind, id, key, w] = cell.dataset.cell.split(":");
      onCell(kind, id, key, Number(w));
    }
  });
}
