import assert from "node:assert/strict";
import { test } from "node:test";
import { fixDots, problems, problemsByCohort } from "../../site/js/core/columns.js";

const col = (name, column, file = "f") => ({ name, label: "", file, wave: "5y", column });

test("valid, distinct columns have no problems in any format", () => {
  const s = [col("a", "alpha"), col("b", "beta_2")];
  for (const format of ["csv", "dta", "sav"]) assert.equal(problems(s, "PID", format).size, 0);
});

test("an invalid name is flagged", () => {
  for (const bad of ["1abc", "_abc", "a b", "", "é"]) {
    const p = problems([col("a", bad)], "PID", "csv");
    assert.equal(p.get("f:a"), "Must start with a letter and use only letters, digits, _ or .");
  }
});

test("two columns equal ignoring case are both flagged", () => {
  const p = problems([col("a", "Sex"), col("b", "sex", "g")], "PID", "csv");
  assert.equal(p.get("f:a"), "Two columns would both be called sex.");
  assert.equal(p.get("g:b"), "Two columns would both be called sex.");
});

test("a column named like the identifier is flagged", () => {
  const p = problems([col("a", "pid")], "PID", "csv");
  assert.match(p.get("f:a"), /the identifier's name/);
});

test("Stata allows letters, digits and _ only, up to 32 characters", () => {
  assert.match(problems([col("a", "a.b")], "PID", "dta").get("f:a"), /a_b/);
  assert.equal(problems([col("a", "a".repeat(32))], "PID", "dta").size, 0);
  assert.match(problems([col("a", "a".repeat(33))], "PID", "dta").get("f:a"), /32/);
  assert.equal(problems([col("a", "a.b")], "PID", "csv").size, 0);
});

test("SPSS allows up to 64 characters, not ending with a dot", () => {
  assert.equal(problems([col("a", "a".repeat(64))], "PID", "sav").size, 0);
  assert.match(problems([col("a", "a".repeat(65))], "PID", "sav").get("f:a"), /64/);
  assert.match(problems([col("a", "ab.")], "PID", "sav").get("f:a"), /dot/);
});

test("fixDots replaces non-word characters and keeps names distinct", () => {
  const fixed = fixDots([col("a", "x.y"), col("b", "x_y"), col("c", "pid"), col("d", "z")], "PID");
  assert.deepEqual(
    fixed.map((b) => b.column),
    ["x_y", "x_y_2", "pid_2", "z"],
  );
});

test("choosing Stata code applies Stata's name rules whatever the output format", () => {
  assert.match(problems([col("a", "a.b")], "PID", "csv", ["stata"]).get("f:a"), /a_b/);
  assert.match(problems([col("a", "a".repeat(33))], "PID", "sav", ["r", "stata"]).get("f:a"), /32/);
  assert.equal(problems([col("a", "a.b")], "PID", "csv", ["r", "python"]).size, 0);
});

test("an empty selection has no problems", () => {
  assert.equal(problems([], "PID", "csv").size, 0);
  assert.equal(problems([], "PID", "dta", ["stata"]).size, 0);
});

/* ── Per cohort (feature 007): each cohort's download is checked on its own ── */

const inCohort = (cohort, name, column, file = "f") => ({ ...col(name, column, file), cohort });
const manifests = new Map([
  ["mini", { key: "mini", identifier: "PID" }],
  ["mini2", { key: "mini2", identifier: "CID" }],
]);

test("problemsByCohort: the same column in two cohorts is no clash", () => {
  const bundles = new Map([
    ["mini", [inCohort("mini", "a", "sex2")]],
    ["mini2", [inCohort("mini2", "b", "sex2")]],
  ]);
  assert.equal(problemsByCohort(bundles, manifests, "csv").size, 0);
});

test("problemsByCohort: the same column twice in one cohort still clashes, keyed by cohort", () => {
  const bundles = new Map([
    ["mini", [inCohort("mini", "a", "x"), inCohort("mini", "b", "x")]],
    ["mini2", [inCohort("mini2", "c", "x")]],
  ]);
  const found = problemsByCohort(bundles, manifests, "csv");
  assert.deepEqual([...found.keys()].sort(), ["mini:f:a", "mini:f:b"]);
});

test("problemsByCohort: each cohort's identifier is checked against its own columns", () => {
  const bundles = new Map([
    ["mini2", [inCohort("mini2", "a", "PID"), inCohort("mini2", "b", "CID")]],
  ]);
  const found = problemsByCohort(bundles, manifests, "csv");
  assert.deepEqual([...found.keys()], ["mini2:f:b"]);
  assert.match(found.get("mini2:f:b"), /identifier/);
});

test("problemsByCohort: equals problems() on each cohort's part", () => {
  const part = [inCohort("mini", "a", "bad name"), inCohort("mini", "b", "ok")];
  const own = problems(part, "PID", "dta", ["stata"]);
  const found = problemsByCohort(new Map([["mini", part]]), manifests, "dta", ["stata"]);
  assert.deepEqual(
    [...found].map(([k, v]) => [k, v]),
    [...own].map(([k, v]) => [`mini:${k}`, v]),
  );
});
