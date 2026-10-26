import assert from "node:assert/strict";
import { before, test } from "node:test";
import {
  add,
  addMany,
  canSelect,
  has,
  rangeBetween,
  remove,
  removeMany,
  restore,
  rowKey,
  sanitiseColumn,
  selectAllState,
  toggle,
  toItem,
} from "../../site/js/core/selection.js";
import { readFixture } from "./helpers.mjs";

let vars;
let manifest;
const byName = (name, file = 0) => vars.find((r) => r[0] === name && r[2] === file);
const item = (name, file = 0) => toItem(byName(name, file), manifest);

before(async () => {
  vars = await readFixture("mini/index.json");
  manifest = await readFixture("mini/manifest.json");
});

test("canSelect allows an ordinary variable", () => {
  assert.equal(canSelect(byName("smoke5"), manifest.files[0], "PID"), "");
});

test("canSelect refuses the identifier in any case", () => {
  assert.match(canSelect(byName("pid", 1), manifest.files[1], "PID"), /already in every download/);
});

test("canSelect refuses a file without the identifier, naming both", () => {
  const why = canSelect(byName("areacode", 3), manifest.files[3], "PID");
  assert.match(why, /mini_noid/);
  assert.match(why, /PID/);
});

test("toItem makes a selection entry from an index row", () => {
  assert.deepEqual(item("smoke5"), {
    name: "smoke5",
    label: "Does the mother smoke",
    file: "mini_age5",
    wave: "5y",
  });
});

test("add appends with a default column and ignores duplicates", () => {
  const one = add([], item("smoke5"), manifest);
  assert.equal(one.changed, 1);
  assert.deepEqual(one.selection, [{ ...item("smoke5"), column: "smoke5" }]);
  const again = add(one.selection, item("smoke5"), manifest);
  assert.equal(again.changed, 0);
  assert.equal(again.selection, one.selection);
});

test("add returns the refusal reason and leaves the selection alone", () => {
  const r = add([], item("areacode", 3), manifest);
  assert.equal(r.changed, 0);
  assert.deepEqual(r.selection, []);
  assert.match(r.reason, /mini_noid/);
});

test("remove, toggle, addMany and removeMany report how many changed", () => {
  const many = addMany(
    [],
    [item("sex"), item("smoke5"), item("PID"), item("areacode", 3)],
    manifest,
  );
  assert.equal(many.changed, 2);
  assert.ok(has(many.selection, "mini_age5", "sex"));
  const off = toggle(many.selection, item("sex"), manifest);
  assert.equal(off.changed, 1);
  assert.ok(!has(off.selection, "mini_age5", "sex"));
  const on = toggle(off.selection, item("sex"), manifest);
  assert.ok(has(on.selection, "mini_age5", "sex"));
  assert.equal(remove(on.selection, "mini_age5:sex").changed, 1);
  assert.equal(remove(on.selection, "mini_age5:nothing").changed, 0);
  const gone = removeMany(on.selection, [item("sex"), item("smoke5"), item("nolab5")]);
  assert.equal(gone.changed, 2);
  assert.deepEqual(gone.selection, []);
});

test("rangeBetween gives the selectable rows between two rows, inclusive, either way round", () => {
  const names = (items) => items.map((i) => i.name);
  const range = rangeBetween(vars, rowKey(byName("tenure5")), rowKey(byName("sex", 1)), manifest);
  assert.deepEqual(names(range), ["tenure5", "quote5", "nolab5", "sex"]);
  const back = rangeBetween(vars, rowKey(byName("sex", 1)), rowKey(byName("tenure5")), manifest);
  assert.deepEqual(names(back), names(range));
  assert.deepEqual(rangeBetween(vars, "nope", rowKey(byName("sex")), manifest), []);
});

test("selectAllState is hidden for none or over 500, else add or remove", () => {
  const ids = vars.filter((r) => r[0].toLowerCase() === "pid");
  assert.equal(selectAllState(ids, manifest, []), "hidden");
  const five = vars.filter((r) => r[3] === 0);
  assert.equal(selectAllState(five, manifest, []), "add");
  const all = addMany(
    [],
    five.map((r) => toItem(r, manifest)),
    manifest,
  ).selection;
  assert.equal(selectAllState(five, manifest, all), "remove");
  const big = Array.from({ length: 501 }, (_, i) => [`v${i}`, "", 0, 0, 0]);
  assert.equal(selectAllState(big, manifest, []), "hidden");
  assert.equal(selectAllState(big.slice(0, 500), manifest, []), "add");
});

test("sanitiseColumn keeps letters, digits, _ and . and starts with a letter", () => {
  assert.equal(sanitiseColumn("a b-c.d"), "a_b_c.d");
  assert.equal(sanitiseColumn("1_9x$"), "x_");
  assert.equal(sanitiseColumn("é"), "");
});

test("a clashing column gets the sweep, then a number", () => {
  let s = add([], item("sex"), manifest).selection;
  s = add(s, item("sex", 1), manifest).selection;
  assert.deepEqual(
    s.map((b) => b.column),
    ["sex", "sex_10y"],
  );
  s = add(s, { name: "SEX", label: "", file: "mini_grid", wave: "10y" }, manifest).selection;
  assert.equal(s[2].column, "SEX_10y_2");
});

test("the identifier's name counts as taken", () => {
  const s = add([], { name: "$PID", label: "", file: "mini_grid", wave: "10y" }, manifest).selection;
  assert.equal(s[0].column, "PID_10y");
});

test("restore drops vanished variables and the identifier and repairs columns", () => {
  const saved = [
    { ...item("sex"), column: "gender" },
    { ...item("sex", 1), column: "GENDER" },
    { name: "gone", label: "", file: "mini_age5", wave: "5y", column: "gone" },
    { ...item("PID"), column: "PID" },
    { ...item("smoke5"), column: "1bad" },
    null,
  ];
  assert.deepEqual(
    restore(saved, vars, manifest).map((b) => [b.name, b.column]),
    [
      ["sex", "gender"],
      ["sex", "sex"],
      ["smoke5", "smoke5"],
    ],
  );
});

test("restore tolerates garbage", () => {
  assert.deepEqual(restore("nonsense", vars, manifest), []);
  assert.deepEqual(restore(undefined, vars, manifest), []);
  assert.deepEqual(restore([42, "x", {}], vars, manifest), []);
});
