import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { before, test } from "node:test";
import { buildProject, codebook } from "../../site/js/core/codegen.js";
import { readFixture } from "./helpers.mjs";

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
const TODAY = "2026-10-26";
const PROJECT = `mini-merge-${TODAY}`;

let manifest;
let dicts;
let templates;
let selection;

const sel = (name, file, wave, column = name) => {
  const entry = dicts[file].variables.find((v) => v.variable === name);
  return { name, label: entry.label, file, wave, column };
};
const options = (o = {}) => ({
  languages: ["r", "python"],
  missingToNa: true,
  outputFormat: "csv",
  ...o,
});
const build = (o, s = selection) => buildProject(s, manifest, dicts, templates, options(o), TODAY);
const file = (project, path) => project.files.find(([p]) => p === `${PROJECT}/${path}`)?.[1];

before(async () => {
  manifest = await readFixture("mini/manifest.json");
  dicts = {};
  for (const f of manifest.files) dicts[f.name] = await readFixture(`mini/dict/${f.name}.json`);
  templates = {};
  for (const t of TEMPLATE_FILES) {
    templates[t] = await readFile(new URL(`../../site/templates/${t}`, import.meta.url), "utf8");
  }
  selection = [
    sel("smoke5", "mini_age5", "5y"),
    sel("quote5", "mini_age5", "5y"),
    sel("tenure5", "mini_age5", "5y"),
    sel("sex", "mini_age5", "5y"),
    sel("sex", "mini_age10", "10y", "sex_10y"),
    sel("alc10", "mini_age10", "10y"),
    sel("mood10", "mini_age10", "10y"),
    sel("weight10", "mini_age10", "10y"),
    sel("hhrel", "mini_grid", "10y"),
  ];
});

test("the project is named after the cohort and date, with the contract's files", () => {
  const both = build();
  assert.equal(both.name, PROJECT);
  const paths = (p) => p.files.map(([path]) => path.slice(PROJECT.length + 1)).sort();
  const common = ["README.md", "codebook.csv", "data/README.md"];
  const r = [`${PROJECT}.Rproj`, "R/load_data.R", "R/merge.R"];
  const py = ["python/load_data.py", "python/merge.py", "python/requirements.txt"];
  assert.deepEqual(paths(both), [...common, ...r, ...py].sort());
  assert.deepEqual(paths(build({ languages: ["r"] })), [...common, ...r].sort());
  assert.deepEqual(paths(build({ languages: ["python"] })), [...common, ...py].sort());
});

test("no placeholder is left in any file", () => {
  for (const o of [{}, { missingToNa: false, outputFormat: "sav" }]) {
    for (const [path, text] of build(o).files) assert.ok(!text.includes("{{"), path);
  }
});

test("dictionary text in code is escaped, newlines becoming spaces", () => {
  const p = build();
  const label = String.raw`"Mother said \"fine\"\\not fine second line"`;
  assert.ok(file(p, "R/merge.R").includes(`"quote5" = ${label}`));
  assert.ok(file(p, "python/merge.py").includes(`"quote5": ${label},`));
});

test("SELECTION is grouped by file, column = variable", () => {
  const p = build();
  assert.ok(
    file(p, "R/merge.R").includes(
      '  "mini_age10" = c(\n    "sex_10y" = "sex",\n    "alc10" = "alc10",',
    ),
  );
  assert.ok(
    file(p, "python/merge.py").includes(
      '    "mini_age10": {\n        "sex_10y": "sex",\n        "alc10": "alc10",',
    ),
  );
});

test("MISSING_CODES come only from the supplied values and ranges", () => {
  const p = build();
  const r = file(p, "R/merge.R");
  const py = file(p, "python/merge.py");
  assert.ok(r.includes('  "sex" = list(values = c(-9), ranges = list())'));
  assert.ok(r.includes('  "tenure5" = list(values = numeric(0), ranges = list(c(NA, -1)))'));
  assert.ok(r.includes('  "alc10" = list(values = numeric(0), ranges = list(c(-9, -2)))'));
  assert.ok(r.includes('  "mood10" = list(values = c(-8), ranges = list())'));
  assert.ok(py.includes('    "tenure5": {"values": [], "ranges": [[None, -1]]},'));
  const codes = r.slice(r.indexOf("MISSING_CODES <- list("), r.indexOf("LABELS <- list("));
  for (const absent of ["smoke5", "sex_10y", "weight10", "hhrel"]) {
    assert.ok(!codes.includes(`"${absent}"`), absent);
  }
  assert.ok(!codes.includes("Dislike"));
});

