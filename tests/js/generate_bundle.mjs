/* Write a generated project to disk, for the Python tests that run its R and Python.

   node tests/js/generate_bundle.mjs <data_dir> <cohort> <out_dir> <missingToNa> \
       <csv|dta|sav> <langs> <file:variable[:column]>...
   node tests/js/generate_bundle.mjs --bundle <data_dir> <out_dir> <missingToNa> \
       <csv|dta|sav> <langs> <cohort/file:variable[:column]>...

The second form builds the several-cohort download (feature 007): picks name their cohort,
and the cohorts' folders and the top README are written into out_dir.

   <missingToNa> is "true" or "false"; <langs> is a comma-separated list of "r", "python" and
   "stata". Columns not
   given get the site's defaults. The project's files are written directly into out_dir. */

import { mkdir, readFile, writeFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { buildBundle, buildProject } from "../../site/js/core/codegen.js";
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
  "stata/load_data.do",
  "stata/merge.do",
  "cohorts-README.md",
];

const readJson = async (path) => JSON.parse(await readFile(path, "utf8"));

/* One cohort's selection and dictionaries from picks `file:variable[:column]`. */
async function projectOf(dataDir, cohort, picks) {
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
  return { selection, manifest, dicts };
}

async function main() {
  const args = process.argv.slice(2);
  const several = args[0] === "--bundle";
  if (several) args.shift();
  const [dataDir, ...rest] = args;
  const cohort = several ? null : rest.shift();
  const [outDir, missingToNa, outputFormat, langs, ...picks] = rest;

  const projects = [];
  if (several) {
    const byCohort = new Map();
    for (const pick of picks) {
      const [key, plain] = [pick.slice(0, pick.indexOf("/")), pick.slice(pick.indexOf("/") + 1)];
      if (!byCohort.has(key)) byCohort.set(key, []);
      byCohort.get(key).push(plain);
    }
    for (const [key, own] of byCohort) projects.push(await projectOf(dataDir, key, own));
  } else {
    projects.push(await projectOf(dataDir, cohort, picks));
  }

  const templates = {};
  for (const t of TEMPLATE_FILES) templates[t] = await readFile(new URL(t, TEMPLATES), "utf8");

  const options = {
    languages: langs.split(","),
    missingToNa: missingToNa === "true",
    outputFormat,
  };
  const today = new Date().toISOString().slice(0, 10);
  const { name, files } = several
    ? buildBundle(projects, templates, options, today)
    : buildProject(
        projects[0].selection,
        projects[0].manifest,
        projects[0].dicts,
        templates,
        options,
        today,
      );
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
