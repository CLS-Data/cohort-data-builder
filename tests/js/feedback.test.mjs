import assert from "node:assert/strict";
import { test } from "node:test";
import { REPOSITORY, tagSuggestionUrl, topicChanges } from "../../site/js/core/feedback.js";

const manifest = {
  name: "Mini",
  topics: {
    domains: [
      {
        id: "health",
        label: "Health",
        topics: [
          { id: "smoking", label: "Smoking" },
          { id: "pregnancy", label: "Pregnancy" },
        ],
      },
    ],
  },
};
const entry = (o = {}) => ({
  variable: "smoke5",
  label: "Smokes at 5",
  topics: [
    ["smoking", 0.9],
    ["pregnancy", 0.6],
  ],
  ...o,
});
const params = (url) => new URL(url).searchParams;

test("the link opens the tag-suggestion form on the repository", () => {
  const url = tagSuggestionUrl(entry(), "mini_age5", manifest);
  assert.ok(url.startsWith(`${REPOSITORY}/issues/new?`));
  assert.equal(REPOSITORY, "https://github.com/CLS-Data/cohort-data-builder");
  assert.equal(params(url).get("template"), "tag-suggestion.yml");
});

test("the form is pre-filled with the variable, cohort, file, label and tags", () => {
  const p = params(tagSuggestionUrl(entry(), "mini_age5", manifest));
  assert.equal(p.get("title"), "Tag suggestion: smoke5 (Mini)");
  assert.equal(p.get("cohort"), "Mini");
  assert.equal(p.get("variable"), "smoke5");
  assert.equal(p.get("file"), "mini_age5");
  assert.equal(p.get("label"), "Smokes at 5");
  assert.equal(p.get("current"), "Smoking (90%); Pregnancy (60%)");
});

test("a variable without tags says none", () => {
  const p = params(tagSuggestionUrl(entry({ topics: [] }), "f", manifest));
  assert.equal(p.get("current"), "none");
  assert.equal(
    params(tagSuggestionUrl(entry({ topics: undefined }), "f", manifest)).get("current"),
    "none",
  );
});

test("every value is URL-encoded", () => {
  const label = 'Fish & chips #1 + "ç" é';
  const url = tagSuggestionUrl(entry({ label }), "f", manifest);
  assert.ok(!url.includes(" "));
  assert.ok(!url.includes('"'));
  assert.equal(params(url).get("label"), label);
});

test("a long label is cut to 300 characters", () => {
  const label = params(tagSuggestionUrl(entry({ label: "x".repeat(500) }), "f", manifest)).get(
    "label",
  );
  assert.equal(label.length, 300);
  assert.ok(label.endsWith("…"));
});

test("a URL over 8,000 characters is cut, keeping cohort, variable and file whole", () => {
  const topics = Array.from({ length: 900 }, (_, i) => [`t${i}`, 0.5]);
  const big = {
    name: "Mini",
    topics: {
      domains: [
        {
          id: "d",
          label: "D",
          topics: topics.map(([id]) => ({ id, label: `Topic number ${id}` })),
        },
      ],
    },
  };
  const url = tagSuggestionUrl(entry({ topics }), "mini_age5", big);
  assert.ok(url.length <= 8000, String(url.length));
  const p = params(url);
  assert.equal(p.get("variable"), "smoke5");
  assert.equal(p.get("cohort"), "Mini");
  assert.equal(p.get("file"), "mini_age5");
  assert.ok(p.get("current").endsWith("…"));
});

/* ── A suggestion chosen in the builder ─────────────────────────────── */

const withHousing = {
  ...manifest,
  topics: {
    domains: [
      ...manifest.topics.domains,
      { id: "housing", label: "Housing", topics: [{ id: "tenure", label: "Tenure" }] },
    ],
  },
};

test("the chosen topics become what to add and what to remove", () => {
  const p = params(
    tagSuggestionUrl(entry(), "f", withHousing, {
      topics: ["smoking", "tenure"],
      why: "It asks about rent.",
    }),
  );
  assert.equal(p.get("suggested"), "Add: Housing › Tenure\nRemove: Health › Pregnancy");
  assert.equal(p.get("why"), "It asks about rent.");
});

test("only additions, or only removals, say only that", () => {
  const add = tagSuggestionUrl(entry({ topics: [] }), "f", withHousing, { topics: ["tenure"] });
  assert.equal(params(add).get("suggested"), "Add: Housing › Tenure");
  assert.equal(params(add).has("why"), false);
  const drop = tagSuggestionUrl(entry(), "f", withHousing, { topics: [] });
  assert.equal(params(drop).get("suggested"), "Remove: Health › Smoking; Health › Pregnancy");
});

test("without a suggestion the form's suggestion is left for the user", () => {
  assert.equal(params(tagSuggestionUrl(entry(), "f", manifest)).has("suggested"), false);
});

test("topicChanges says what a choice adds and removes", () => {
  assert.deepEqual(topicChanges(entry(), ["smoking", "tenure"]), {
    add: ["tenure"],
    remove: ["pregnancy"],
  });
  assert.deepEqual(topicChanges(entry({ topics: undefined }), []), { add: [], remove: [] });
});
