/* Loading the supplied data files (contracts/site-data.md).

   `fetch` is passed in so this runs under Node in tests. Every URL is relative, so the site
   works from any path, including a GitHub Pages project URL. */

async function getJson(fetch, url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Could not load ${url} (HTTP ${res.status})`);
  return res.json();
}

/**
 * Load the list of cohorts on the site.
 * @param {typeof fetch} fetch A fetch-compatible function.
 * @returns {Promise<object[]>} `datasets` from data/datasets.json.
 * @throws {Error} Naming the URL and HTTP status when the file cannot be loaded.
 */
export async function loadCatalogue(fetch) {
  return (await getJson(fetch, "data/datasets.json")).datasets;
}

/**
 * Load one cohort's manifest and variable index.
 * @param {typeof fetch} fetch A fetch-compatible function.
 * @param {string} key The cohort key, e.g. "bcs70".
 * @returns {Promise<{manifest: object, vars: Array[]}>} The manifest and the index rows.
 * @throws {Error} Naming the URL and HTTP status when a file cannot be loaded.
 */
export async function loadCohort(fetch, key) {
  const [manifest, vars] = await Promise.all([
    getJson(fetch, `data/${key}/manifest.json`),
    getJson(fetch, `data/${key}/index.json`),
  ]);
  return { manifest, vars };
}

/**
 * Load one file's dictionary, at most once per cache.
 * @param {typeof fetch} fetch A fetch-compatible function.
 * @param {string} key The cohort key.
 * @param {string} file The data file name from the manifest.
 * @param {Map<string, object>} cache Dictionaries already loaded, keyed `<key>/<file>`.
 * @returns {Promise<object>} The dictionary.
 * @throws {Error} Naming the URL and HTTP status when the file cannot be loaded.
 */
export async function loadDict(fetch, key, file, cache) {
  const id = `${key}/${file}`;
  if (!cache.has(id)) {
    cache.set(id, await getJson(fetch, `data/${key}/dict/${encodeURIComponent(file)}.json`));
  }
  return cache.get(id);
}
