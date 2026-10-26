/* Shared test helpers: fixture data, a fake fetch and a fake localStorage. */

import { readFile } from "node:fs/promises";

const FIXTURES = new URL("../fixtures/data/", import.meta.url);

/**
 * Read a JSON file from tests/fixtures/data/.
 * @param {string} path Path inside the fixture data folder, e.g. "mini/manifest.json".
 * @returns {Promise<any>} The parsed JSON.
 */
export async function readFixture(path) {
  return JSON.parse(await readFile(new URL(path, FIXTURES), "utf8"));
}

/**
 * Build a fetch-compatible function that serves files from a folder, as the site's
 * web server would. URLs are taken relative to the folder; a missing file answers
 * `{ok: false, status: 404}`. Every requested URL is recorded in `fetch.calls`.
 * @param {URL} [root] Folder standing in for the site root; defaults to one whose
 *   `data/` is the fixture data.
 * @returns {((url: string) => Promise<{ok: boolean, status: number, json: () => Promise<any>,
 *   text: () => Promise<string>}>) & {calls: string[]}} The fake fetch.
 */
export function fixtureFetch(root = new URL("../fixtures/", import.meta.url)) {
  const fake = async (url) => {
    fake.calls.push(url);
    let body;
    try {
      body = await readFile(new URL(url, root), "utf8");
    } catch {
      return { ok: false, status: 404, json: async () => null, text: async () => "" };
    }
    return { ok: true, status: 200, json: async () => JSON.parse(body), text: async () => body };
  };
  fake.calls = [];
  return fake;
}

/**
 * An in-memory stand-in for `localStorage`.
 * @param {{throws?: boolean}} [options] With `throws: true`, every method throws, as
 *   storage does in some private-browsing modes.
 * @returns {{getItem: (k: string) => string|null, setItem: (k: string, v: string) => void,
 *   removeItem: (k: string) => void, clear: () => void, readonly length: number}}
 */
export function fakeStorage({ throws = false } = {}) {
  const items = new Map();
  const guard = () => {
    if (throws) throw new Error("storage unavailable");
  };
  return {
    getItem(k) {
      guard();
      return items.has(k) ? items.get(k) : null;
    },
    setItem(k, v) {
      guard();
      items.set(k, String(v));
    },
    removeItem(k) {
      guard();
      items.delete(k);
    },
    clear() {
      guard();
      items.clear();
    },
    get length() {
      guard();
      return items.size;
    },
  };
}
