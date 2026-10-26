import assert from "node:assert/strict";
import { test } from "node:test";
import { read, storeKey, write } from "../../site/js/core/storage.js";
import { fakeStorage } from "./helpers.mjs";

test("storeKey namespaces by cohort", () => {
  assert.equal(storeKey("selection", "bcs70"), "cohort-data-builder:bcs70:selection");
});

test("storeKey uses _site for site-wide settings", () => {
  assert.equal(storeKey("theme"), "cohort-data-builder:_site:theme");
});

test("write then read round-trips JSON", () => {
  const s = fakeStorage();
  assert.equal(write(s, "k", { a: [1, 2] }), true);
  assert.deepEqual(read(s, "k", null), { a: [1, 2] });
});

test("read returns the fallback for a missing key", () => {
  assert.equal(read(fakeStorage(), "nope", "dflt"), "dflt");
});

test("read returns the fallback for invalid JSON", () => {
  const s = fakeStorage();
  s.setItem("k", "{not json");
  assert.deepEqual(read(s, "k", []), []);
});

test("read returns the fallback when storage throws", () => {
  assert.equal(read(fakeStorage({ throws: true }), "k", 7), 7);
});

test("write returns false and does not throw when storage throws", () => {
  assert.equal(write(fakeStorage({ throws: true }), "k", 1), false);
});

test("read and write tolerate no storage at all", () => {
  assert.equal(read(undefined, "k", 3), 3);
  assert.equal(write(undefined, "k", 3), false);
});
