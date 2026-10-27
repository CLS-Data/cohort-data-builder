/* Write a generated project to disk, for the Python tests that run its R and Python.

   node tests/js/generate_bundle.mjs <data_dir> <cohort> <out_dir> <missingToNa> \
       <csv|dta|sav> <langs> <file:variable[:column]>...

   <missingToNa> is "true" or "false"; <langs> is "r", "python" or "r,python". Columns not
   given get the site's defaults. The project's files are written directly into out_dir. */

import { mkdir, readFile, writeFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { buildProject } from "../../site/js/core/codegen.js";
import { addMany } from "../../site/js/core/selection.js";

const TEMPLATES = new URL("../../site/templates/", import.meta.url);
const TEMPLATE_FILES = [
  "README.md",
  "data-README.md",
  "project.Rproj",
  "r/load_data.R",
  "r/merge.R",
  "python/load_data.py",
  "python/merge.py",
  "python/requirements.txt",
];

const readJson = async (path) => JSON.parse(await readFile(path, "utf8"));

async function main() {
  const [dataDir, cohort, outDir, missingToNa, outputFormat, langs, ...picks] =
    process.argv.slice(2);
  const manifest = await readJson(join(dataDir, cohort, "manifest.json"));
  const waveOf = new Map(manifest.files.map((f) => [f.name, f.wave]));

  let selection = [];
  for (const pick of picks) {
    const [file, name, column] = pick.split(":");
    const item = { name, label: "", file, wave: waveOf.get(file) };
    const r = addMany(selection, [item], manifest);
    if (r.reason || !r.changed) throw new Error(`cannot select ${pick}: ${r.reason}`);
    selection = r.selection;
    if (column) selection[selection.length - 1].column = column;
  }

  const dicts = {};
  for (const file of new Set(selection.map((b) => b.file))) {
    dicts[file] = await readJson(join(dataDir, cohort, "dict", `${file}.json`));
  }
  const templates = {};
  for (const t of TEMPLATE_FILES) templates[t] = await readFile(new URL(t, TEMPLATES), "utf8");

  const options = {
    languages: langs.split(","),
    missingToNa: missingToNa === "true",
    outputFormat,
  };
  const today = new Date().toISOString().slice(0, 10);
  const { name, files } = buildProject(selection, manifest, dicts, templates, options, today);
  for (const [path, text] of files) {
    const target = join(outDir, path.slice(name.length + 1));
    await mkdir(dirname(target), { recursive: true });
    await writeFile(target, text);
  }
}

main().catch((err) => {
  console.error(err.message);
  process.exit(1);
});
