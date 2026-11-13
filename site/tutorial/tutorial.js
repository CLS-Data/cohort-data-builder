// Tutorial page: live counts from ../data, and working copies of the builder's controls.
// It borrows only the builder's stylesheet; the demo variables below are copied from the
// BCS70 dictionary.
"use strict";

/* The theme: the builder's own setting, so the two pages always match. */
const THEME_KEY = "cohort-data-builder:_site:theme";
try {
  const stored = JSON.parse(localStorage.getItem(THEME_KEY));
  if (stored === "light" || stored === "dark") document.documentElement.dataset.theme = stored;
} catch {
  // No storage: follow the system setting.
}

// topic id → [label, domain id]
const TOPICS = {
  smoking: ["Smoking", "health_behaviour"],
  pregnancy_history: ["Pregnancy", "pregnancy"],
  employment: ["Occupation and employment", "employment_income"],
  childcare: ["Childcare", "family_social"],
  benefits: ["Benefits and welfare", "employment_income"],
  home_life: ["Home life", "family_social"],
  travel_transport: ["Travel and transport", "housing_environment"],
  leisure: ["Leisure activities", "family_social"],
  school_engagement: ["School engagement", "education"],
};

// [value, label]; `na` lists the ranges of codes that count as missing.
const VARIABLES = [
  {
    name: "bd7smoke",
    label: "(Derived) Smoking habits",
    sweep: "34/35",
    file: "bcs_2004_followup",
    values: [
      [-7, "Other missing"],
      [0, "never smoked"],
      [1, "ex smoker"],
      [2, "occasional smoker"],
      [3, "up to 10 a day"],
      [4, "11 to 20 a day"],
      [5, "more than 20 a day"],
      [6, "daily but frequency not stated"],
    ],
    na: [[-9, -1]],
    topics: [["smoking", 0.9]],
  },
  {
    name: "B10AGESTR",
    label: "Age started smoking regularly",
    sweep: "46/48",
    file: "bcs_age46_main",
    values: [
      [-9, "Refused"],
      [-8, "Not known"],
      [-1, "Not applicable"],
    ],
    na: [
      [-9, -8],
      [-1, -1],
    ],
    topics: [["smoking", 0.9]],
  },
  {
    name: "b11nfcigs",
    label: "Number of cigarettes a day usually smoked",
    sweep: "51/53",
    file: "bcs11_age51_main",
    values: [
      [-9, "Refused"],
      [-8, "Don't know"],
      [-3, "Not asked at case fieldwork stage"],
      [-2, "Not asked due to scripting/routing error"],
      [-1, "Not applicable"],
    ],
    na: [[-10, -1]],
    topics: [["smoking", 0.9]],
  },
  {
    name: "cgprega4",
    label: "(P2) MC:Whether smoked during pregnancy",
    sweep: "29/30",
    file: "bcs2000",
    values: [
      [1, "Smoked in 3 mths before preg"],
      [2, "Smoked in mths 1-5 of preg"],
      [3, "Smoked in mths 6-9 of preg"],
      [4, "Did not smoke in 3 months before preg"],
      [8, "Dont know"],
      [9, "Not answered"],
    ],
    na: [],
    topics: [
      ["smoking", 0.9],
      ["pregnancy_history", 0.9],
    ],
  },
  {
    name: "cpregb8",
    label: "(P8) Whether smoked more, less or same as before",
    sweep: "29/30",
    file: "bcs2000",
    values: [
      [1, "More"],
      [2, "Less"],
      [3, "Same"],
    ],
    na: [],
    topics: [
      ["smoking", 0.9],
      ["pregnancy_history", 0.8],
    ],
  },
  {
    name: "bd7smk11",
    label: "(Derived) Smoked in the 3 months before pregnancy (P1)",
    sweep: "34/35",
    file: "bcs_2004_followup",
    values: [
      [-9, "Refusal"],
      [-8, "Don't know"],
      [-6, "No information available"],
      [-1, "Not applicable"],
      [0, "No"],
      [1, "Yes"],
    ],
    na: [[-9, -1]],
    topics: [
      ["smoking", 0.9],
      ["pregnancy_history", 0.6],
    ],
  },
  {
    name: "b7smkml2",
    label: "Whether smoked more / less during pregnancy (P2)",
    sweep: "34/35",
    file: "bcs_2004_followup",
    values: [
      [-9, "Refusal"],
      [-8, "Don't Know"],
      [-7, "Other missing"],
      [-6, "No information available"],
      [-1, "Not applicable"],
      [1, "More"],
      [2, "Less"],
      [3, "Same"],
    ],
    na: [[-9, -1]],
    topics: [["smoking", 0.9]],
  },
];

