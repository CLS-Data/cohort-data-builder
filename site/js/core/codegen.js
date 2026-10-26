/* Turning a selection into the files of a downloadable project.

   Almost nothing here is R or Python: the loaders and the merge logic are templates in
   site/templates/, reviewed as R and as Python. This fills in the selection, the
   missing-value codes, the labels and the README. Dictionaries and templates are passed
   in, so it runs under Node in tests. */

/** The output file types, by option value. */
export const FORMATS = {
  csv: { ext: "csv", name: "CSV" },
  dta: { ext: "dta", name: "Stata" },
  sav: { ext: "sav", name: "SPSS" },
};

const ID_LABEL = "Identifier: every file is merged on this";

/* Anything from a dictionary can contain anything, so every string inside a quoted literal
   is escaped. R and Python accept the same escapes for what matters here. */
const quote = (s) =>
  `"${String(s ?? "")
    .replace(/\\/g, "\\\\")
    .replace(/"/g, '\\"')
    .replace(/\r?\n/g, " ")}"`;

const fill = (template, values) =>
  template.replace(/\{\{(\w+)\}\}/g, (whole, key) => (key in values ? values[key] : whole));

/** "-1.0" -> "-1": the dictionaries store every code as a decimal. */
const code = (value) => String(value).replace(/\.0$/, "");

function byFile(selection) {
  const out = new Map();
  for (const b of selection) {
    if (!out.has(b.file)) out.set(b.file, []);
    out.get(b.file).push(b);
  }
  return out;
}

/* Each selected variable's dictionary entry (undefined when the dictionary lacks it). */
const entriesOf = (selection, dicts) =>
  new Map(selection.map((b) => [b, dicts[b.file]?.variables.find((v) => v.variable === b.name)]));

/* ── The selection and missing codes, in each language ─────────────── */

const rSelection = (groups) =>
  [...groups]
    .map(
      ([file, items]) =>
        `  ${quote(file)} = c(\n${items.map((b) => `    ${quote(b.column)} = ${quote(b.name)}`).join(",\n")}\n  )`,
    )
    .join(",\n");

const pySelection = (groups) =>
  [...groups]
    .map(
      ([file, items]) =>
        `    ${quote(file)}: {\n${items.map((b) => `        ${quote(b.column)}: ${quote(b.name)},`).join("\n")}\n    },`,
    )
    .join("\n");

/* Only the supplied na.values and na.ranges (FR-024): kept codes are answers, and lossy
   codes are already among the values or ranges. */
function codesOf(entry) {
  const values = entry?.na?.values || [];
  const ranges = entry?.na?.ranges || [];
  return values.length || ranges.length ? { values, ranges } : null;
}

const rCodes = (selection, entries) =>
  selection
    .map((b) => [b, codesOf(entries.get(b))])
    .filter(([, c]) => c)
    .map(([b, { values, ranges }]) => {
      const v = values.length ? `c(${values.join(", ")})` : "numeric(0)";
      const r = ranges
        .map(([lo, hi]) => `c(${lo === null ? "NA" : lo}, ${hi === null ? "NA" : hi})`)
        .join(", ");
      return `  ${quote(b.column)} = list(values = ${v}, ranges = list(${r}))`;
    })
    .join(",\n");

const pyCodes = (selection, entries) =>
  selection
    .map((b) => [b, codesOf(entries.get(b))])
    .filter(([, c]) => c)
    .map(([b, { values, ranges }]) => {
      const r = ranges
        .map(([lo, hi]) => `[${lo === null ? "None" : lo}, ${hi === null ? "None" : hi}]`)
        .join(", ");
      return `    ${quote(b.column)}: {"values": [${values.join(", ")}], "ranges": [${r}]},`;
    })
    .join("\n");

/* ── Labels, for Stata and SPSS output ─────────────────────────────── */

/* A column's value labels as [code, label] pairs, or null. Whole-number codes only: Stata
   cannot label anything else, and a set with a fraction in it is not a coding scheme.
   One label per code, the first the dictionary gives. */
function codeLabels(entry) {
  const out = new Map();
  for (const v of entry?.values || []) {
    const x = Number(v.value);
    if (!Number.isInteger(x)) return null;
    if (!out.has(x)) out.set(x, String(v.label ?? ""));
  }
  return out.size ? [...out] : null;
}

const labelOf = (b, entries) => entries.get(b)?.label || b.label || b.name;

const rLabels = (selection, entries, identifier) =>
  [
    `  ${quote(identifier)} = ${quote(ID_LABEL)}`,
    ...selection.map((b) => `  ${quote(b.column)} = ${quote(labelOf(b, entries))}`),
  ].join(",\n");

