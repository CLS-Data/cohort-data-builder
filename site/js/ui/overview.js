/* The top of the Variables view: what the cohort is, every matching variable by sweep, and
   the topic rows beneath, which are the topic filter.

   With several cohorts chosen (feature 007) the sweeps line up on one age axis
   (core/ages.js): an axis row, then a row of bars per cohort; and every topic or domain row
   has a sub-row per cohort on the same columns. With one cohort it is the overview as before.

   Sweeps with no matches are drawn as gaps rather than left out: absence is usually the
   thing you need to know.

   The topic rows are a tree: domains, each opening onto its topics. A name toggles that
   domain or topic in the filter; the cells beside it are the same thing by sweep, and a
   cell narrows to that topic at that sweep. */

import { ageAxis, ageLabel, cells, sweepAge } from "../core/ages.js";
import { colourSlot } from "../core/cohorts.js";
import { esc } from "../core/text.js";
import { schemeIndex, shade } from "../core/topics.js";
import { cohort, manifestOf, RETRY_EVENT, readyCohorts, state } from "./state.js";

const $ = (sel) => document.querySelector(sel);
const fmt = (x) => x.toLocaleString("en-GB");
const several = () => state.chosen.length > 1;
const nameOf = (key) => state.catalogue.find((d) => d.key === key)?.name || key;
const slotOf = (key) =>
  colourSlot(
    key,
    state.catalogue.map((d) => d.key),
  );
const mark = (key) => `<span class="coh-mark" data-coh="${slotOf(key)}" aria-hidden="true"></span>`;
const axisOf = () => ageAxis(readyCohorts().map((c) => c.manifest));

/* A cohort's label in a row: its mark, short name and a count. */
const cohLabel = (key, count) =>
  `<div class="ov-label">${mark(key)}<span class="ov-coh-name">${esc(nameOf(key))}</span>
    <span class="ov-count">${count}</span></div>`;

/* In place of a loading or failed cohort's cells. */
function cohState(key) {
  const c = cohort(key);
  if (c?.status === "failed") {
    return `<p class="ov-state vm-warn">Could not load ${esc(nameOf(key))}.
      <button class="link-btn" data-retry="${esc(key)}">Retry</button></p>`;
  }
  return `<p class="ov-state">Loading ${esc(nameOf(key))}…</p>`;
}

/** Write the line saying what the cohort is and how big it is. */
export function renderAbout() {
  // One line per chosen cohort, from its manifest once loaded, else the catalogue.
  const several = state.chosen.length > 1;
  const keys = state.catalogue.map((d) => d.key);
  $("#ov-about").innerHTML = state.chosen
    .map((key) => {
      const m = cohort(key)?.manifest || state.catalogue.find((d) => d.key === key);
      const counts = m.counts || { variables: m.variables, files: m.files };
      const mark = several
        ? `<span class="coh-mark" data-coh="${colourSlot(key, keys)}" aria-hidden="true"></span>`
        : "";
      return (
        `<span class="ov-about-line">${mark}<strong>${esc(m.fullName || m.name)}</strong>${m.description ? ` — ${esc(m.description)}` : ""} ` +
        `<span class="vm-dim">${counts.variables.toLocaleString("en-GB")} variables in ${counts.files} file${counts.files === 1 ? "" : "s"}.</span></span>`
      );
    })
    .join(several ? "<br>" : "");
}

/**
 * Draw one bar per sweep, in manifest (time) order, from the last search.
 * @param {boolean} filtered Whether any filter or query is active.
 */