const CONFIDENCE_EXAMPLES = [
  {
    name: "b7ynojo4",
    label: "Reasons for not having a job at the moment - 4",
    topics: [
      ["employment", 0.9],
      ["childcare", 0.6],
      ["benefits", 0.5],
    ],
  },
  {
    name: "sec288",
    label: "Secondary activity 2021 MTUS (time-use diary)",
    topics: [
      ["home_life", 0.9],
      ["employment", 0.7],
      ["travel_transport", 0.6],
      ["leisure", 0.6],
      ["school_engagement", 0.6],
    ],
  },
  {
    name: "bd7smk11",
    label: "(Derived) Smoked in the 3 months before pregnancy (P1)",
    topics: [
      ["smoking", 0.9],
      ["pregnancy_history", 0.6],
    ],
  },
];

// BCS70: variables per topic and sweep (topic confidence ≥ 0.5), main sweeps only.
const HEAT_SWEEPS = ["0", "5", "10", "16", "26", "30", "34", "38", "42", "46", "51"];
const HEAT = [
  ["Smoking", "health_behaviour", [6, 6, 23, 157, 3, 36, 47, 4, 5, 28, 7]],
  ["Housing", "housing_environment", [19, 28, 55, 96, 14, 178, 104, 75, 161, 11, 52]],
  ["Occupation and employment", "employment_income", [12, 12, 66, 1949, 65, 301, 263, 204, 158, 99, 251]],
  ["School engagement", "education", [0, 5, 279, 1412, 2, 18, 67, 2, 2, 0, 0]],
  ["Respiratory system", "physical_health", [17, 16, 90, 55, 6, 22, 10, 3, 5, 17, 39]],
  ["Emotions and behaviour", "mental_health", [8, 32, 211, 321, 3, 35, 160, 0, 20, 30, 38]],
];
const SHADE_TEXT = {
  within:
    "Within each topic: each row is shaded against its own busiest sweep, so you can see when a topic peaks, even a rare one like smoking.",
  across:
    "Across topics: every cell is on one scale, so you can see which topics dominate the study overall. Rare topics fade out.",
};

const RUN = { r: "Rscript R/merge.R", py: "python python/merge.py", stata: "do stata/merge.do" };
const FORMATS = { CSV: "a CSV file", Stata: "a Stata (.dta) file", SPSS: "an SPSS (.sav) file" };
const EXT = { CSV: "csv", Stata: "dta", SPSS: "sav" };

const $ = (sel) => document.querySelector(sel);
const fmt = (n) => n.toLocaleString("en-GB");
const plural = (n, word) => `${fmt(n)} ${word}${n === 1 ? "" : "s"}`;

function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") node.className = v;
    else node.setAttribute(k, v);
  }
  for (const c of children) if (c !== null) node.append(c);
  return node;
}

function topicChip(id, conf, cls = "topic-chip") {
  const [label, domain] = TOPICS[id] || [id, ""];
  return el("span", { class: cls, "data-domain": domain }, `${label} `, el("span", { class: "vm-pct" }, `${Math.round(conf * 100)}%`));
}

const isMissing = (v, na) => na.some(([lo, hi]) => v >= lo && v <= hi);

/* Live counts */

