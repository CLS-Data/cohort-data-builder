import assert from "node:assert/strict";
import { test } from "node:test";
import {
  chooseInitial,
  colourSlot,
  formatChoice,
  parseChoice,
  toggleChoice,
} from "../../site/js/core/cohorts.js";

const keys = ["mini", "mini2", "x"];

test("parseChoice keeps known keys, in catalogue order", () => {
  assert.deepEqual(parseChoice("#mini2+mini", keys), ["mini", "mini2"]);
  assert.deepEqual(parseChoice("mini2+mini", keys), ["mini", "mini2"]);
  assert.deepEqual(parseChoice("#mini2+nope", keys), ["mini2"]);
  assert.deepEqual(parseChoice("#mini+mini", keys), ["mini"]);
  assert.deepEqual(parseChoice("#nope", keys), []);
  assert.deepEqual(parseChoice("", keys), []);
  assert.deepEqual(parseChoice("#mini%2Bmini2", keys), ["mini", "mini2"]);
});

test("formatChoice writes catalogue order joined by +", () => {
  assert.equal(formatChoice(["mini2", "mini"], keys), "mini+mini2");
  assert.equal(formatChoice(["x"], keys), "x");
});

test("chooseInitial: the address, then the stored choice, then the old key, then the first", () => {
  const base = { hash: "", stored: null, storedOld: null, keys };
  assert.deepEqual(chooseInitial({ ...base, hash: "#x+mini" }), ["mini", "x"]);
  assert.deepEqual(chooseInitial({ ...base, hash: "#nope", stored: ["mini2"] }), ["mini2"]);
  assert.deepEqual(chooseInitial({ ...base, stored: ["nope"], storedOld: "x" }), ["x"]);
  assert.deepEqual(chooseInitial({ ...base, stored: "garbage", storedOld: 7 }), ["mini"]);
  assert.deepEqual(chooseInitial(base), ["mini"]);
  assert.deepEqual(chooseInitial({ ...base, keys: [] }), []);
});

test("toggleChoice adds or removes, keeps order and never removes the last", () => {
  assert.deepEqual(toggleChoice(["mini"], "mini", keys), ["mini"]);
  assert.deepEqual(toggleChoice(["mini"], "x", keys), ["mini", "x"]);
  assert.deepEqual(toggleChoice(["x"], "mini2", keys), ["mini2", "x"]);
  assert.deepEqual(toggleChoice(["mini", "x"], "mini", keys), ["x"]);
  assert.deepEqual(toggleChoice(["mini"], "nope", keys), ["mini"]);
});

test("colourSlot pins the real cohorts and gives others their position mod 6", () => {
  const real = ["ncds", "bcs70", "next_steps", "mcs"];
  assert.deepEqual(
    real.map((k) => colourSlot(k, real)),
    [1, 2, 3, 4],
  );
  assert.equal(colourSlot("bcs70", ["bcs70"]), 2, "pinned whatever the catalogue");
  assert.equal(colourSlot("x", keys), 3);
  assert.equal(colourSlot("mini", keys), 1);
  const many = ["a", "b", "c", "d", "e", "f", "g"];
  assert.equal(colourSlot("g", many), 1);
  assert.equal(colourSlot("nope", keys), 1);
});
