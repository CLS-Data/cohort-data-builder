import assert from "node:assert/strict";
import { before, test } from "node:test";
import {
  CONFIDENCES,
  DEFAULT_CONF,
  ensure,
  flatten,
  passes,
  rowDomains,
  rowTopics,
  shade,
  tally,
  toggle,
  validConf,
} from "../../site/js/core/topics.js";
import { readFixture } from "./helpers.mjs";

let vars;
let manifest;
let topics;
const byName = (name) => vars.find((r) => r[0] === name);

before(async () => {
  vars = await readFixture("mini/index.json");
  manifest = await readFixture("mini/manifest.json");
  topics = flatten(manifest.topics);
});

test("flatten lists every topic with its domain index", () => {
  assert.deepEqual(
    topics.map((t) => [t.id, t.domain]),
    [
      ["smoking", 0],
      ["alcohol", 0],
      ["tenure", 1],
    ],
  );
  assert.equal(topics[0].label, "Smoking");
  assert.deepEqual(flatten(undefined), []);
});

test("rowTopics keeps tags at or above the threshold, strongest first", () => {
  assert.deepEqual(rowTopics(byName("smoke5"), 50), [
    [0, 95],
    [1, 55],
  ]);
  assert.deepEqual(rowTopics(byName("smoke5"), 70), [[0, 95]]);
  assert.deepEqual(rowTopics(byName("alc10"), 30), [[1, 30]]);
  assert.deepEqual(rowTopics(byName("alc10"), 50), []);
  assert.deepEqual(rowTopics(byName("sex"), 30), []);
  assert.deepEqual(rowTopics(["x", "", 0, 0, 0, [2, 40, 0, 80]], 30), [
    [0, 80],
    [2, 40],
  ]);
});

test("rowDomains gives the domains of a row's topics", () => {
  assert.deepEqual([...rowDomains([0, 1], topics)], [0]);
  assert.deepEqual([...rowDomains([2, 0], topics)].sort(), [0, 1]);
});

test("toggle adds and removes an item without changing the original", () => {
  const sel = [];
  const one = toggle(sel, "t", 0, topics);
  assert.deepEqual(one, [{ kind: "t", i: 0 }]);
  assert.deepEqual(sel, []);
  assert.deepEqual(toggle(one, "t", 0, topics), []);
});

test("selecting a topic replaces its selected domain, and a domain replaces its topics", () => {
  const withDomain = toggle([{ kind: "t", i: 2 }], "d", 0, topics);
  assert.deepEqual(toggle(withDomain, "t", 1, topics), [
    { kind: "t", i: 2 },
    { kind: "t", i: 1 },
  ]);
  const withTopics = [
    { kind: "t", i: 0 },
    { kind: "t", i: 1 },
    { kind: "t", i: 2 },
  ];
  assert.deepEqual(toggle(withTopics, "d", 0, topics), [
    { kind: "t", i: 2 },
    { kind: "d", i: 0 },
  ]);
});

test("ensure selects but never deselects", () => {
  const sel = [{ kind: "t", i: 0 }];
  assert.equal(ensure(sel, "t", 0, topics), sel);
  assert.deepEqual(ensure(sel, "t", 2, topics), [
    { kind: "t", i: 0 },
    { kind: "t", i: 2 },
  ]);
});

test("passes: nothing selected passes all, any needs one, all needs every item", () => {
  const ds = new Set([0]);
  assert.equal(passes([], "all", [], new Set()), true);
  const sel = [
    { kind: "t", i: 0 },
    { kind: "t", i: 2 },
  ];
  assert.equal(passes(sel, "any", [0], ds), true);
  assert.equal(passes(sel, "all", [0], ds), false);
  assert.equal(passes(sel, "all", [0, 2], new Set([0, 1])), true);
  assert.equal(passes(sel, "any", [1], ds), false);
  assert.equal(passes([{ kind: "d", i: 0 }], "any", [1], ds), true);
  assert.equal(passes([{ kind: "d", i: 1 }], "any", [1], ds), false);
});

test("tally counts rows per sweep for each topic and each domain", () => {
  const t = tally(vars, manifest, 50);
  assert.deepEqual(
    t.topics.map((r) => [...r]),
    [
      [1, 0, 0],
      [1, 0, 0],
      [1, 1, 0],
    ],
  );
  assert.deepEqual(
    t.domains.map((r) => [...r]),
    [
      [1, 0, 0],
      [1, 1, 0],
    ],
  );
  const low = tally(vars, manifest, 30);
  assert.deepEqual([...low.topics[1]], [1, 1, 0]);
  assert.deepEqual([...low.domains[0]], [1, 1, 0]);
});

test("shade: 0 for nothing, else 1 to 4, by row or on a log scale overall", () => {
  assert.equal(shade(0, 10, 100, "row"), 0);
  assert.equal(shade(10, 10, 100, "row"), 4);
  assert.equal(shade(5, 10, 100, "row"), 2);
  assert.equal(shade(1, 1000, 1000, "row"), 1);
  assert.equal(shade(100, 100, 100, "abs"), 4);
  assert.equal(shade(1, 100, 10000, "abs"), 1);
  const mid = shade(100, 100, 10000, "abs");
  assert.ok(mid > 1 && mid < 4, String(mid));
});

test("confidence thresholds are 30, 50, 70 or 90, defaulting to 50", () => {
  assert.deepEqual(CONFIDENCES, [30, 50, 70, 90]);
  assert.equal(DEFAULT_CONF, 50);
  assert.equal(validConf(70), 70);
  assert.equal(validConf(60), 50);
  assert.equal(validConf("90"), 50);
  assert.equal(validConf(undefined), 50);
});
