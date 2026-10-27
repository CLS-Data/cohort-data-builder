import assert from "node:assert/strict";
import { test } from "node:test";
import { loadCatalogue, loadCohort, loadDict } from "../../site/js/core/data.js";
import { fixtureFetch, readFixture } from "./helpers.mjs";

test("loadCatalogue returns the datasets list", async () => {
  const datasets = await loadCatalogue(fixtureFetch());
  assert.deepEqual(datasets, (await readFixture("datasets.json")).datasets);
});

test("loadCohort returns the manifest and index rows", async () => {
  const { manifest, vars } = await loadCohort(fixtureFetch(), "mini");
  assert.equal(manifest.key, "mini");
  assert.deepEqual(vars, await readFixture("mini/index.json"));
});

test("loadDict fetches a dictionary once and then serves it from the cache", async () => {
  const fetch = fixtureFetch();
  const cache = new Map();
  const first = await loadDict(fetch, "mini", "mini_age5", cache);
  const second = await loadDict(fetch, "mini", "mini_age5", cache);
  assert.equal(first.file, "mini_age5");
  assert.equal(second, first);
  assert.equal(fetch.calls.filter((u) => u.includes("mini_age5")).length, 1);
});

test("every URL requested is relative", async () => {
  const fetch = fixtureFetch();
  await loadCatalogue(fetch);
  await loadCohort(fetch, "mini");
  await loadDict(fetch, "mini", "mini_age10", new Map());
  assert.deepEqual(fetch.calls.sort(), [
    "data/datasets.json",
    "data/mini/dict/mini_age10.json",
    "data/mini/index.json",
    "data/mini/manifest.json",
  ]);
});

test("a failed load throws with the URL and HTTP status", async () => {
  const fetch = fixtureFetch();
  await assert.rejects(loadCohort(fetch, "absent"), /data\/absent\/\w+\.json.*404/);
  await assert.rejects(
    loadDict(fetch, "mini", "nope", new Map()),
    /data\/mini\/dict\/nope\.json.*404/,
  );
  await assert.rejects(
    loadCatalogue(fixtureFetch(new URL("file:///nonexistent/"))),
    /data\/datasets\.json.*404/,
  );
});