test("MISSING_TO_NA and OUTPUT_FORMAT follow the options", () => {
  const on = build({ outputFormat: "dta" });
  assert.ok(file(on, "R/merge.R").includes("MISSING_TO_NA <- TRUE"));
  assert.ok(file(on, "python/merge.py").includes("MISSING_TO_NA = True"));
  assert.ok(file(on, "R/merge.R").includes('OUTPUT_FORMAT <- "dta"'));
  const off = build({ missingToNa: false });
  assert.ok(file(off, "R/merge.R").includes("MISSING_TO_NA <- FALSE"));
  assert.ok(file(off, "python/merge.py").includes("MISSING_TO_NA = False"));
});

test("LABELS start with the identifier", () => {
  const r = file(build(), "R/merge.R");
  assert.ok(r.includes('LABELS <- list(\n  "PID" = "Identifier: every file is merged on this",'));
});

test("VALUE_LABELS only for whole-number codes, first label per code", () => {
  const odd = structuredClone(dicts);
  const values = odd.mini_age5.variables.find((v) => v.variable === "smoke5").values;
  values.push({ value: "1.0", label: "Yes again" });
  odd.mini_age5.variables
    .find((v) => v.variable === "tenure5")
    .values.push({ value: "2.5", label: "Half" });
  const p = buildProject(selection, manifest, odd, templates, options(), TODAY);
  const r = file(p, "R/merge.R");
  const vl = r.slice(r.indexOf("VALUE_LABELS <- list("));
  assert.ok(vl.includes('  "smoke5" = c("Yes" = 1, "No" = 2)'));
  assert.ok(!vl.includes('"tenure5"'));
  assert.ok(!vl.includes('"weight10"'));
  assert.ok(file(p, "python/merge.py").includes('    "smoke5": {1: "Yes", 2: "No"},'));
});

test("the README is filled in and its missing-codes note follows the option", () => {
  const on = file(build(), "README.md");
  assert.match(on, /^# Mini: 9 variables/);
  assert.ok(on.includes("`mini_grid`"));
  assert.ok(on.includes("https://example.org/mini"));
  assert.match(on, /converted to NA/);
  assert.match(file(build({ missingToNa: false }), "README.md"), /kept as deposited/);
  assert.equal(on.split("codebook.csv       what every output column is").length - 1, 1);
});

test("codebook header, identifier row and field formats", () => {
  const lines = codebook(selection, manifest, dicts).split("\n");
  assert.equal(
    lines[0],
    "column,variable,file,wave,label,missing_codes,negative_kept,value_labels,topics",
  );
  assert.equal(lines[1], "PID,PID,,,Identifier: every file is merged on this,,,,");
  const text = lines.join("\n");
  assert.ok(
    text.includes("alc10,alc10,mini_age10,10y,How often drinks alcohol,-9 to -2,-1=Dislike,"),
  );
  assert.ok(
    text.includes(
      "tenure5,tenure5,mini_age5,5y,Housing tenure of the family home,-1 and below,,1=Owned; 2=Rented; -1=Not applicable,Tenure (0.60)",
    ),
  );
});

test("codebook quotes commas, quotes and newlines (RFC 4180)", () => {
  const text = codebook(selection, manifest, dicts);
  assert.ok(
    text.includes('quote5,quote5,mini_age5,5y,"Mother said ""fine""\\not fine\nsecond line",'),
  );
  const odd = [{ name: "x", label: "a, b", file: "mini_age5", wave: "5y", column: "x" }];
  const lines = codebook(odd, manifest, dicts).trim().split("\n");
  assert.equal(lines[2], 'x,x,mini_age5,5y,"a, b",,,,');
});

test("every template has the placeholders the contract requires", () => {
  const required = {
    "r/merge.R":
      "dataset created identifier missing_to_na selection missing_codes output_format labels value_labels",
    "python/merge.py":
      "dataset created identifier missing_to_na selection missing_codes output_format labels value_labels",
    "README.md":
      "dataset full_name created count files languages contents ext format_note identifier ukds_url missing_note run",
    "data-README.md": "dataset files ukds_url",
  };
  for (const [name, keys] of Object.entries(required)) {
    for (const key of keys.split(" ")) {
      assert.ok(templates[name].includes(`{{${key}}}`), `${name} lacks {{${key}}}`);
    }
  }
});
