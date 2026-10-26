/* Text helpers for building HTML strings safely. No DOM, no state. */

const ENTITIES = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };

/**
 * Escape text for use in HTML content or a quoted attribute.
 * @param {unknown} s Any value; null and undefined become "".
 * @returns {string} The escaped text.
 */
export const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ENTITIES[c]);

/**
 * Escape text and wrap the first case-insensitive match of `term` in `<mark>`.
 * @param {unknown} text The text to show.
 * @param {string} term The search term; empty means no highlight.
 * @returns {string} Safe HTML.
 */
export function highlight(text, term) {
  const t = String(text ?? "");
  if (!term) return esc(t);
  const i = t.toLowerCase().indexOf(term.toLowerCase());
  if (i < 0) return esc(t);
  return `${esc(t.slice(0, i))}<mark>${esc(t.slice(i, i + term.length))}</mark>${esc(t.slice(i + term.length))}`;
}

/**
 * Upper-case the first character.
 * @param {unknown} s The text.
 * @returns {string} The text with its first character upper-cased.
 */
export const capitalise = (s) => String(s).replace(/^./, (c) => c.toUpperCase());

/**
 * A measurement level's display name: NOMINAL becomes Nominal, -1 becomes Unrecorded.
 * @param {string[]} levels The manifest's `levels` list.
 * @param {number} i A level index from an index row, or -1 when none was recorded.
 * @returns {string} The display name ("?" for an index out of range).
 */
export function levelName(levels, i) {
  if (i === -1) return "Unrecorded";
  const name = (levels || [])[i] || "?";
  return name.charAt(0) + name.slice(1).toLowerCase();
}
