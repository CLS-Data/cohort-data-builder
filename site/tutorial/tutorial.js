// Tutorial page: live counts from ../data, and the hands-on demos. Self-contained: it shares
// no code with the builder, and the demo variables below are copied from the BCS70 dictionary.
"use strict";

const TOPIC_LABELS = {
  smoking: "Smoking",
  pregnancy_history: "Pregnancy",
  employment: "Occupation and employment",
  childcare: "Childcare",
  benefits: "Benefits and welfare",
  home_life: "Home life",
  travel_transport: "Travel and transport",
  leisure: "Leisure activities",
  school_engagement: "School engagement",
};

// [value, label]; `na` lists the codes that count as missing.
const VARIABLES = [
  {
    name: "bd7smoke",
    label: "(Derived) Smoking habits",
    sweep: "Age 34/35",
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
    sweep: "Age 46/48",
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
    sweep: "Age 51/53",
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
    sweep: "Age 29/30",
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
    sweep: "Age 29/30",
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
    sweep: "Age 34/35",
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
    sweep: "Age 34/35",
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
const HEAT_SWEEPS = ["Birth", "5", "10", "16", "26", "30", "34", "38", "42", "46", "51"];
const HEAT = [
  ["Smoking", [6, 6, 23, 157, 3, 36, 47, 4, 5, 28, 7]],
  ["Housing", [19, 28, 55, 96, 14, 178, 104, 75, 161, 11, 52]],
  ["Occupation and employment", [12, 12, 66, 1949, 65, 301, 263, 204, 158, 99, 251]],
  ["School engagement", [0, 5, 279, 1412, 2, 18, 67, 2, 2, 0, 0]],
  ["Respiratory system", [17, 16, 90, 55, 6, 22, 10, 3, 5, 17, 39]],
  ["Emotions and behaviour", [8, 32, 211, 321, 3, 35, 160, 0, 20, 30, 38]],
];
const SHADE_TEXT = {
  within:
    "Each topic is shaded against its own busiest sweep, so you can see when a topic peaks, even a rare one like smoking.",
  across:
    "Every cell is on one scale, so you can see which topics dominate the study overall. Rare topics fade out.",
};

const RUN = { r: "Rscript R/merge.R", py: "python python/merge.py" };
const FORMATS = { CSV: "a CSV file", Stata: "a Stata (.dta) file", SPSS: "an SPSS (.sav) file" };

const CHEVRON =
  '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M9 6l6 6-6 6"/></svg>';
const TICK =
  '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12l5 5 9-10"/></svg>';

const $ = (sel) => document.querySelector(sel);
const fmt = (n) => n.toLocaleString("en-GB");

function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") node.className = v;
    else if (k === "html") node.innerHTML = v;
    else node.setAttribute(k, v);
  }
  for (const c of children) node.append(c);
  return node;
}

function chip(id, conf, min = 0) {
  const off = conf < min;
  return el(
    "span",
    { class: off ? "chip is-off" : "chip" },
    `${TOPIC_LABELS[id] || id} `,
    el("b", {}, conf.toFixed(1)),
  );
}

const isMissing = (v, na) => na.some(([lo, hi]) => v >= lo && v <= hi);

/* Live counts */

async function loadCounts() {
  try {
    const res = await fetch("../data/datasets.json");
    const { datasets } = await res.json();
    $("#t-cohorts").textContent = fmt(datasets.length);
    $("#t-total").textContent = fmt(datasets.reduce((s, d) => s + d.variables, 0));
    const list = $("#t-cohort-list");
    for (const d of datasets) {
      list.append(el("li", {}, `${d.name} `, el("span", {}, `${fmt(d.variables)} variables`)));
    }
    const manifest = await (await fetch(`../data/${datasets[0].key}/manifest.json`)).json();
    const domains = manifest.topics?.domains || [];
    $("#t-domains").textContent = fmt(domains.length);
    $("#t-topics").textContent = fmt(domains.reduce((s, d) => s + (d.topics || []).length, 0));
    const dl = $("#t-domain-list");
    for (const d of domains) {
      dl.append(el("li", {}, d.label, el("span", {}, String((d.topics || []).length))));
    }
  } catch {
    for (const id of ["#t-cohorts", "#t-total", "#t-topics", "#t-domains"]) $(id).textContent = "–";
  }
}

/* Step 1: search */

