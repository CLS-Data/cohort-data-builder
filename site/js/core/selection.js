/* The selection as plain data: what can be picked, adding and removing, output column
   names, and restoring a saved selection. No DOM and no shared state.

   A selection is an array of {name, label, file, wave, column}, in the order picked.
   Functions never change the array they are given; they return a new one with how many
   entries changed. */

const SELECT_ALL_MAX = 500; // beyond this "select all" is a mistake, not a shortcut

/* The intersection of a valid R name, a Python-friendly column and a CSV header that
   survives any tool. */
const NAME_OK = /^[A-Za-z][A-Za-z0-9_.]*$/;

/**
 * The key a selection entry is known by.
 * @param {{file: string, name: string}} item A selection entry or item.
 * @returns {string} `<file>:<name>`.
 */
export const keyOf = (item) => `${item.file}:${item.name}`;

/**
 * The key an index row is known by in the result list.
 * @param {Array} row An index row.
 * @returns {string} `<fileIndex>:<name>`.
 */
export const rowKey = (row) => `${row[2]}:${row[0]}`;

const isIdentifier = (name, identifier) =>
  String(name).toLowerCase() === String(identifier).toLowerCase();

/**
 * Why a variable cannot be selected.
 * @param {Array} row The variable's index row.
 * @param {{name: string, hasId: boolean}} file Its manifest file.
 * @param {string} identifier The cohort's person identifier.
 * @returns {string} The reason, or "" when it can be selected.
 */
export function canSelect(row, file, identifier) {
  if (isIdentifier(row[0], identifier)) {
    return `${row[0]} is already in every download: it is what the files are merged on.`;
  }
  if (!file.hasId) return `${file.name} has no ${identifier} column, so it cannot be merged.`;
  return "";
}

/**
 * The selection item for an index row.
 * @param {Array} row An index row.
 * @param {object} manifest The cohort manifest.
 * @returns {{name: string, label: string, file: string, wave: string}} The item.
 */
export function toItem(row, manifest) {
  return {
    name: row[0],
    label: row[1] || "",
    file: manifest.files[row[2]].name,
    wave: manifest.wave.list[row[3]].key,
  };
}

/* Membership is asked once per row drawn, so it is a Set lookup. Selections are never
   changed in place, so one Set per array stays right. */
const keySets = new WeakMap();

/**
 * Whether a variable is in the selection.
 * @param {object[]} selection The selection.
 * @param {string} file The file name.
 * @param {string} name The variable name.
 * @returns {boolean} True if selected.
 */
export function has(selection, file, name) {
  if (!keySets.has(selection)) keySets.set(selection, new Set(selection.map(keyOf)));
  return keySets.get(selection).has(`${file}:${name}`);
}

/**
 * Make a string a safe column name: anything outside `[A-Za-z0-9_.]` becomes `_`, and
 * leading characters that are not letters are dropped.
 * @param {string} s The proposed name.
 * @returns {string} The safe name (possibly empty).
 */
export const sanitiseColumn = (s) =>
  String(s || "")
    .replace(/[^A-Za-z0-9_.]/g, "_")
    .replace(/^[^A-Za-z]+/, "");

/* Every output column already claimed, lower-cased: columns differing only by case clash
   in Stata, SPSS and most people's heads. The identifier is column one of every output. */
function taken(selection, identifier) {
  const out = new Set([String(identifier).toLowerCase()]);
  for (const b of selection) out.add(b.column.toLowerCase());
  return out;
}

/* The variable's own name, qualified by sweep only if that would clash. */
function defaultColumn(name, wave, claimed) {
  const base = sanitiseColumn(name) || "var";
  if (!claimed.has(base.toLowerCase())) return base;
  const qualified = sanitiseColumn(`${base}_${wave}`);
  if (!claimed.has(qualified.toLowerCase())) return qualified;
  for (let n = 2; ; n++) {
    const candidate = `${qualified}_${n}`;
    if (!claimed.has(candidate.toLowerCase())) return candidate;
  }
}

/* Add items to a copy of the selection; returns the copy, the count and the last refusal. */
function put(selection, items, manifest) {
  const next = [...selection];
  const keys = new Set(selection.map(keyOf));
  const claimed = taken(selection, manifest.identifier);
  let changed = 0;
  let reason = "";
  for (const it of items) {
    if (!it?.name || !it.file || keys.has(keyOf(it))) continue;
    const file = manifest.files.find((f) => f.name === it.file);
    if (!file) {
      reason = `${it.file} is not in this cohort.`;
      continue;
    }
    const why = canSelect([it.name], file, manifest.identifier);
    if (why) {
      reason = why;
      continue;
    }
    const wave = it.wave || file.wave;
    const column = defaultColumn(it.name, wave, claimed);
    claimed.add(column.toLowerCase());
    keys.add(keyOf(it));
    next.push({ name: it.name, label: it.label || "", file: it.file, wave, column });
    changed++;
  }
  return { selection: changed ? next : selection, changed, reason };
}

