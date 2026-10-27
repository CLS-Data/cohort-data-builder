/* Reading and writing browser storage without ever throwing.

   Storage can be missing or throw (private browsing, full quota, blocked site data); the
   site then simply forgets between visits. The storage object is passed in so this runs
   under Node in tests. */

/**
 * The storage key for a setting. Selections only make sense against the cohort they were
 * made in, so keys are namespaced by cohort; site-wide settings use `_site`.
 * @param {string} name The setting, e.g. "selection" or "theme".
 * @param {string} [cohortKey] The cohort key; omit for a site-wide setting.
 * @returns {string} `cohort-data-builder:<cohortKey>:<name>`.
 */
export const storeKey = (name, cohortKey = "_site") => `cohort-data-builder:${cohortKey}:${name}`;

/**
 * Read a JSON value.
 * @param {Storage|undefined} storage Usually `localStorage`.
 * @param {string} key The key, from {@link storeKey}.
 * @param {*} fallback Returned when the key is missing, unreadable or not JSON.
 * @returns {*} The stored value or `fallback`.
 */
export function read(storage, key, fallback) {
  try {
    const raw = storage.getItem(key);
    return raw === null ? fallback : JSON.parse(raw);
  } catch {
    return fallback;
  }
}

/**
 * Write a value as JSON.
 * @param {Storage|undefined} storage Usually `localStorage`.
 * @param {string} key The key, from {@link storeKey}.
 * @param {*} value Any JSON-serialisable value.
 * @returns {boolean} True if it was stored.
 */
export function write(storage, key, value) {
  try {
    storage.setItem(key, JSON.stringify(value));
    return true;
  } catch {
    return false;
  }
}
