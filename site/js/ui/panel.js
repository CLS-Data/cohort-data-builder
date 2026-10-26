/* The selection beside the list: what you have picked so far, kept in view while you pick,
   so a click visibly lands somewhere.

   A summary rather than the whole Selection view: a count, the variables grouped by sweep
   or by file, a filter for when there are hundreds, and the way on to review and download.
   Quick with thousands selected: a group draws its first GROUP_SHOWN rows until asked for
   the rest, and a closed group draws none. */

import { keyOf, remove } from "../core/selection.js";
import { capitalise, esc } from "../core/text.js";
import { saveOptions, setSelection } from "./selected.js";
import { state } from "./state.js";
import { switchView } from "./views.js";

const $ = (sel) => document.querySelector(sel);
const n = (x) => x.toLocaleString("en-GB");
const GROUP_SHOWN = 200;
const CLEAR_WAIT_MS = 4000;

const closed = new Set(); // groups folded away
const full = new Set(); // groups showing every row
let filter = "";
let clearArmed = null; // the timer while "Clear" waits for its second click

function groupsOf(items) {
  const byFile = state.options.panelGroup === "file";
  const order = state.manifest.wave.list.map((w) => w.key);
  const groups = new Map();
  for (const b of items) {
    const g = byFile ? b.file : b.wave;
    if (!groups.has(g)) groups.set(g, []);
    groups.get(g).push(b);
  }
  return [...groups].sort(([a], [b]) =>
    byFile ? a.localeCompare(b) : order.indexOf(a) - order.indexOf(b),
  );
}

function rowHtml(b) {
  const label = b.label || "no label";
  return `<li class="sp-row">
    <span class="sp-name" title="${esc(b.name)}">${esc(b.name)}</span>
    <span class="sp-label" title="${esc(label)}">${esc(label)}</span>
    <span class="sp-meta">${esc(state.options.panelGroup === "file" ? b.wave : b.file)}</span>
    <button class="sp-x" data-remove="${esc(keyOf(b))}" aria-label="Remove ${esc(b.name)}" title="Remove">✕</button>
  </li>`;
}

/** Redraw the panel and the Selection tab's tally from the current selection. */
export function renderPanel() {
  if (!state.manifest) return;
  const count = state.bundle.length;
  $("#sp-toggle").textContent = `Selected (${n(count)})`;
  const tally = $("#basket-tally");
  tally.hidden = !count;
  tally.textContent = n(count);
  $("#sp-count").innerHTML = count
    ? `<strong>${n(count)}</strong> variable${count === 1 ? "" : "s"} selected`
    : "Nothing selected yet";
  $("#sp-clear").hidden = !count;
  $("#sp-tools").hidden = !count;
  $("#sp-review").hidden = !count;
  $("#sp-group-wave").textContent = capitalise(state.manifest.wave.term);
  for (const b of document.querySelectorAll("#spanel [data-group]")) {
    b.setAttribute("aria-pressed", String(b.dataset.group === state.options.panelGroup));
  }

  const list = $("#sp-list");
  if (!count) {
    list.innerHTML = `<p class="sp-empty">Click a variable to add it here.</p>`;
    return;
  }
  const q = filter.trim().toLowerCase();
  const items = q
    ? state.bundle.filter(
        (b) => b.name.toLowerCase().includes(q) || (b.label || "").toLowerCase().includes(q),
      )
    : state.bundle;
  if (!items.length) {
    list.innerHTML = `<p class="sp-empty">None of the ${n(count)} match “${esc(filter.trim())}”.</p>`;
    return;
  }
  list.innerHTML = groupsOf(items)
    .map(([g, rows]) => {
      const open = !closed.has(g);
      const shown = open ? (full.has(g) ? rows : rows.slice(0, GROUP_SHOWN)) : [];
      return `<section class="sp-grp">
      <button class="sp-grp-head" data-grp="${esc(g)}" aria-expanded="${open}">
        <span class="sp-caret" aria-hidden="true">${open ? "▾" : "▸"}</span>
        <span class="sp-grp-name">${esc(g)}</span>
        <span class="sp-grp-n">${n(rows.length)}</span></button>
      ${open ? `<ul class="sp-rows">${shown.map(rowHtml).join("")}</ul>` : ""}
      ${open && shown.length < rows.length ? `<button class="link-btn sp-all" data-all="${esc(g)}">Show all ${n(rows.length)}</button>` : ""}
    </section>`;
    })
    .join("");
}

/* On a mid-width screen the panel is shown on request; the choice is remembered. */
function setOpen(open) {
  state.options.panelOpen = open;
  $(".vwork").classList.toggle("is-panel-open", open);
  $("#sp-toggle").setAttribute("aria-expanded", String(open));
  saveOptions();
}

function clearClicked() {
  // Two clicks: a few hundred picks shouldn't go on one slip.
  const btn = $("#sp-clear");
  if (clearArmed) {
    clearTimeout(clearArmed);
    clearArmed = null;
    btn.textContent = "Clear";
    setSelection([]);
    return;
  }
  btn.textContent = `Clear all ${n(state.bundle.length)}?`;
  clearArmed = setTimeout(() => {
    clearArmed = null;
    btn.textContent = "Clear";
  }, CLEAR_WAIT_MS);
}

/** Attach the panel's event handlers. Call once, after the options are restored. */
export function wirePanel() {
  setOpen(state.options.panelOpen);
  $("#sp-toggle").addEventListener("click", () => setOpen(!state.options.panelOpen));
  $("#sp-q").addEventListener("input", (e) => {
    filter = e.target.value;
    renderPanel();
  });

  $("#spanel").addEventListener("click", (e) => {
    const group = e.target.closest("[data-group]");
    if (group) {
      state.options.panelGroup = group.dataset.group;
      saveOptions();
      closed.clear();
      full.clear();
      return renderPanel();
    }
    const head = e.target.closest("[data-grp]");
    if (head) {
      const g = head.dataset.grp;
      if (closed.has(g)) closed.delete(g);
      else closed.add(g);
      renderPanel();
      return $(`#sp-list [data-grp="${CSS.escape(g)}"]`)?.focus();
    }
    const all = e.target.closest("[data-all]");
    if (all) {
      full.add(all.dataset.all);
      return renderPanel();
    }
    const x = e.target.closest("[data-remove]");
    if (x) {
      // Focus moves to the next ✕, so a keyboard user can keep removing.
      const at = [...document.querySelectorAll("#sp-list .sp-x")].indexOf(x);
      const had = document.activeElement === x;
      setSelection(remove(state.bundle, x.dataset.remove).selection);
      if (had) {
        const rest = document.querySelectorAll("#sp-list .sp-x");
        (rest[Math.min(at, rest.length - 1)] || $("#sp-list")).focus();
      }
      return;
    }
    if (e.target.closest("#sp-review")) return switchView("basket");
    if (e.target.closest("#sp-clear")) clearClicked();
  });
}