/**
 * Add one variable.
 * @param {object[]} selection The selection.
 * @param {{name: string, label?: string, file: string, wave?: string}} item What to add.
 * @param {object} manifest The cohort manifest.
 * @returns {{selection: object[], changed: number, reason: string}} The new selection
 *   (the same array when nothing changed), 1 or 0, and why it was refused ("" if it was
 *   not, including when it was already selected).
 */
export const add = (selection, item, manifest) => put(selection, [item], manifest);

/**
 * Add many variables at once (a range or a whole result list).
 * @param {object[]} selection The selection.
 * @param {object[]} items What to add; unselectable ones are skipped.
 * @param {object} manifest The cohort manifest.
 * @returns {{selection: object[], changed: number, reason: string}} As {@link add}.
 */
export const addMany = (selection, items, manifest) => put(selection, items, manifest);

/**
 * Remove variables.
 * @param {object[]} selection The selection.
 * @param {{file: string, name: string}[]} items What to remove.
 * @returns {{selection: object[], changed: number}} The new selection and how many went.
 */
export function removeMany(selection, items) {
  const keys = new Set(items.map(keyOf));
  const next = selection.filter((b) => !keys.has(keyOf(b)));
  const changed = selection.length - next.length;
  return { selection: changed ? next : selection, changed };
}

/**
 * Remove one variable by key.
 * @param {object[]} selection The selection.
 * @param {string} key `<file>:<name>`.
 * @returns {{selection: object[], changed: number}} As {@link removeMany}.
 */
export function remove(selection, key) {
  const next = selection.filter((b) => keyOf(b) !== key);
  const changed = selection.length - next.length;
  return { selection: changed ? next : selection, changed };
}

/**
 * Add a variable if it is not selected, otherwise remove it.
 * @param {object[]} selection The selection.
 * @param {object} item The variable.
 * @param {object} manifest The cohort manifest.
 * @returns {{selection: object[], changed: number, reason?: string}} As {@link add}.
 */
export function toggle(selection, item, manifest) {
  return has(selection, item.file, item.name)
    ? remove(selection, keyOf(item))
    : add(selection, item, manifest);
}

const selectable = (rows, manifest) =>
  rows.filter((r) => !canSelect(r, manifest.files[r[2]], manifest.identifier));

/**
 * The selectable variables between two rows of the result list, both included. The caller
 * adds or removes them according to the clicked row's state.
 * @param {Array[]} matches The result rows, in list order.
 * @param {string} anchorKey The row clicked before ({@link rowKey}).
 * @param {string} toKey The row clicked now.
 * @param {object} manifest The cohort manifest.
 * @returns {object[]} Selection items; empty if either row is not in the list.
 */
export function rangeBetween(matches, anchorKey, toKey, manifest) {
  const from = matches.findIndex((r) => rowKey(r) === anchorKey);
  const to = matches.findIndex((r) => rowKey(r) === toKey);
  if (from < 0 || to < 0) return [];
  const rows = matches.slice(Math.min(from, to), Math.max(from, to) + 1);
  return selectable(rows, manifest).map((r) => toItem(r, manifest));
}

/**
 * The selectable variables among the results, as selection items.
 * @param {Array[]} matches The result rows.
 * @param {object} manifest The cohort manifest.
 * @returns {object[]} Selection items.
 */
export const selectableItems = (matches, manifest) =>
  selectable(matches, manifest).map((r) => toItem(r, manifest));

/**
 * What the "Select all" button should offer.
 * @param {Array[]} matches The result rows.
 * @param {object} manifest The cohort manifest.
 * @param {object[]} selection The selection.
 * @returns {"hidden"|"add"|"remove"} Hidden for no selectable rows or more than 500;
 *   "remove" when every selectable row is already selected.
 */
export function selectAllState(matches, manifest, selection) {
  const rows = selectable(matches, manifest);
  if (!rows.length || rows.length > SELECT_ALL_MAX) return "hidden";
  const allIn = rows.every((r) => has(selection, manifest.files[r[2]].name, r[0]));
  return allIn ? "remove" : "add";
}

/**
 * Rebuild a saved selection against the current data. Entries whose variable no longer
 * exists, and the identifier, are dropped; a saved column is kept only if it is a valid
 * name not already claimed (ignoring case), otherwise a default is assigned.
 * @param {unknown} saved What was stored; anything that is not an array gives [].
 * @param {Array[]} vars The cohort's index rows.
 * @param {object} manifest The cohort manifest.
 * @returns {object[]} The selection.
 */
export function restore(saved, vars, manifest) {
  if (!Array.isArray(saved)) return [];
  const exists = new Set(vars.map((r) => `${manifest.files[r[2]].name}:${r[0]}`));
  const claimed = new Set([String(manifest.identifier).toLowerCase()]);
  const out = [];
  for (const b of saved) {
    if (!b || typeof b !== "object" || !exists.has(keyOf(b))) continue;
    if (isIdentifier(b.name, manifest.identifier)) continue;
    const column =
      typeof b.column === "string" && NAME_OK.test(b.column) && !claimed.has(b.column.toLowerCase())
        ? b.column
        : defaultColumn(b.name, b.wave, claimed);
    claimed.add(column.toLowerCase());
    out.push({ name: b.name, label: b.label || "", file: b.file, wave: b.wave, column });
  }
  return out;
}
