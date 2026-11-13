/* The "Suggest a tag change" dialog. Tags come from a language model and some are wrong:
   here a researcher ticks the topics a variable should have, from the cohort's own topic
   list, and is sent to a GitHub issue that already says what to add and remove. Nothing
   in the builder changes. */

import { tagSuggestionUrl, topicChanges } from "../core/feedback.js";
import { esc } from "../core/text.js";
import { state } from "./state.js";

const $ = (s) => document.querySelector(s);
let open = null; // {entry, file, opener} while the dialog is showing

const chosen = () => [...document.querySelectorAll("#tag-list input:checked")].map((i) => i.value);

/* The current tags first, ticked, so they are seen before the long list; then every other
   topic by domain. */
function renderList(entry) {
  const domains = state.manifest.topics?.domains || [];
  const conf = new Map((entry.topics || []).map(([id, c]) => [id, Math.round(c * 100)]));
  const domainOf = new Map(domains.flatMap((d) => d.topics.map((t) => [t.id, d])));
  const option = (
    t,
    d,
  ) => `<label class="tag-opt" data-search="${esc(`${d.label} ${t.label}`.toLowerCase())}">
    <input type="checkbox" value="${esc(t.id)}" ${conf.has(t.id) ? "checked" : ""}>
    ${esc(t.label)}${conf.has(t.id) ? ` <span class="vm-pct">${conf.get(t.id)}%</span>` : ""}</label>`;
  const group = (legend, items) =>
    items.length
      ? `<fieldset class="tag-domain"><legend>${esc(legend)}</legend>${items.join("")}</fieldset>`
      : "";
  const current = (entry.topics || [])
    .filter(([id]) => domainOf.has(id))
    .map(([id]) =>
      option(
        domainOf.get(id).topics.find((t) => t.id === id),
        domainOf.get(id),
      ),
    );
  $("#tag-list").innerHTML =
    group("Current tags", current) +
    domains
      .map((d) =>
        group(
          d.label,
          d.topics.filter((t) => !conf.has(t.id)).map((t) => option(t, d)),
        ),
      )
      .join("");
}

/* "Adds Tenure · removes Alcohol": what the issue will ask for. */
function renderChanges() {
  const names = new Map(state.topics.map((t) => [t.id, t.label]));
  const { add, remove } = topicChanges(open.entry, chosen());
  const say = (verb, ids) =>
    ids.length ? `${verb} ${ids.map((id) => names.get(id) || id).join(", ")}` : "";
  const text = [say("Adds", add), say("removes", remove)].filter(Boolean).join(" · ");
  $("#tag-changes").textContent = text
    ? text[0].toUpperCase() + text.slice(1)
    : "No change yet: tick or untick a topic.";
  $("#tag-send").disabled = !text;
}

function filter(q) {
  const words = q.toLowerCase().trim().split(/\s+/).filter(Boolean);
  for (const label of document.querySelectorAll("#tag-list .tag-opt")) {
    label.hidden = !words.every((w) => label.dataset.search.includes(w));
  }
  for (const set of document.querySelectorAll("#tag-list .tag-domain")) {
    set.hidden = !set.querySelector(".tag-opt:not([hidden])");
  }
}

/**
 * Open the dialog for one variable.
 * @param {{variable: string, label?: string, topics?: Array<[string, number]>}} entry The
 *   variable's dictionary entry.
 * @param {string} file The data file the variable is in.
 * @param {HTMLElement} opener The control that opened it, given focus back on close.
 */
export function openSuggest(entry, file, opener) {
  open = { entry, file, opener };
  $("#tag-dialog-title").textContent = `Suggest tags for ${entry.variable}`;
  $("#tag-filter").value = "";
  $("#tag-why").value = "";
  renderList(entry);
  renderChanges();
  $("#tag-dialog").showModal();
  $("#tag-filter").focus();
}

/** Attach the dialog's event handlers. Call once. */
export function wireSuggest() {
  const dialog = $("#tag-dialog");
  $("#tag-filter").addEventListener("input", (e) => filter(e.target.value));
  $("#tag-list").addEventListener("change", renderChanges);
  $("#tag-cancel").addEventListener("click", () => dialog.close());
  $("#tag-send").addEventListener("click", () => {
    const url = tagSuggestionUrl(open.entry, open.file, state.manifest, {
      topics: chosen(),
      why: $("#tag-why").value,
    });
    window.open(url, "_blank", "noopener");
    dialog.close();
  });
  dialog.addEventListener("close", () => {
    open?.opener?.focus();
    open = null;
  });
}