async function loadCounts() {
  try {
    const { datasets } = await (await fetch("../data/datasets.json")).json();
    $("#t-cohorts").textContent = fmt(datasets.length);
    $("#t-total").textContent = fmt(datasets.reduce((s, d) => s + d.variables, 0));
    const list = $("#t-cohort-list");
    for (const d of datasets) list.append(el("li", {}, `${d.name} `, el("span", {}, fmt(d.variables))));
    const manifest = await (await fetch(`../data/${datasets[0].key}/manifest.json`)).json();
    const domains = manifest.topics?.domains || [];
    $("#t-domains").textContent = fmt(domains.length);
    $("#t-topics").textContent = fmt(domains.reduce((s, d) => s + (d.topics || []).length, 0));
    const dl = $("#t-domain-list");
    for (const d of domains) {
      dl.append(
        el(
          "li",
          {},
          el("span", { class: "dom-swatch", "data-domain": d.id, "aria-hidden": "true" }),
          el("span", {}, d.label),
          el("span", {}, String((d.topics || []).length)),
        ),
      );
    }
  } catch {
    for (const id of ["#t-cohorts", "#t-total", "#t-topics", "#t-domains"]) $(id).textContent = "–";
  }
}

/* Step 1: search */

function details(v, id) {
  const kept = v.values.filter(([c]) => !isMissing(c, v.na));
  const na = v.values.filter(([c]) => isMissing(c, v.na));
  const valueList = (rows, cls) =>
    el(
      "ul",
      { class: cls },
      ...rows.map(([code, label]) => el("li", {}, el("span", { class: "vm-code" }, String(code)), ` ${label}`)),
    );
  return el(
    "div",
    { class: "vrow-more", id, hidden: "" },
    kept.length ? el("div", { class: "vm-topics" }, el("span", { class: "vm-key" }, "Values"), valueList(kept, "vm-values")) : null,
    na.length ? el("div", { class: "vm-topics" }, el("span", { class: "vm-key" }, "Missing"), valueList(na, "vm-values is-na")) : null,
    el("div", { class: "vm-topics" }, el("span", { class: "vm-key" }, "Topics"), ...v.topics.map(([t, c]) => topicChip(t, c, "vm-topic"))),
    el("p", { class: "vm-meta vm-dim" }, `Sweep ${v.sweep} · file ${v.file}`),
  );
}

function renderSearch() {
  const q = $("#search-input").value.trim().toLowerCase();
  const hits = VARIABLES.filter((v) => !q || v.name.toLowerCase().includes(q) || v.label.toLowerCase().includes(q));
  $("#search-count").textContent = plural(hits.length, "variable");
  const ol = $("#search-rows");
  ol.replaceChildren();
  if (!hits.length) {
    ol.append(el("li", { class: "t-empty" }, `No variables match “${q}”.`));
    return;
  }
  for (const v of hits) {
    const id = `d-${v.name}`;
    const btn = el(
      "button",
      { type: "button", class: "v-expand", "aria-expanded": "false", "aria-controls": id, "aria-label": `Show details for ${v.name}` },
      "▸",
    );
    const more = details(v, id);
    btn.addEventListener("click", () => {
      const open = btn.getAttribute("aria-expanded") !== "true";
      btn.setAttribute("aria-expanded", String(open));
      btn.textContent = open ? "▾" : "▸";
      more.hidden = !open;
      row.classList.toggle("is-open", open);
    });
    const row = el(
      "li",
      { class: "vrow t-row demo-row", "data-domain": TOPICS[v.topics[0][0]][1] },
      el(
        "div",
        { class: "t-row-main" },
        btn,
        el("span", { class: "v-name" }, v.name),
        el("span", { class: "v-label", title: v.label }, v.label),
        el("span", { class: "v-wave" }, v.sweep),
      ),
      more,
    );
    ol.append(row);
  }
}

/* Step 2: the topic map */

let shade = "within";
let topic = null;

// Share of the contour colour for a cell: never quite blank, so a cell with any variables
// in it still shows.
const level = (n, top) => (6 + (94 * n) / top).toFixed(1);

