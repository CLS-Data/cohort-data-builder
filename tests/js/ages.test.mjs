import assert from "node:assert/strict";
import { before, test } from "node:test";
import { ageAxis, ageLabel, cells, sweepAge } from "../../site/js/core/ages.js";
import { readFixture } from "./helpers.mjs";

let mini;
let mini2;
let mini3;

before(async () => {
  mini = await readFixture("mini/manifest.json");
  mini2 = await readFixture("mini2/manifest.json");
  mini3 = await readFixture("mini3/manifest.json");
});

test("sweepAge: the explicit age, else an age-shaped key, else null", () => {
  assert.equal(sweepAge({ key: "14y" }), 14);
  assert.equal(sweepAge({ key: "9m" }), 0.75);
  assert.equal(sweepAge({ key: "2.5y" }), 2.5);
  assert.equal(sweepAge({ key: "w2", age: 7 }), 7);
  assert.equal(sweepAge({ key: "5y", age: 6 }), 6, "explicit wins over the key");
  assert.equal(sweepAge({ key: "xwave" }), null);
  assert.equal(sweepAge({ key: "34/35" }), null);
  assert.equal(sweepAge({ key: "y5" }), null);
});

test("ageLabel: months under one, whole years plainly, else one decimal", () => {
  assert.equal(ageLabel(0.75), "9m");
  assert.equal(ageLabel(0), "0");
  assert.equal(ageLabel(11), "11");
  assert.equal(ageLabel(2.5), "2.5");
  assert.equal(ageLabel(null), "?");
});

test("one cohort: the columns are its sweeps, in order, labelled by key", () => {
  const axis = ageAxis([mini]);
  assert.deepEqual(
    axis.columns.map((c) => c.label),
    ["5y", "10y", "xwave"],
  );
  assert.deepEqual(cells(axis, mini), [0, 1, 2]);
});

test("several cohorts: the sorted union of ages, unknown ages last", () => {
  const axis = ageAxis([mini, mini2]);
  assert.deepEqual(
    axis.columns.map((c) => c.age),
    [3, 5, 7, 10, 11, null],
  );
  assert.deepEqual(
    axis.columns.map((c) => c.label),
    ["3", "5", "7", "10", "11", "?"],
  );
  assert.deepEqual(cells(axis, mini), [null, 0, null, 1, null, 2]);
  assert.deepEqual(cells(axis, mini2), [0, null, 1, null, 2, 3]);
});

test("a cohort with no unknown sweep leaves the unknown column empty", () => {
  const axis = ageAxis([mini, mini3]);
  assert.deepEqual(
    axis.columns.map((c) => c.age),
    [5, 10, 16, null],
  );
  assert.deepEqual(cells(axis, mini3), [null, null, 0, null]);
});

test("each cohort's unknown sweeps take their own unknown column, in order", () => {
  const two = {
    ...mini3,
    wave: { ...mini3.wave, list: [{ key: "a" }, { key: "16y" }, { key: "b" }] },
  };
  const axis = ageAxis([mini, two]);
  assert.deepEqual(
    axis.columns.map((c) => c.age),
    [5, 10, 16, null, null],
  );
  assert.deepEqual(cells(axis, mini), [0, 1, null, 2, null]);
  assert.deepEqual(cells(axis, two), [null, null, 1, 0, 2]);
});

test("ages that differ only by rounding share a column", () => {
  const a = { key: "a", wave: { list: [{ key: "x", age: 0.75 }] } };
  const b = { key: "b", wave: { list: [{ key: "9m" }] } };
  const axis = ageAxis([a, b]);
  assert.equal(axis.columns.length, 1);
  assert.equal(axis.columns[0].label, "9m");
});
