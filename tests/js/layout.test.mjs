/* The front-end layout from plan.md exists, so the JavaScript test run is never empty. */

import assert from "node:assert/strict";
import { statSync } from "node:fs";
import { test } from "node:test";

test("site/js/core exists", () => {
  assert.ok(statSync(new URL("../../site/js/core", import.meta.url)).isDirectory());
});