function renderMap() {
  const all = Math.max(...HEAT.flatMap(([, , row]) => row));
  $("#heat").dataset.shade = shade;
  $("#shade-explain").textContent = SHADE_TEXT[shade];

  // The bars: the topic chosen, else all six together.
  const rows = topic === null ? HEAT : [HEAT[topic]];
  const sums = HEAT_SWEEPS.map((_, i) => rows.reduce((s, [, , r]) => s + r[i], 0));
  const top = Math.max(...sums);
  $("#spine-name").textContent = topic === null ? "All six topics" : HEAT[topic][0];
  $("#spine-total").textContent = fmt(sums.reduce((a, b) => a + b, 0));
  $("#spine").replaceChildren(
    ...sums.map((n, i) =>
      el(
        "li",
        { class: n ? "node" : "node is-empty", title: `Age ${HEAT_SWEEPS[i]}: ${plural(n, "variable")}` },
        el("span", { class: "node-bar" }, el("span", { class: "node-fill", style: `height: ${n ? Math.max(8, (100 * n) / top) : 0}%` })),
        el("span", { class: "node-n" }, fmt(n)),
      ),
    ),
  );

  const body = $("#heat-body");
  body.replaceChildren();
  HEAT.forEach(([name, domain, row], t) => {
    const max = shade === "within" ? Math.max(...row) : all;
    const on = topic === t;
    const pick = el(
      "button",
      { type: "button", class: "tg-name", "aria-pressed": String(on), title: `Show ${name} alone` },
      el("span", { class: "tg-box", "aria-hidden": "true" }),
      el("span", { class: "dom-swatch", "data-domain": domain, "aria-hidden": "true" }),
      el("span", { class: "tg-text" }, name),
    );
    pick.addEventListener("click", () => {
      topic = on ? null : t;
      renderMap();
      body.querySelectorAll(".tg-name")[t].focus();
    });
    body.append(
      el(
        "div",
        { class: `ov-row tg-row${on ? " is-on" : ""}` },
        el("div", { class: "ov-label" }, pick, el("span", { class: "ov-count" }, fmt(row.reduce((a, b) => a + b, 0)))),
        el(
          "div",
          { class: "tg-cells" },
          ...row.map((n, i) => {
            const pct = level(n, max);
            return el(
              "span",
              {
                class: "tg-cell heat-cell",
                "data-l": n ? "x" : "0",
                style: n ? `background: color-mix(in srgb, var(--contour) ${pct}%, transparent)` : "",
                title: `${name}, age ${HEAT_SWEEPS[i]}: ${plural(n, "variable")}`,
              },
              el("span", { class: "visually-hidden" }, fmt(n)),
            );
          }),
        ),
      ),
    );
  });
}

function setupMap() {
  $("#heat-sweeps").append(...HEAT_SWEEPS.map((s) => el("span", {}, s === "0" ? "birth" : `${s}y`)));
  for (const input of document.querySelectorAll('input[name="shade"]')) {
    input.addEventListener("change", () => {
      shade = input.value;
      renderMap();
    });
  }
  renderMap();
}

/* Step 3: selection */

function setupSelection() {
  const items = VARIABLES.slice(0, 5);
  const picked = new Set();
  let anchor = null;
  let group = "sweep";
  const rows = items.map((v, i) => {
    const b = el(
      "button",
      { type: "button", class: "t-row-main", "aria-pressed": "false", "aria-label": `Select ${v.name}` },
      el("span", { class: "v-check", "aria-hidden": "true" }, "＋"),
      el("span", { class: "v-name" }, v.name),
      el("span", { class: "v-label" }, v.label),
    );
    b.addEventListener("click", (e) => {
      if (e.shiftKey && anchor !== null) {
        const [a, z] = anchor < i ? [anchor, i] : [i, anchor];
        for (let k = a; k <= z; k++) picked.add(k);
      } else {
        if (picked.has(i)) picked.delete(i);
        else picked.add(i);
        anchor = i;
      }
      paint();
    });
    const li = el("li", { class: "vrow t-row", "data-domain": TOPICS[v.topics[0][0]][1] }, b);
    $("#select-rows").append(li);
    return [li, b];
  });

  function paint() {
    rows.forEach(([li, b], i) => {
      const on = picked.has(i);
      li.classList.toggle("is-in", on);
      b.setAttribute("aria-pressed", String(on));
      b.querySelector(".v-check").textContent = on ? "✓" : "＋";
    });
    $("#select-count").textContent = `${picked.size} selected`;
    const panel = $("#select-panel");
    panel.replaceChildren();
    if (!picked.size) {
      panel.append(el("li", { class: "t-none" }, "Click a row to add it here."));
      return;
    }
    const groups = new Map();
    for (const i of [...picked].sort((a, b) => a - b)) {
      const key = group === "sweep" ? `Age ${items[i].sweep}` : items[i].file;
      groups.set(key, [...(groups.get(key) || []), items[i].name]);
    }
    for (const [key, names] of groups) {
      panel.append(el("li", { class: "t-group" }, key), ...names.map((n) => el("li", { class: "t-item" }, n)));
    }
  }

  const groupButtons = document.querySelectorAll("#select-demo [data-group]");
  for (const b of groupButtons) {
    b.addEventListener("click", () => {
      group = b.dataset.group;
      for (const o of groupButtons) o.setAttribute("aria-pressed", String(o === b));
      paint();
    });
  }
  $("#select-clear").addEventListener("click", () => {
    picked.clear();
    anchor = null;
    paint();
  });
  paint();
}

