/* Links that let a researcher tell the maintainers something is wrong. Pure: no DOM. */

/**
 * The project's public repository, where issues are raised. Change it here in a fork.
 * @type {string}
 */
export const REPOSITORY = "https://github.com/CLS-Data/cohort-data-builder";

const MAX_URL = 8000; // GitHub refuses much longer issue links
const MAX_LABEL = 300;

/**
 * What a choice of topics changes about a variable's tags.
 * @param {{topics?: Array<[string, number]>}} entry The variable's dictionary entry.
 * @param {string[]} chosen The topic ids the variable should have.
 * @returns {{add: string[], remove: string[]}} Topic ids to add (in `chosen` order) and to
 *   remove (in the entry's order).
 */
export function topicChanges(entry, chosen) {
  const current = (entry.topics || []).map(([id]) => id);
  return {
    add: chosen.filter((id) => !current.includes(id)),
    remove: current.filter((id) => !chosen.includes(id)),
  };
}

/* Cut to `max` characters, the last being an ellipsis. */
const cut = (s, max) => (s.length > max ? `${s.slice(0, Math.max(0, max - 1))}…` : s);

/**
 * A link to a new GitHub issue, from the tag-suggestion form, pre-filled with what is
 * known about one variable (its cohort, name, file, label and current topic tags) and,
 * when given, the topics the researcher chose for it.
 * @param {{variable: string, label?: string, topics?: Array<[string, number]>}} entry The
 *   variable's dictionary entry; `topics` are `[topic id, confidence 0–1]`.
 * @param {string} file The data file the variable is in.
 * @param {{name: string, topics?: {domains: Array<{topics: Array<{id: string, label: string}>}>}}} manifest
 *   The cohort manifest, for its name and topic labels.
 * @param {{topics: string[], why?: string}} [suggestion] The topic ids the variable should
 *   have, and why. Written into the form as "Add: Domain › Topic…" and "Remove: …" lines.
 * @returns {string} The URL, at most 8,000 characters: when longer, the current tags, the
 *   reason and then the label are shortened, never the cohort, variable or file.
 */
export function tagSuggestionUrl(entry, file, manifest, suggestion) {
  const domains = manifest.topics?.domains || [];
  const names = new Map(domains.flatMap((d) => d.topics.map((t) => [t.id, t.label])));
  const full = new Map(
    domains.flatMap((d) => d.topics.map((t) => [t.id, `${d.label} › ${t.label}`])),
  );
  const tags = (entry.topics || [])
    .map(([id, conf]) => `${names.get(id) || id} (${Math.round(conf * 100)}%)`)
    .join("; ");
  const fields = {
    template: "tag-suggestion.yml",
    title: `Tag suggestion: ${entry.variable} (${manifest.name})`,
    cohort: manifest.name,
    variable: entry.variable,
    file,
    label: cut(String(entry.label || ""), MAX_LABEL),
    current: tags || "none",
  };
  if (suggestion) {
    const { add, remove } = topicChanges(entry, suggestion.topics);
    const list = (ids) => ids.map((id) => full.get(id) || id).join("; ");
    fields.suggested = [
      add.length ? `Add: ${list(add)}` : "",
      remove.length ? `Remove: ${list(remove)}` : "",
    ]
      .filter(Boolean)
      .join("\n");
    if (suggestion.why?.trim()) fields.why = suggestion.why.trim();
  }
  const url = () => `${REPOSITORY}/issues/new?${new URLSearchParams(fields)}`;
  for (const key of ["current", "why", "label"]) {
    if (!(key in fields)) continue;
    // Each pass drops what was over, in encoded characters, plus a little for the ellipsis.
    while (url().length > MAX_URL && fields[key].length > 1) {
      const over = url().length - MAX_URL;
      fields[key] = cut(fields[key], Math.max(1, fields[key].length - Math.ceil(over / 3) - 1));
    }
  }
  return url();
}
