/* The top of the Variables view: what the cohort is, every matching variable by sweep, and
   the topic rows beneath, which are the topic filter.

   Sweeps with no matches are drawn as gaps rather than left out: absence is usually the
   thing you need to know.

   The topic rows are a tree: domains, each opening onto its topics. A name toggles that
   domain or topic in the filter; the cells beside it are the same thing by sweep, and a
   cell narrows to that topic at that sweep. */

import { esc } from "../core/text.js";
import { shade } from "../core/topics.js";
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

/* ── The topic rows ──────────────────────────────────────────────────── */

const isSelected = (kind, i) => state.topicSel.some((s) => s.kind === kind && s.i === i);

function topicRow(kind, i, counts, allMax, expanded) {
  const item = kind === "d" ? state.domains[i] : state.topics[i];
  const label = item.label;
  const on = isSelected(kind, i);
  const partly =
    kind === "d" &&
    !on &&
    state.topicSel.some((s) => s.kind === "t" && state.topics[s.i].domain === i);
  const rowMax = Math.max(1, ...counts);
  const waves = state.manifest.wave.list;
  const total = counts.reduce((a, b) => a + b, 0);
  const cells = [...counts]
    .map((c, w) => {
      const what = `${esc(label)} at ${esc(waves[w].key)}: ${c.toLocaleString("en-GB")}`;
      return `<button class="tg-cell${state.waveFilter === w ? " is-col" : ""}"
          data-l="${shade(c, rowMax, allMax, state.options.gridShade)}" data-cell="${kind}:${i}:${w}"
          title="${what} variable${c === 1 ? "" : "s"}" aria-label="${what}"></button>`;
    })
    .join("");
  const chevron =
    kind === "d"
      ? `<button class="tg-chev" data-expand="${i}" aria-expanded="${expanded}"
         aria-label="${expanded ? "Hide" : "Show"} the topics in ${esc(label)}">${expanded ? "▾" : "▸"}</button>`
      : "";
  const swatch =
    kind === "d"
      ? `<span class="dom-swatch" data-domain="${esc(item.id)}" aria-hidden="true"></span>`
      : "";
  return `<div class="ov-row tg-row${kind === "t" ? " is-topic" : ""}${on ? " is-on" : ""}${partly ? " is-part" : ""}">
    <div class="ov-label">${chevron}<button class="tg-name" data-row="${kind}:${i}" aria-pressed="${on}"
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

  const { topics, domains } = state.tally;
  const allMax = Math.max(1, ...domains.flatMap((r) => [...r]));
  const parts = [];
  state.domains.forEach((_, di) => {
    const expanded = state.gridExpanded.has(di);
    parts.push(topicRow("d", di, domains[di], allMax, expanded));
    if (!expanded) return;
    state.topics.forEach((t, ti) => {
      if (t.domain === di) parts.push(topicRow("t", ti, topics[ti], allMax, false));
    });
  });
  body.innerHTML = parts.join("");
}

/**
 * Make clicks in the overview call back. Opening and closing the topic rows is handled here.
 * @param {{onWave: (wave: number) => void, onTopic: (kind: string, i: number) => void,
 *   onCell: (kind: string, i: number, wave: number) => void, onOptions: () => void}} on
 *   Called with a clicked sweep bar, topic name or topic cell, and after the threshold or
 *   shading changes (state.options already updated).
 */
export function wireOverview({ onWave, onTopic, onCell, onOptions }) {
  $("#spine-track").addEventListener("click", (e) => {
    const btn = e.target.closest("[data-wave]");
    if (btn) onWave(Number(btn.dataset.wave));
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
      const d = Number(exp.dataset.expand);
      if (state.gridExpanded.has(d)) state.gridExpanded.delete(d);
      else state.gridExpanded.add(d);
      return renderTopicGrid();
    }
    const name = e.target.closest("[data-row]");
    if (name) {
      const [kind, i] = name.dataset.row.split(":");
      return onTopic(kind, Number(i));
    }
    const cell = e.target.closest("[data-cell]");
    if (cell) {
      const [kind, i, w] = cell.dataset.cell.split(":");
      onCell(kind, Number(i), Number(w));
    }
  });
}