/* Step 4: download options */

/* "R", "R and Python", "R, Python and Stata". */
const listOf = (names) =>
  names.length < 2 ? names.join("") : `${names.slice(0, -1).join(", ")} and ${names.at(-1)}`;

function renderSummary() {
  const form = $("#download-demo");
  const langs = [...form.querySelectorAll('input[name="lang"]:checked')].map((i) => i.value);
  const format = form.querySelector('input[name="fmt"]:checked').value;
  const na = $("#dl-na").checked;
  $("#dl-summary").textContent = langs.length
    ? `You get ${langs.length > 1 ? `${listOf(langs)} code that each write` : `${langs[0] === "Stata" ? "a Stata do-file" : `an ${langs[0]} project`} that writes`} ${FORMATS[format]}, with missing codes ${na ? "turned into NA" : "kept as they are"}.`
    : "Choose at least one language.";
  const lines = ["<b>cohort-data-builder-project.zip</b>", "├─ README.md", "├─ codebook.csv", "├─ data/        ← your copy goes here"];
  if (langs.includes("R")) lines.push("├─ R/merge.R");
  if (langs.includes("Python")) lines.push("├─ python/merge.py");
  if (langs.includes("Stata")) lines.push("├─ stata/merge.do");
  lines.push(`└─ output/merged.${EXT[format]}`);
  $("#dl-tree").innerHTML = lines.join("\n");
}

/* Step 5: run */

function setupRun() {
  const buttons = document.querySelectorAll("#run [data-lang]");
  for (const b of buttons) {
    b.addEventListener("click", () => {
      for (const o of buttons) o.setAttribute("aria-pressed", String(o === b));
      $("#run-cmd").textContent = RUN[b.dataset.lang];
    });
  }
}

/* Topics: confidence threshold */

function renderConfidence(min) {
  $("#conf-list").replaceChildren(
    ...CONFIDENCE_EXAMPLES.map((v) =>
      el(
        "li",
        {},
        el("span", { class: "v-name" }, v.name),
        el("span", { class: "v-label" }, v.label),
        el(
          "div",
          { class: "chips" },
          ...v.topics.map(([t, c]) => {
            const chip = topicChip(t, c, c < min ? "chip is-off" : "chip");
            if (c < min) chip.title = "Below the threshold: hidden in the builder";
            return chip;
          }),
        ),
      ),
    ),
  );
}

function setupConfidence() {
  const buttons = document.querySelectorAll("#conf-buttons button");
  for (const b of buttons) {
    b.addEventListener("click", () => {
      for (const o of buttons) o.setAttribute("aria-pressed", String(o === b));
      renderConfidence(Number(b.dataset.min));
    });
  }
  renderConfidence(0.5);
}

/* The theme button, as in the builder. */

function setupTheme() {
  const root = document.documentElement;
  $("#theme").addEventListener("click", () => {
    const now = root.dataset.theme || (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
    root.dataset.theme = now === "dark" ? "light" : "dark";
    try {
      localStorage.setItem(THEME_KEY, JSON.stringify(root.dataset.theme));
    } catch {
      // Not remembered: fine.
    }
  });
}

document.addEventListener("DOMContentLoaded", () => {
  setupTheme();
  loadCounts();
  $("#search-input").addEventListener("input", renderSearch);
  renderSearch();
  setupMap();
  setupSelection();
  $("#download-demo").addEventListener("change", renderSummary);
  $("#download-demo").addEventListener("submit", (e) => e.preventDefault());
  renderSummary();
  setupRun();
  setupConfidence();
});
