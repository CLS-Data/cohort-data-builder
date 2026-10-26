/* Which view is on screen. Its own module so views can switch to each other without
   importing each other. */

import { state } from "./state.js";

const shown = new Map();

/**
 * Register what a view draws as it comes into sight.
 * @param {string} view The view name ("search" or "basket").
 * @param {() => void} fn Called each time the view is shown.
 */
export const onShow = (view, fn) => {
  shown.set(view, fn);
};

/**
 * Show one view and mark its tab current.
 * @param {string} view The view name ("search" or "basket").
 */
export function switchView(view) {
  state.view = view;
  for (const tab of document.querySelectorAll(".view-tab")) {
    const on = tab.dataset.view === view;
    tab.classList.toggle("is-current", on);
    if (on) tab.setAttribute("aria-current", "page");
    else tab.removeAttribute("aria-current");
  }
  for (const v of document.querySelectorAll(".view")) {
    v.classList.toggle("is-current", v.dataset.view === view);
  }
  shown.get(view)?.();
}
