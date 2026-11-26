/* The top of the Variables view: every matching variable by sweep, and the topic rows
   beneath, which are the topic filter.

   With several cohorts chosen (feature 007) it is still one row of bars, on one age axis
   (core/ages.js): each bar is stacked by cohort, in proportion and in each cohort's colour,
   and each topic row's cells likewise. A bar or cell then stands for an age, across the
   cohorts. With one cohort it is the overview as before.

   Sweeps with no matches are drawn as gaps rather than left out: absence is usually the
   thing you need to know.

   The topic rows are a tree: domains, each opening onto its topics. A name toggles that
   domain or topic in the filter; the cells beside it are the same thing by sweep, and a
   cell narrows to that topic at that sweep. */

import { ageAxis, cells } from "../core/ages.js";
import { colourSlot } from "../core/cohorts.js";
import { esc } from "../core/text.js";
import { schemeIndex, shade } from "../core/topics.js";
import { cohort, manifestOf, state } from "./state.js";

const $ = (sel) => document.querySelector(sel);
const fmt = (x) => x.toLocaleString("en-GB");
const several = () => state.chosen.length > 1;
const nameOf = (key) => state.catalogue.find((d) => d.key === key)?.name || key;
const slotOf = (key) =>
  colourSlot(
    key,
    state.catalogue.map((d) => d.key),
  );
const plural = (k) => `${fmt(k)} variable${k === 1 ? "" : "s"}`;

/* The age axis over the loaded cohorts, and for each column the sweep each cohort has
   there: [{cohort, i}], in catalogue order. */
function axisColumns() {
  const ready = state.results.map((r) => ({ key: r.cohort, m: manifestOf(r.cohort) }));
  const axis = ageAxis(ready.map((c) => c.m));
  const per = ready.map(({ key, m }) => ({ key, at: cells(axis, m) }));
  return axis.columns.map((c, j) => ({
    label: c.label,
    sweeps: per.filter((p) => p.at[j] !== null).map((p) => ({ cohort: p.key, i: p.at[j] })),
  }));
}

/* The age filter a column stands for. */
const ageFilter = (col, j) => ({
  col: j,
  label: col.label,
  sweeps: Object.fromEntries(col.sweeps.map((s) => [s.cohort, s.i])),
});
const ageText = (label) => (label === "?" ? "age not known" : `age ${label}`);
const isAgeOn = (j) => state.waveFilter?.sweeps !== undefined && state.waveFilter.col === j;

/* Segments of a stacked bar, first cohort at the bottom: [{cohort, n}] with n > 0. */
const stack = (parts) =>
  parts
    .filter((p) => p.n > 0)
    .map(
      (p) =>
        `<span class="coh-seg" data-cohort="${esc(p.cohort)}" data-coh="${slotOf(p.cohort)}" style="flex-grow:${p.n}"></span>`,
    )
    .join("");

/**
 * Draw one bar per sweep, in manifest (time) order, from the last search; with several
 * cohorts, one bar per age, stacked by cohort.
 * @param {boolean} filtered Whether any filter or query is active.
 */
