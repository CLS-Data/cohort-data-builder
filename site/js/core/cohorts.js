/* Which cohorts are chosen, and each cohort's colour (feature 007, contracts/cohort-choice.md).
   No DOM and no shared state.

   A choice is a list of cohort keys, always in catalogue order and never empty while the
   site has cohorts. It is written to the page address as `#ncds+bcs70`. */

/* Known cohorts keep their colour whatever else is added to the catalogue. */
const PINNED = { ncds: 1, bcs70: 2, next_steps: 3, mcs: 4 };

/** How many cohort colours the stylesheet defines (`--coh-1` … `--coh-6`). */
export const COLOURS = 6;

/**
 * Keys in catalogue order, without unknown keys or repeats.
 * @param {string[]} chosen Keys in any order.
 * @param {string[]} keys The catalogue's keys, in order.
 * @returns {string[]} The known chosen keys, in catalogue order.
 */
const ordered = (chosen, keys) => keys.filter((k) => chosen.includes(k));

/**
 * Read a choice from the page address.
 * @param {string} hash `location.hash`, with or without the leading `#`.
 * @param {string[]} keys The catalogue's keys, in order.
 * @returns {string[]} The known keys it names, in catalogue order; empty if none.
 */
export function parseChoice(hash, keys) {
  let text = String(hash || "").replace(/^#/, "");
  try {
    text = decodeURIComponent(text);
  } catch {
    // A malformed escape: read it as it is.
  }
  return ordered(text.split("+"), keys);
}

/**
 * Write a choice for the page address (without the `#`).
 * @param {string[]} chosen The chosen keys.
 * @param {string[]} keys The catalogue's keys, in order.
 * @returns {string} The keys in catalogue order, joined by `+`.
 */
export const formatChoice = (chosen, keys) => ordered(chosen, keys).join("+");

/**
 * The cohorts to open when the page loads.
 * @param {{hash: string, stored: unknown, storedOld: unknown, keys: string[]}} from The
 *   address, the stored choice (`_site:cohorts`), the stored single cohort of earlier
 *   versions (`_site:cohort`) and the catalogue's keys.
 * @returns {string[]} The first of these that names a known cohort, else the first
 *   catalogue cohort; empty only when the catalogue is.
 */
export function chooseInitial({ hash, stored, storedOld, keys }) {
  const fromHash = parseChoice(hash, keys);
  if (fromHash.length) return fromHash;
  if (Array.isArray(stored)) {
    const fromStore = ordered(
      stored.filter((k) => typeof k === "string"),
      keys,
    );
    if (fromStore.length) return fromStore;
  }
  if (typeof storedOld === "string" && keys.includes(storedOld)) return [storedOld];
  return keys.slice(0, 1);
}

/**
 * Add a cohort to the choice, or remove it.
 * @param {string[]} chosen The current choice; not changed.
 * @param {string} key The cohort pressed.
 * @param {string[]} keys The catalogue's keys, in order.
 * @returns {string[]} The new choice, in catalogue order. The last chosen cohort is never
 *   removed, and an unknown key changes nothing.
 */
export function toggleChoice(chosen, key, keys) {
  if (!keys.includes(key)) return ordered(chosen, keys);
  if (!chosen.includes(key)) return ordered([...chosen, key], keys);
  const next = ordered(
    chosen.filter((k) => k !== key),
    keys,
  );
  return next.length ? next : ordered(chosen, keys);
}

/**
 * Which of the stylesheet's cohort colours a cohort uses.
 * @param {string} key The cohort key.
 * @param {string[]} keys The catalogue's keys, in order.
 * @returns {number} 1 to {@link COLOURS}: pinned for the known cohorts, else the cohort's
 *   catalogue position (mod {@link COLOURS}); 1 for a key not in the catalogue.
 */
export function colourSlot(key, keys) {
  if (PINNED[key]) return PINNED[key];
  return (Math.max(0, keys.indexOf(key)) % COLOURS) + 1;
}