const pyLabels = (selection, entries, identifier) =>
  [
    `    ${quote(identifier)}: ${quote(ID_LABEL)},`,
    ...selection.map((b) => `    ${quote(b.column)}: ${quote(labelOf(b, entries))},`),
  ].join("\n");

const rValueLabels = (selection, entries) =>
  selection
    .map((b) => [b, codeLabels(entries.get(b))])
    .filter(([, c]) => c)
    .map(
      ([b, c]) => `  ${quote(b.column)} = c(${c.map(([x, l]) => `${quote(l)} = ${x}`).join(", ")})`,
    )
    .join(",\n");

const pyValueLabels = (selection, entries) =>
  selection
    .map((b) => [b, codeLabels(entries.get(b))])
    .filter(([, c]) => c)
    .map(
      ([b, c]) => `    ${quote(b.column)}: {${c.map(([x, l]) => `${x}: ${quote(l)}`).join(", ")}},`,
    )
    .join("\n");

/* ── The codebook ────────────────────────────────────────────────────── */

const csvCell = (s) => {
  const t = String(s ?? "");
  return /[",\n\r]/.test(t) ? `"${t.replace(/"/g, '""')}"` : t;
};

/* "-9, -3 to -1, -1 and below": what MISSING_TO_NA replaces. */
function describeNa(na) {
  if (!na) return "";
  const parts = (na.values || []).map(String);
  for (const [lo, hi] of na.ranges || []) {
    parts.push(
      lo === null ? `${hi} and below` : hi === null ? `${lo} and above` : `${lo} to ${hi}`,
    );
  }
  return parts.join(", ");
}

/**
 * The codebook: one CSV row per output column, the identifier first.
 * @param {object[]} selection The selection.
 * @param {object} manifest The cohort manifest.
 * @param {Object<string, object>} dicts Each selected file's dictionary, by file name.
 * @returns {string} RFC 4180 CSV text with columns column, variable, file, wave, label,
 *   missing_codes, negative_kept, value_labels and topics.
 */
export function codebook(selection, manifest, dicts) {
  const entries = entriesOf(selection, dicts);
  const topicLabels = new Map(
    (manifest.topics?.domains || []).flatMap((d) => d.topics.map((t) => [t.id, t.label])),
  );
  const rows = [
    [
      "column",
      "variable",
      "file",
      "wave",
      "label",
      "missing_codes",
      "negative_kept",
      "value_labels",
      "topics",
    ],
    [manifest.identifier, manifest.identifier, "", "", ID_LABEL, "", "", "", ""],
  ];
  for (const b of selection) {
    const entry = entries.get(b);
    rows.push([
      b.column,
      b.name,
      b.file,
      b.wave,
      entry?.label || b.label,
      describeNa(entry?.na),
      (entry?.na?.kept || []).map(([x, l]) => `${x}=${l}`).join("; "),
      (entry?.values || []).map((v) => `${code(v.value)}=${v.label}`).join("; "),
      (entry?.topics || [])
        .map(([id, c]) => `${topicLabels.get(id) || id} (${c.toFixed(2)})`)
        .join("; "),
    ]);
  }
  return `${rows.map((r) => r.map(csvCell).join(",")).join("\n")}\n`;
}

/* ── The README ──────────────────────────────────────────────────────── */

function runSteps(languages, project) {
  const steps = [];
  if (languages.includes("r")) {
    steps.push(`**R.** Open \`${project}.Rproj\` in RStudio and source \`R/merge.R\`, or run
\`Rscript R/merge.R\` from this folder. Reading \`.tab\` and \`.csv\` files needs only base R;
\`.dta\` and \`.sav\` files need \`install.packages("haven")\`.`);
  }
  if (languages.includes("python")) {
    steps.push(`**Python.** \`pip install -r python/requirements.txt\`, then
\`python python/merge.py\`. \`pyreadstat\` is only needed for \`.sav\` files.`);
  }
  return steps.join("\n\n");
}

function contents(languages, project) {
  const lines = [
    "    README.md          this file",
    "    codebook.csv       what every output column is",
    "    data/              where the data files go",
    "    output/            created on the first run",
  ];
  if (languages.includes("r")) {
    lines.push(
      `    ${project}.Rproj`,
      "    R/load_data.R      finds and reads data files; the read call follows the extension",
      "    R/merge.R          your selection and the merge: run this",
    );
  }
  if (languages.includes("python")) {
    lines.push(
      "    python/load_data.py  finds and reads data files; the read call follows the extension",
      "    python/merge.py      your selection and the merge: run this",
      "    python/requirements.txt",
    );
  }
  return lines.join("\n");
}

const MISSING_ON =
  "**Missing-value codes are converted to NA.** Each variable's missing-value codes, as " +
  "listed in the data dictionary (`codebook.csv`, column `missing_codes`), are replaced " +
  "with NA. Negative codes that are real answers (column `negative_kept`) are kept. Set " +
  "`MISSING_TO_NA` to false at the top of the merge script to keep every code.";
const MISSING_OFF =
  "**Missing-value codes are kept as deposited.** Set `MISSING_TO_NA` to true at the top " +
  "of the merge script to replace them with NA: `codebook.csv` lists which codes that " +
  "would replace (column `missing_codes`).";

/* ── Everything together ─────────────────────────────────────────────── */

/**
 * Build every file of the download.
 * @param {object[]} selection The selection, in output order.
 * @param {object} manifest The cohort manifest.
 * @param {Object<string, object>} dicts Each selected file's dictionary, by file name.
 * @param {Object<string, string>} templates The text of each file in site/templates/, by
 *   path relative to that folder (e.g. "r/merge.R").
 * @param {{languages: string[], missingToNa: boolean, outputFormat: string}} options The
 *   download options.
 * @param {string} today The date, YYYY-MM-DD, used in the project name.
 * @returns {{name: string, files: Array<[string, string]>}} The project name
 *   (`<key>-merge-<date>`) and its files as `[path, text]`, paths under the project folder.
 */
export function buildProject(selection, manifest, dicts, templates, options, today) {
  const project = `${manifest.key}-merge-${today}`;
  const { languages, missingToNa } = options;
  const format = FORMATS[options.outputFormat] ? options.outputFormat : "csv";
  const groups = byFile(selection);
  const entries = entriesOf(selection, dicts);

  const fileInfo = new Map(manifest.files.map((f) => [f.name, f]));
  const fileList = [...groups.keys()]
    .map((f) => {
      const info = fileInfo.get(f) || {};
      return `- \`${f}\`${info.description ? `: ${info.description}` : ""} (${info.wave || "?"})`;
    })
    .join("\n");
  const common = {
    dataset: manifest.name,
    full_name: manifest.fullName,
    created: today,
    identifier: manifest.identifier,
    ukds_url: manifest.ukdsUrl || "the UK Data Service",
    files: fileList,
  };

  const files = [];
  const add = (path, text) => files.push([`${project}/${path}`, text]);
  const n = selection.length;
  add(
    "README.md",
    fill(templates["README.md"], {
      ...common,
      count: `${n} variable${n === 1 ? "" : "s"}`,
      ext: FORMATS[format].ext,
      format_note:
        format === "csv"
          ? " CSV has no room for labels: `codebook.csv` has them."
          : ` A ${FORMATS[format].name} file, with each column's label and value labels from ` +
            "the data dictionary. To get a different file type, change `OUTPUT_FORMAT` at the " +
            'top of the merge script ("csv", "dta" or "sav").',
      languages:
        languages.length === 2
          ? "The same merge is included in R and in Python; use whichever you prefer."
          : `The merge is written in ${languages[0] === "r" ? "R" : "Python"}.`,
      missing_note: missingToNa ? MISSING_ON : MISSING_OFF,
      run: runSteps(languages, project),
      contents: contents(languages, project),
    }),
  );
  add("codebook.csv", codebook(selection, manifest, dicts));
  add("data/README.md", fill(templates["data-README.md"], common));

  const settings = (yes, no) => ({
    ...common,
    missing_to_na: missingToNa ? yes : no,
    output_format: format,
  });
  if (languages.includes("r")) {
    add(`${project}.Rproj`, templates["project.Rproj"]);
    add("R/load_data.R", templates["r/load_data.R"]);
    add(
      "R/merge.R",
      fill(templates["r/merge.R"], {
        ...settings("TRUE", "FALSE"),
        selection: rSelection(groups),
        missing_codes: rCodes(selection, entries),
        labels: rLabels(selection, entries, manifest.identifier),
        value_labels: rValueLabels(selection, entries),
      }),
    );
  }
  if (languages.includes("python")) {
    add("python/load_data.py", templates["python/load_data.py"]);
    add("python/requirements.txt", templates["python/requirements.txt"]);
    add(
      "python/merge.py",
      fill(templates["python/merge.py"], {
        ...settings("True", "False"),
        selection: pySelection(groups),
        missing_codes: pyCodes(selection, entries),
        labels: pyLabels(selection, entries, manifest.identifier),
        value_labels: pyValueLabels(selection, entries),
      }),
    );
  }
  return { name: project, files };
}
