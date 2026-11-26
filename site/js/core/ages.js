/* Sweep ages and the shared age axis of the overview (feature 007). No DOM and no shared
   state.

   With several cohorts the overview lines their sweeps up by age. The axis is ordinal, not
   to scale: one equal-width column per distinct age across the cohorts, so that the same
   age is in the same column, near ages sit side by side without overlapping, and early
   childhood (sweeps months apart) is not crushed against adulthood (years apart). A cohort
   with several sweeps at one age (sub-sweeps) has them in adjacent columns of that age, in
   list order; an age has as many columns as any cohort needs. Sweeps whose age is not known
   go in "?" columns at the end. With one cohort the columns are just its sweeps, in list
   order, which is the overview as it was before. */

const AGE_KEY = /^(\d+(?:\.\d+)?)([ym])$/;

/* Ages are compared after rounding, so 0.75 (an explicit age) and "9m" (a key) agree. */
const same = (age) => Math.round(age * 1000) / 1000;

/**
 * A sweep's age in years: its `age`, else from a key like `14y` or `9m`, else null.
 * @param {{key: string, age?: number}} wave One entry of `manifest.wave.list`.
 * @returns {number|null} The age, or null when it is not known.
 */
export function sweepAge(wave) {
  if (typeof wave.age === "number" && Number.isFinite(wave.age)) return wave.age;
  const m = AGE_KEY.exec(String(wave.key ?? ""));
  if (!m) return null;
  const n = Number(m[1]);
  return m[2] === "y" ? n : n / 12;
}

/**
 * How an age is written on the axis.
 * @param {number|null} age In years.
 * @returns {string} Months under one year ("9m"), whole years plainly ("11"), else one
 *   decimal ("2.5"); "?" when the age is not known.
 */
export function ageLabel(age) {
  if (age === null || age === undefined) return "?";
  if (age > 0 && age < 1) return `${Math.round(age * 12)}m`;
  return Number.isInteger(age) ? String(age) : age.toFixed(1);
}

/**
 * The columns of the overview for the chosen cohorts.
 * @param {{key: string, wave: {list: object[]}}[]} manifests The chosen cohorts' manifests,
 *   in catalogue order.
 * @returns {{single: boolean, columns: {age: number|null, label: string}[],
 *   slots: Map<string, (number|null)[]>}} The columns, left to right; `slots` gives, per
 *   cohort key, the sweep index in each column (null where it has none). With one cohort,
 *   `single` is true and the columns are its sweeps, labelled by sweep key.
 */
export function ageAxis(manifests) {
  if (manifests.length === 1) {
    const m = manifests[0];
    const list = m.wave.list;
    return {
      single: true,
      columns: list.map((w) => ({ age: sweepAge(w), label: w.key })),
      slots: new Map([[m.key, list.map((_, i) => i)]]),
    };
  }
  // How many columns each age needs: the most sweeps any one cohort has at it.
  const width = new Map(); // rounded age (null: not known) -> columns
  for (const m of manifests) {
    const here = new Map();
    for (const w of m.wave.list) {
      const age = sweepAge(w);
      const k = age === null ? null : same(age);
      here.set(k, (here.get(k) || 0) + 1);
    }
    for (const [k, n] of here) width.set(k, Math.max(width.get(k) || 0, n));
  }
  const ages = [...width.keys()].filter((k) => k !== null).sort((a, b) => a - b);
  const columns = [];
  const first = new Map(); // rounded age -> its first column
  for (const k of [...ages, null]) {
    if (!width.has(k)) continue;
    first.set(k, columns.length);
    for (let n = 0; n < width.get(k); n++) columns.push({ age: k, label: ageLabel(k) });
  }
  const slots = new Map();
  for (const m of manifests) {
    const row = columns.map(() => null);
    const used = new Map(); // rounded age -> columns of it taken so far
    m.wave.list.forEach((w, i) => {
      const age = sweepAge(w);
      const k = age === null ? null : same(age);
      const nth = used.get(k) || 0;
      used.set(k, nth + 1);
      row[first.get(k) + nth] = i;
    });
    slots.set(m.key, row);
  }
  return { single: false, columns, slots };
}

/**
 * A cohort's sweep index in each column of an axis.
 * @param {{slots: Map<string, (number|null)[]>, columns: object[]}} axis From
 *   {@link ageAxis}.
 * @param {{key: string}} manifest One of the cohorts the axis was built from.
 * @returns {(number|null)[]} One entry per column; null where the cohort has no sweep.
 */
export const cells = (axis, manifest) =>
  axis.slots.get(manifest.key) ?? axis.columns.map(() => null);
