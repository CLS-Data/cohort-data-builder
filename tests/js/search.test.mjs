import assert from "node:assert/strict";
import { before, test } from "node:test";
import {
  buildLabelIndex,
  filterVariables,
  PAGE,
  page,
  sameLabel,
} from "../../site/js/core/search.js";
import { readFixture } from "./helpers.mjs";

let vars;
let manifest;
const any = { query: "", wave: null, file: null, level: null };
const names = (rows) => rows.map((r) => r[0]);

before(async () => {
  vars = await readFixture("mini/index.json");
  manifest = await readFixture("mini/manifest.json");
});

test("no filters matches everything, counted per sweep and level", () => {
  const { matches, perWave, perLevel } = filterVariables(vars, manifest, any);
  assert.equal(matches.length, 16);
  assert.deepEqual(perWave, [6, 9, 1]);
  assert.deepEqual(Object.fromEntries(perLevel), { 0: 11, 1: 3, 2: 1, "-1": 1 });
});

test("the query matches any part of a name or label, ignoring case", () => {
  assert.deepEqual(names(filterVariables(vars, manifest, { ...any, query: "SMOK" }).matches), [
    "smoke5",
  ]);
  assert.deepEqual(names(filterVariables(vars, manifest, { ...any, query: "person" }).matches), [
    "PID",
    "pid",
    "PID",
  ]);
  assert.deepEqual(names(filterVariables(vars, manifest, { ...any, query: "ure1" }).matches), [
    "tenure10",
  ]);
});

test("perWave counts after every filter, with a zero for an empty sweep", () => {
  const r = filterVariables(vars, manifest, { ...any, query: "sex" });
  assert.deepEqual(r.perWave, [1, 1, 0]);
  const w = filterVariables(vars, manifest, { ...any, query: "tenure", wave: 1 });
  assert.deepEqual(names(w.matches), ["tenure10"]);
  assert.deepEqual(w.perWave, [0, 1, 0]);
});

test("perLevel ignores the level filter but applies the others", () => {
  const r = filterVariables(vars, manifest, { ...any, wave: 1, level: 2 });
  assert.deepEqual(names(r.matches), ["weight10"]);
  assert.deepEqual(Object.fromEntries(r.perLevel), { 0: 5, 1: 2, 2: 1, "-1": 1 });
});

test("level -1 selects variables with no recorded level", () => {
  assert.deepEqual(names(filterVariables(vars, manifest, { ...any, level: -1 }).matches), [
    "misc10",
  ]);
  const noLevel = [["x", "no level field", 0, 0]];
  assert.deepEqual(Object.fromEntries(filterVariables(noLevel, manifest, any).perLevel), {
    "-1": 1,
  });
});

test("the file filter keeps one file", () => {
  assert.deepEqual(names(filterVariables(vars, manifest, { ...any, file: 2 }).matches), [
    "PID",
    "hhrel",
  ]);
});

const smoking = { kind: "t", i: 0 };
const alcohol = { kind: "t", i: 1 };
const housing = { kind: "d", i: 1 };

test("the topic filter keeps variables tagged at or above the threshold", () => {
  const f = (topicSel, topicMode, minConf) =>
    names(filterVariables(vars, manifest, { ...any, topicSel, topicMode, minConf }).matches);
  assert.deepEqual(f([smoking], "any", 50), ["smoke5"]);
  assert.deepEqual(f([alcohol], "any", 50), ["smoke5"]);
  assert.deepEqual(f([alcohol], "any", 30), ["smoke5", "alc10"]);
  assert.deepEqual(f([smoking, alcohol], "any", 30), ["smoke5", "alc10"]);
  assert.deepEqual(f([smoking, alcohol], "all", 30), ["smoke5"]);
  assert.deepEqual(f([housing], "any", 50), ["tenure5", "tenure10"]);
  assert.deepEqual(f([housing], "any", 70), ["tenure10"]);
  assert.deepEqual(f([], "all", 50).length, 16);
});

test("perLevel and perWave respect the topic filter", () => {
  const r = filterVariables(vars, manifest, { ...any, topicSel: [housing], minConf: 50 });
  assert.deepEqual(Object.fromEntries(r.perLevel), { 0: 2 });
  assert.deepEqual(r.perWave, [1, 1, 0]);
});

