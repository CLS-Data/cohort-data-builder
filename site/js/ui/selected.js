/* The selection and options as the interface holds them: changing, saving and restoring,
   and telling the views that draw them. The selection itself is plain data, handled by
   core/selection.js. */

import { cohortKeyOf, restore } from "../core/selection.js";
import { read, storeKey, write } from "../core/storage.js";
import { validConf } from "../core/topics.js";
import { state } from "./state.js";

/** Browser storage, or undefined when the browser blocks it (the site then forgets). */
export const storage = (() => {
  try {
    return window.localStorage;
  } catch {
    return undefined;
  }
})();

const listeners = [];

/**
 * Register something to redraw whenever the selection changes.
 * @param {() => void} fn Called after each change.
 */
export const onSelectionChange = (fn) => {
  listeners.push(fn);
};

const notify = () => {
  for (const fn of listeners) fn();
};

/* Saved without the cohort: each cohort's selection has its own storage key, as before. */
const forStorage = (selection) => selection.map(({ cohort: _, ...rest }) => rest);

/**
 * Replace one cohort's selection, save it and redraw what shows it.
 * @param {string} key The cohort.
 * @param {object[]} next Its new selection; its current one means nothing changed.
 */
export function setSelection(key, next) {
  const now = state.bundles.get(key) || [];
  if (next === now) return;
  if (next.length) state.bundles.set(key, next);
  else state.bundles.delete(key);
  write(storage, storeKey("selection", key), forStorage(next));
  notify();
}

/**
 * Remove variables from whichever cohorts' selections hold them.
 * @param {string[]} keys `<cohort>:<file>:<name>` of each ({@link cohortKeyOf}).
 * @returns {number} How many were removed.
 */
export function removeSelected(keys) {
  const gone = new Set(keys);
  let changed = 0;
  for (const [key, selection] of [...state.bundles]) {
    const next = selection.filter((b) => !gone.has(cohortKeyOf(b)));
    if (next.length !== selection.length) {
      changed += selection.length - next.length;
      setSelection(key, next);
    }
  }
  return changed;
}

/** Empty every cohort's selection. */
export function clearSelection() {
  for (const key of [...state.bundles.keys()]) setSelection(key, []);
}

/**
 * A cohort's saved selection, without checking it against the data.
 * @param {string} key The cohort.
 * @returns {unknown} What was stored ([] if nothing).
 */
export const savedSelection = (key) => read(storage, storeKey("selection", key), []);

/**
 * Load a cohort's saved selection, dropping whatever no longer exists. The cohort must
 * be loaded.
 * @param {string} key The cohort.
 */
export function restoreSelection(key) {
  const { vars, manifest } = state.cohorts.get(key);
  const restored = restore(savedSelection(key), vars, manifest);
  if (restored.length) state.bundles.set(key, restored);
  else state.bundles.delete(key);
  notify();
}

/** Save the interface options, once for the whole site. */
export const saveOptions = () => write(storage, storeKey("options"), state.options);

/** Restore the saved interface options, keeping only values that make sense. */
export function restoreOptions() {
  const saved = read(storage, storeKey("options"), null);
  if (!saved || typeof saved !== "object") return;
  const o = state.options;
  if (Array.isArray(saved.languages)) {
    const langs = saved.languages.filter((l) => ["r", "python", "stata"].includes(l));
    if (langs.length) o.languages = langs;
  }
  o.missingToNa = saved.missingToNa === true;
  o.minConf = validConf(saved.minConf);
  o.gridShade = saved.gridShade === "abs" ? "abs" : "row";
  if (["csv", "dta", "sav"].includes(saved.outputFormat)) o.outputFormat = saved.outputFormat;
  o.panelOpen = saved.panelOpen === true;
  o.panelGroup = saved.panelGroup === "file" ? "file" : "wave";
}