export function renderSpine(filtered) {
  $("#spine-title").textContent = filtered ? "Matching variables" : "All variables";
  if (several()) return renderStacked();
  const r = state.results[0];
  if (!r) {
    $("#spine-track").innerHTML = "";
    return;
  }
  const m = manifestOf(r.cohort);
  const { perWave } = r;
  const waves = m.wave.list;
  const max = Math.max(1, ...perWave);
  const total = perWave.reduce((a, b) => a + b, 0);
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

/* Several cohorts: a bar per age column, its segments each cohort's sweep there. */
function renderStacked() {
  const columns = axisColumns();
  const sizes = columns.map((c) =>
    c.sweeps.map((s) => ({
      ...s,
      n: state.results.find((r) => r.cohort === s.cohort).perWave[s.i],
    })),
  );
  const totals = sizes.map((parts) => parts.reduce((a, p) => a + p.n, 0));
  const max = Math.max(1, ...totals);
  $("#spine-note").textContent = fmt(totals.reduce((a, b) => a + b, 0));
  $("#spine-track").innerHTML = columns
    .map((c, j) => {
      const n = totals[j];
      const pct = n ? Math.max(6, Math.round((n / max) * 100)) : 0;
      const who = sizes[j]
        .map((p) => `${nameOf(p.cohort)} ${fmt(p.n)} (${manifestOf(p.cohort).wave.list[p.i].key})`)
        .join(", ");
      const age = ageText(c.label);
      return `<li data-col="${j}"><button class="node${n ? "" : " is-empty"}" data-col="${j}"
          aria-pressed="${isAgeOn(j)}"
          title="${esc(age[0].toUpperCase() + age.slice(1))} — ${plural(n)}: ${esc(who)}">
        <span class="node-bar"><span class="node-fill is-stack" style="height:${pct}%">${stack(sizes[j])}</span></span>
        <span class="node-age">${esc(c.label)}</span>
        <span class="node-n">${n ? fmt(n) : "—"}</span>
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

/* Several cohorts: each topic or domain row is one row, its cells on the age axis, each
   cell stacked by cohort. A cohort without topic tags is named above the rows. */
function renderTopicGrids(body) {
  const columns = axisColumns();
  const tagged = state.results.filter((r) => manifestOf(r.cohort).topics);
  const untagged = state.chosen.filter(
    (key) => cohort(key)?.status === "ready" && !manifestOf(key).topics,
  );
  // Each row's counts per column and cohort, so the shading can compare across rows.
  const rowsOf = (kind, item) =>
    columns.map((c) =>
      c.sweeps.map((s) => {
        const r = tagged.find((x) => x.cohort === s.cohort);
        const counts = r && countsFor(r, kind, item.id);
        return { ...s, n: counts ? counts[s.i] : 0 };
      }),
    );
  const domainRows = state.domains.map((d) => rowsOf("d", d));
  const allMax = Math.max(
    1,
    ...domainRows.flatMap((row) => row.map((parts) => parts.reduce((a, p) => a + p.n, 0))),
  );
  const parts = [];
  if (untagged.length) {
    const names = untagged.map(nameOf);
    const list =
      names.length > 1 ? `${names.slice(0, -1).join(", ")} and ${names.at(-1)}` : names[0];
    parts.push(
      `<p class="tg-none">${esc(list)} ${names.length > 1 ? "have" : "has"} no topic tags.</p>`,
    );
  }
  state.domains.forEach((d, k) => {
    const expanded = state.gridExpanded.has(d.id);
    parts.push(stackedRow("d", d, columns, domainRows[k], allMax, expanded));
    if (!expanded) return;
    for (const t of d.topics)
      parts.push(stackedRow("t", t, columns, rowsOf("t", t), allMax, false));
  });
  body.innerHTML = parts.join("");
}

function stackedRow(kind, item, columns, row, allMax, expanded) {
  const totals = row.map((parts) => parts.reduce((a, p) => a + p.n, 0));
  const total = totals.reduce((a, b) => a + b, 0);
  const rowMax = Math.max(1, ...totals);
  const top = state.options.gridShade === "within" ? rowMax : allMax;
  const cellsHtml = columns
    .map((c, j) => {
      const n = totals[j];
      const who = row[j]
        .filter((p) => p.n > 0)
        .map((p) => `${nameOf(p.cohort)} ${fmt(p.n)}`)
        .join(", ");
      const what = `${item.label} at ${ageText(c.label)}: ${fmt(n)}${who ? ` (${who})` : ""}`;
      const pct = n ? Math.max(12, Math.round((n / top) * 100)) : 0;
      return `<button class="tg-cell is-stack${isAgeOn(j) ? " is-col" : ""}" data-col="${j}"
          data-l="${n ? "x" : "0"}" data-cell="${kind}:${esc(item.id)}:${j}"
          title="${esc(what)}" aria-label="${esc(what)}"><span class="tg-stack" style="height:${pct}%">${stack(row[j])}</span></button>`;
    })
    .join("");
  return topicLabel(kind, item, total, expanded).replace(
    '<div class="tg-cells"></div>',
    `<div class="tg-cells">${cellsHtml}</div>`,
  );
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
 * @param {{onWave: (filter: object) => void,
 *   onTopic: (kind: string, id: string) => void,
 *   onCell: (kind: string, id: string, filter: object) => void,
 *   onOptions: () => void}} on Called with a clicked bar's sweep or age filter (`{cohort, i}`,
 *   or with several cohorts `{col, label, sweeps}`), a topic name, a topic cell (its topic
 *   and the same kind of filter), and after the threshold or shading changes
 *   (state.options already updated).
 */
export function wireOverview({ onWave, onTopic, onCell, onOptions }) {
  // A column's age filter, from the columns as last drawn.
  const ageAt = (j) => ageFilter(axisColumns()[j], j);
  $("#spine-track").addEventListener("click", (e) => {
    const btn = e.target.closest("button.node");
    if (!btn) return;
    if (btn.dataset.col !== undefined) onWave(ageAt(Number(btn.dataset.col)));
    else onWave({ cohort: btn.dataset.cohort, i: Number(btn.dataset.wave) });
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
    if (!cell) return;
    const parts = cell.dataset.cell.split(":");
    if (parts.length === 3) onCell(parts[0], parts[1], ageAt(Number(parts[2])));
    else onCell(parts[0], parts[1], { cohort: parts[2], i: Number(parts[3]) });
  });
}