test("the topic tally ignores the sweep and topic filters but not query, file or level", () => {
  const base = { ...any, topicSel: [smoking], topicMode: "any", minConf: 30 };
  const counts = (filters) => {
    const { tally } = filterVariables(vars, manifest, filters);
    return [tally.topics.map((r) => [...r]), tally.domains.map((r) => [...r])];
  };
  assert.deepEqual(counts({ ...base, wave: 1 }), [
    [
      [1, 0, 0],
      [1, 1, 0],
      [1, 1, 0],
    ],
    [
      [1, 1, 0],
      [1, 1, 0],
    ],
  ]);
  assert.deepEqual(counts({ ...base, query: "tenure" })[0], [
    [0, 0, 0],
    [0, 0, 0],
    [1, 1, 0],
  ]);
  assert.deepEqual(counts({ ...base, level: 1 })[0], [
    [0, 0, 0],
    [0, 1, 0],
    [0, 0, 0],
  ]);
  assert.deepEqual(counts({ ...base, file: 0 })[1], [
    [1, 0, 0],
    [1, 0, 0],
  ]);
});

test("a cohort without topics ignores the topic filter and tallies nothing", () => {
  const plain = { ...manifest, topics: undefined };
  const r = filterVariables(vars, plain, { ...any, topicSel: [smoking], minConf: 50 });
  assert.equal(r.matches.length, 16);
  assert.deepEqual(r.tally, { topics: [], domains: [] });
});

test("no match gives empty matches and zero counts", () => {
  const r = filterVariables(vars, manifest, { ...any, query: "zzzz" });
  assert.deepEqual(r.matches, []);
  assert.deepEqual(r.perWave, [0, 0, 0]);
});

test("page shows 200 at a time and says how many are left", () => {
  const m = Array.from({ length: 450 }, (_, i) => [`v${i}`]);
  assert.equal(PAGE, 200);
  assert.deepEqual(
    (({ rows, left, next }) => [rows.length, left, next])(page(m, PAGE)),
    [200, 250, 200],
  );
  assert.deepEqual(
    (({ rows, left, next }) => [rows.length, left, next])(page(m, 2 * PAGE)),
    [400, 50, 50],
  );
  assert.deepEqual(
    (({ rows, left, next }) => [rows.length, left, next])(page(m, 3 * PAGE)),
    [450, 0, 0],
  );
});

const row = (name, label, wave) => [name, label, 0, wave, 0];

test("sameLabel finds identical labels after normalising case, spacing and end punctuation", () => {
  const a = row("a1", "Age of  mother at birth?", 2);
  const b = row("b1", "age of mother at birth", 0);
  const c = row("c1", "AGE OF MOTHER AT BIRTH.", 1);
  const index = buildLabelIndex([a, b, c, row("d1", "Something else entirely", 0)]);
  assert.deepEqual(sameLabel(index, a), { rows: [b, c], more: 0 });
});

test("sameLabel orders by sweep then name, shows at most 10 and counts the rest", () => {
  const rows = Array.from({ length: 13 }, (_, i) =>
    row(`v${String(i).padStart(2, "0")}`, "Shared label text", i % 3),
  );
  const { rows: shown, more } = sameLabel(buildLabelIndex(rows), rows[0]);
  assert.equal(shown.length, 10);
  assert.equal(more, 2);
  assert.deepEqual(names(shown).slice(0, 4), ["v03", "v06", "v09", "v12"]);
});

test("short labels are not indexed and huge groups give nothing", () => {
  const short = [row("a", "Area code", 0), row("b", "Area code", 1)];
  assert.deepEqual(sameLabel(buildLabelIndex(short), short[0]), { rows: [], more: 0 });
  const many = Array.from({ length: 41 }, (_, i) =>
    row(`v${i}`, "Boilerplate interviewer note", 0),
  );
  assert.deepEqual(sameLabel(buildLabelIndex(many), many[0]), { rows: [], more: 0 });
});

test("the fixture's shared labels are found across sweeps", async () => {
  const index = buildLabelIndex(vars);
  const tenure5 = vars.find((r) => r[0] === "tenure5");
  assert.deepEqual(names(sameLabel(index, tenure5).rows), ["tenure10"]);
});

test("filtering 35,000 rows takes well under the 0.5 s budget", () => {
  const big = Array.from({ length: 35000 }, (_, i) => [
    `VAR${i}`,
    i % 7 === 0 ? `Smoking question ${i}` : `Other question number ${i}`,
    i % 80,
    i % 12,
    i % 3,
  ]);
  const wide = {
    ...manifest,
    wave: { ...manifest.wave, list: Array.from({ length: 12 }, (_, i) => ({ key: `w${i}` })) },
  };
  filterVariables(big, wide, { ...any, query: "smok", wave: 3 }); // warm up
  const start = performance.now();
  const r = filterVariables(big, wide, { ...any, query: "smok", wave: 3 });
  const ms = performance.now() - start;
  assert.ok(r.matches.length > 0);
  assert.ok(ms < 100, `took ${ms.toFixed(1)} ms`);
});
