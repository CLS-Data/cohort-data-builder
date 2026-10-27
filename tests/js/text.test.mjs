import assert from "node:assert/strict";
import { test } from "node:test";
import { capitalise, esc, highlight, levelName } from "../../site/js/core/text.js";

test("esc escapes the five HTML-special characters", () => {
  assert.equal(
    esc(`<a href="x">Tom & Jerry's</a>`),
    "&lt;a href=&quot;x&quot;&gt;Tom &amp; Jerry&#39;s&lt;/a&gt;",
  );
});

test("esc treats null and undefined as empty", () => {
  assert.equal(esc(null), "");
  assert.equal(esc(undefined), "");
  assert.equal(esc(42), "42");
});

test("highlight marks the first case-insensitive match and escapes the rest", () => {
  assert.equal(
    highlight("Smoking <now> smoking", "SMOK"),
    "<mark>Smok</mark>ing &lt;now&gt; smoking",
  );
});

test("highlight escapes the matched text itself", () => {
  assert.equal(highlight("a<b", "<"), "a<mark>&lt;</mark>b");
});

test("highlight returns escaped text when the term is empty or absent", () => {
  assert.equal(highlight("a & b", ""), "a &amp; b");
  assert.equal(highlight("a & b", "zzz"), "a &amp; b");
  assert.equal(highlight(null, "a"), "");
});

test("capitalise upper-cases the first character only", () => {
  assert.equal(capitalise("sweep one"), "Sweep one");
  assert.equal(capitalise(""), "");
});

test("levelName sentence-cases a level and names -1 Unrecorded", () => {
  const levels = ["NOMINAL", "ORDINAL", "SCALE"];
  assert.equal(levelName(levels, 0), "Nominal");
  assert.equal(levelName(levels, 2), "Scale");
  assert.equal(levelName(levels, -1), "Unrecorded");
});
