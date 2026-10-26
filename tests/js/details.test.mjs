import assert from "node:assert/strict";
import { before, test } from "node:test";
import { describeVariable } from "../../site/js/core/details.js";
import { readFixture } from "./helpers.mjs";

let manifest;
let dicts;
const entry = (file, name) => dicts[file].variables.find((v) => v.variable === name);
const file = (name) => manifest.files.find((f) => f.name === name);
const codes = (items) => items.map((v) => v.code);

before(async () => {
  manifest = await readFixture("mini/manifest.json");
  dicts = {};
  for (const f of manifest.files) dicts[f.name] = await readFixture(`mini/dict/${f.name}.json`);
});

test("value labels split into answers and missing codes (open-ended range)", () => {
  const d = describeVariable(entry("mini_age5", "tenure5"), file("mini_age5"), "PID");
  assert.deepEqual(d.answers, [
    { code: "1", label: "Owned" },
    { code: "2", label: "Rented" },
  ]);
  assert.deepEqual(d.missing, [{ code: "-1", label: "Not applicable", lossy: false }]);
  assert.deepEqual(d.more, []);
});

test("na.values mark missing codes; kept codes stay answers and are passed through", () => {
  const d = describeVariable(entry("mini_age10", "alc10"), file("mini_age10"), "PID");
  assert.deepEqual(codes(d.answers), ["1", "2", "-1"]);
  assert.deepEqual(codes(d.missing), ["-9"]);
  assert.deepEqual(d.kept, [[-1, "Dislike"]]);
});

test("a missing code also listed as lossy is flagged", () => {
  const d = describeVariable(entry("mini_age10", "mood10"), file("mini_age10"), "PID");
  assert.deepEqual(d.missing, [{ code: "-8", label: "Don't know", lossy: true }]);
  assert.deepEqual(d.lossy, [[-8, "Don't know"]]);
});

test("answers keep dictionary order and stop at 8, the rest in more", () => {
  const values = Array.from({ length: 11 }, (_, i) => ({ value: `${10 - i}.0`, label: `L${i}` }));
  const d = describeVariable({ variable: "x", values }, file("mini_age5"), "PID");
  assert.deepEqual(codes(d.answers), ["10", "9", "8", "7", "6", "5", "4", "3"]);
  assert.deepEqual(codes(d.more), ["2", "1", "0"]);
});

test("the identifier, in any case, is described as the identifier", () => {
  assert.deepEqual(describeVariable(entry("mini_age10", "pid"), file("mini_age10"), "PID"), {
    isIdentifier: true,
  });
});

test("a SCALE variable with no value labels is noted as continuous", () => {
  const d = describeVariable(entry("mini_age10", "weight10"), file("mini_age10"), "PID");
  assert.equal(d.note, "continuous");
  assert.deepEqual(d.answers, []);
});

test("no na and no kept or lossy give empty lists", () => {
  const d = describeVariable(entry("mini_age5", "smoke5"), file("mini_age5"), "PID");
  assert.deepEqual([d.missing, d.kept, d.lossy], [[], [], []]);
});

test("facts list file, study, position, level and type, omitting absent ones", () => {
  const full = describeVariable(
    { variable: "x", pos: "4", measurement: "NOMINAL", type: "numeric" },
    file("mini_age5"),
    "PID",
  );
  assert.deepEqual(full.facts, [
    { name: "File", value: "mini_age5", detail: "Age 5 interview" },
    { name: "Study", value: "SN 0000" },
    { name: "Position", value: "4" },
    { name: "Level", value: "Nominal" },
    { name: "Type", value: "numeric" },
  ]);
  const bare = describeVariable({ variable: "x" }, { name: "f" }, "PID");
  assert.deepEqual(bare.facts, [{ name: "File", value: "f" }]);
});