function renderSearch() {
  const q = $("#search-input").value.trim().toLowerCase();
  const hits = VARIABLES.filter(
    (v) => !q || v.name.toLowerCase().includes(q) || v.label.toLowerCase().includes(q),
  );
  $("#search-count").textContent = `${hits.length} variable${hits.length === 1 ? "" : "s"}`;
  const ul = $("#search-rows");
  ul.replaceChildren();
  if (!hits.length) {
    ul.append(el("li", { class: "empty" }, `No variables match “${q}”.`));
    return;
  }
  for (const v of hits) {
    const id = `d-${v.name}`;
    const btn = el("button", {
      type: "button",
      class: "expand",
      "aria-expanded": "false",
      "aria-controls": id,
      "aria-label": `Show details for ${v.name}`,
      html: CHEVRON,
    });
    const details = el(
      "div",
      { class: "details", id, hidden: "" },
      el(
        "div",
        {},
        el("h4", {}, "Value labels"),
        el(
          "ul",
          { class: "vals" },
          ...v.values.map(([code, label]) => {
            const na = isMissing(code, v.na);
            return el(
              "li",
              { class: na ? "is-na" : "" },
              el("span", { class: "code" }, String(code)),
              el("span", {}, na ? `${label} · missing` : label),
            );
          }),
        ),
      ),
      el(
        "div",
        {},
        el("h4", {}, "Topics"),
        el("div", { class: "chips" }, ...v.topics.map(([t, c]) => chip(t, c))),
      ),
    );
    btn.addEventListener("click", () => {
      const open = btn.getAttribute("aria-expanded") !== "true";
      btn.setAttribute("aria-expanded", String(open));
      details.hidden = !open;
    });
    ul.append(
      el(
        "li",
        { class: "demo-row" },
        el(
          "div",
          { class: "row-line" },
          btn,
          el("span", { class: "row-name" }, v.name),
          el("span", { class: "row-label", title: v.label }, v.label),
          el("span", { class: "row-sweep" }, v.sweep),
        ),
        details,
      ),
    );
  }
}

/* Step 2: topic map */

function renderHeat(shade) {
  const all = Math.max(...HEAT.flatMap(([, row]) => row));
  $("#heat").dataset.shade = shade;
  $("#shade-explain").textContent = SHADE_TEXT[shade];
  const body = $("#heat-body");
  body.replaceChildren();
  for (const [topic, row] of HEAT) {
    const top = shade === "within" ? Math.max(...row) : all;
    body.append(
      el(
        "tr",
        {},
        el("th", { scope: "row" }, topic),
        ...row.map((n, i) => {
          const a = n ? 0.1 + 0.85 * (n / top) : 0.03;
          return el(
            "td",
            {
              class: "heat-cell",
              style: `background-color: rgba(var(--heat), ${a.toFixed(3)})`,
              title: `${topic}, ${HEAT_SWEEPS[i] === "Birth" ? "birth" : `age ${HEAT_SWEEPS[i]}`}: ${fmt(n)} variables`,
            },
            el("span", { class: "sr" }, fmt(n)),
          );
        }),
      ),
    );
  }
}

function setupHeat() {
  const head = $("#heat-sweeps");
  for (const s of HEAT_SWEEPS) head.append(el("th", { scope: "col" }, s));
  for (const input of document.querySelectorAll('input[name="shade"]')) {
    input.addEventListener("change", () => renderHeat(input.value));
  }
  renderHeat("within");
}

/* Step 3: selection */

function setupSelection() {
  const items = VARIABLES.slice(0, 5);
  const picked = new Set();
  let anchor = null;
  const ul = $("#select-rows");
  const buttons = items.map((v, i) => {
    const b = el(
      "button",
      { type: "button", class: "pick", "aria-pressed": "false", "aria-label": `Select ${v.name}` },
      el("span", { class: "box", html: TICK }),
      el("span", { class: "row-name" }, v.name),
      el("span", { class: "row-label" }, v.label),
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
    ul.append(el("li", {}, b));
    return b;
  });
  function paint() {
    buttons.forEach((b, i) => {
      b.setAttribute("aria-pressed", String(picked.has(i)));
    });
    $("#select-count").textContent = `${picked.size} selected`;
  }
  $("#select-clear").addEventListener("click", () => {
    picked.clear();
    anchor = null;
    paint();
  });
}

/* Step 4: download options */

function renderSummary() {
  const form = $("#download-demo");
  const langs = [...form.querySelectorAll('input[name="lang"]:checked')].map((i) => i.value);
  const format = form.querySelector('input[name="fmt"]:checked').value;
  const na = $("#dl-na").checked;
  $("#dl-summary").textContent = langs.length
    ? `You get ${langs.length > 1 ? "R and Python projects that each write" : `an ${langs[0]} project that writes`} ${FORMATS[format]}, with missing codes ${na ? "turned into NA" : "kept as they are"}.`
    : "Choose at least one language.";
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

/* Topics: confidence filter */

function renderConfidence(min) {
  const ul = $("#conf-list");
  ul.replaceChildren(
    ...CONFIDENCE_EXAMPLES.map((v) =>
      el(
        "li",
        {},
        el("div", { class: "conf-name" }, v.name),
        el("div", { class: "conf-label" }, v.label),
        el("div", { class: "chips" }, ...v.topics.map(([t, c]) => chip(t, c, min))),
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

document.addEventListener("DOMContentLoaded", () => {
  loadCounts();
  $("#search-input").addEventListener("input", renderSearch);
  renderSearch();
  setupHeat();
  setupSelection();
  $("#download-demo").addEventListener("change", renderSummary);
  $("#download-demo").addEventListener("submit", (e) => e.preventDefault());
  renderSummary();
  setupRun();
  setupConfidence();
});