export function renderSpine(filtered) {
  const multi = several();
  $("#ov-chart").classList.toggle("is-several", multi);
  $("#spine-track").classList.toggle("is-axis", multi);
  if (multi) return renderSpines(filtered);
  $("#spine-rows").innerHTML = "";
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

/* Several cohorts: the axis in the first row, then a row of bars per cohort. */
function renderSpines(filtered) {
  const axis = axisOf();
  $("#ov-chart").style.setProperty("--cols", String(axis.columns.length));
  const total = state.results.reduce((a, r) => a + r.matches.length, 0);
  const max = Math.max(1, ...state.results.flatMap((r) => r.perWave));
  $("#spine-title").textContent = filtered ? "Matching variables" : "All variables";
  $("#spine-note").textContent = fmt(total);
  $("#spine-track").innerHTML = axis.columns
    .map(
      (c) =>
        `<li title="${c.age === null ? "Age not known" : `Age ${esc(c.label)}`}">${esc(c.label)}</li>`,
    )
    .join("");
  $("#spine-rows").innerHTML = state.chosen
    .map((key) => {
      const c = cohort(key);
      const r = state.results.find((x) => x.cohort === key);
      if (c?.status !== "ready" || !r) {
        return `<div class="ov-row ov-coh" data-cohort="${esc(key)}">${cohLabel(key, "")}${cohState(key)}</div>`;
      }
      const m = c.manifest;
      const bars = cells(axis, m)
        .map((i, j) => {
          if (i === null) return `<li data-col="${j}"></li>`;
          const wave = m.wave.list[i];
          const n = r.perWave[i];
          const pct = n ? Math.max(6, Math.round((n / max) * 100)) : 0;
          const age = sweepAge(wave);
          const on = state.waveFilter?.cohort === key && state.waveFilter.i === i;
          return `<li data-col="${j}"><button class="node${n ? "" : " is-empty"}" data-cohort="${esc(key)}" data-wave="${i}"
              aria-pressed="${on}"
              title="${esc(nameOf(key))} ${esc(wave.key)} (${age === null ? "age not known" : `age ${ageLabel(age)}`}) — ${fmt(n)} variable${n === 1 ? "" : "s"}">
            <span class="node-bar"><span class="node-fill" style="height:${pct}%"></span></span></button></li>`;
        })
        .join("");
      return `<div class="ov-row ov-coh" data-cohort="${esc(key)}">${cohLabel(key, fmt(r.matches.length))}
        <ol class="spine-track" aria-label="${esc(nameOf(key))}: matches by sweep">${bars}</ol></div>`;
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

  if (several()) return renderTopicGrids(body);
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

/* Several cohorts: each topic or domain row gives the total across them, and beneath it a
   sub-row per chosen cohort with its cells on the age axis. */
function renderTopicGrids(body) {
  const axis = axisOf();
  const allMax = Math.max(
    1,
    ...state.results.flatMap((r) => r.tally.domains.flatMap((row) => [...row])),
  );
  const parts = [];
  for (const d of state.domains) {
    const expanded = state.gridExpanded.has(d.id);
    parts.push(topicRowMulti("d", d, axis, allMax, expanded));
    if (!expanded) continue;
    for (const t of d.topics) parts.push(topicRowMulti("t", t, axis, allMax, false));
  }
  body.innerHTML = parts.join("");
}

function topicRowMulti(kind, item, axis, allMax, expanded) {
  const { id, label } = item;
  const per = new Map(
    state.results.map((r) => [
      r.cohort,
      manifestOf(r.cohort).topics ? countsFor(r, kind, id) : undefined,
    ]),
  );
  const total = [...per.values()].reduce((a, c) => a + (c ? c.reduce((x, y) => x + y, 0) : 0), 0);
  const head = topicLabel(kind, item, total, expanded);
  const subs = state.chosen
    .map((key) => {
      const open = `<div class="ov-row tg-sub" data-of="${kind}:${esc(id)}" data-cohort="${esc(key)}">`;
      const c = cohort(key);
      if (c?.status !== "ready" || !per.has(key))
        return `${open}${cohLabel(key, "")}<div></div></div>`;
      const counts = per.get(key);
      if (counts === undefined) {
        return `${open}${cohLabel(key, "")}<p class="tg-none">no topic tags</p></div>`;
      }
      if (counts === null) {
        return `${open}${cohLabel(key, "—")}<p class="tg-none">not among ${esc(nameOf(key))}'s topics</p></div>`;
      }
      const waves = c.manifest.wave.list;
      const rowMax = Math.max(1, ...counts);
      const sum = counts.reduce((a, b) => a + b, 0);
      const row = cells(axis, c.manifest)
        .map((i, j) => {
          if (i === null) return `<span class="tg-cell is-none" data-col="${j}"></span>`;
          const n = counts[i];
          const what = `${label}, ${nameOf(key)} at ${waves[i].key}: ${fmt(n)}`;
          const col = state.waveFilter?.cohort === key && state.waveFilter.i === i;
          return `<button class="tg-cell${col ? " is-col" : ""}" data-col="${j}"
              data-l="${shade(n, rowMax, allMax, state.options.gridShade)}" data-cell="${kind}:${esc(id)}:${esc(key)}:${i}"
              title="${esc(what)} variable${n === 1 ? "" : "s"}" aria-label="${esc(what)}"></button>`;
        })
        .join("");
      return `${open}${cohLabel(key, sum ? fmt(sum) : "—")}<div class="tg-cells">${row}</div></div>`;
    })
    .join("");
  return `${head}${subs}`;
}

/* A topic or domain row's label part and an empty cells part, with its total. */
function topicLabel(kind, item, total, expanded) {
  const { id, label } = item;
  const on = isSelected(kind, id);
  const domainOfTopic = schemeIndex(state.scheme).domainOf;
  const partly =
    kind === "d" &&
    !on &&
    state.topicSel.some((s) => s.kind === "t" && domainOfTopic.get(s.id) === id);
  const chevron =
    kind === "d"
      ? `<button class="tg-chev" data-expand="${esc(id)}" aria-expanded="${expanded}"
         aria-label="${expanded ? "Hide" : "Show"} the topics in ${esc(label)}">${expanded ? "▾" : "▸"}</button>`
      : "";
  const swatch =
    kind === "d"
      ? `<span class="dom-swatch" data-domain="${esc(id)}" aria-hidden="true"></span>`
      : "";
  return `<div class="ov-row tg-row${kind === "t" ? " is-topic" : ""}${on ? " is-on" : ""}${partly ? " is-part" : ""}" data-id="${kind}:${esc(id)}">
    <div class="ov-label">${chevron}<button class="tg-name" data-row="${kind}:${esc(id)}" aria-pressed="${on}"
        title="${esc(item.description || "")}"><span class="tg-box" aria-hidden="true"></span>${swatch}<span class="tg-text">${esc(label)}</span></button>
      <span class="ov-count">${total ? fmt(total) : "—"}</span></div>
    <div class="tg-cells"></div></div>`;
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
  $("#spine-rows").addEventListener("click", (e) => {
    const retry = e.target.closest("[data-retry]");
    if (retry) {
      document.dispatchEvent(new CustomEvent(RETRY_EVENT, { detail: retry.dataset.retry }));
      return;
    }
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
