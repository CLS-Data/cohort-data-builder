/* The selection and options as the interface holds them: changing, saving and restoring,
   and telling the views that draw them. The selection itself is plain data, handled by
   core/selection.js. */

import { restore } from "../core/selection.js";
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

/**
 * Replace the selection, save it for this cohort and redraw what shows it.
 * @param {object[]} next The new selection; the current one means nothing changed.
 */
export function setSelection(next) {
  if (next === state.bundle) return;
  state.bundle = next;
  write(storage, storeKey("selection", state.manifest.key), next);
  notify();
}

/** Load this cohort's saved selection, dropping whatever no longer exists. */
export function restoreSelection() {
  const saved = read(storage, storeKey("selection", state.manifest.key), []);
  state.bundle = restore(saved, state.vars, state.manifest);
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
    const langs = saved.languages.filter((l) => l === "r" || l === "python");
    if (langs.length) o.languages = langs;
  }
  o.missingToNa = saved.missingToNa === true;
  o.minConf = validConf(saved.minConf);
  o.gridShade = saved.gridShade === "abs" ? "abs" : "row";
  if (["csv", "dta", "sav"].includes(saved.outputFormat)) o.outputFormat = saved.outputFormat;
  o.panelOpen = saved.panelOpen === true;
  o.panelGroup = saved.panelGroup === "file" ? "file" : "wave";
}
