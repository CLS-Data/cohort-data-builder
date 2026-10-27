import assert from "node:assert/strict";
import { test } from "node:test";
import { fixDots, problems } from "../../site/js/core/columns.js";

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
