"""Run the generated R and Python projects on fabricated data and compare what they write."""

import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyreadstat
import pytest

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / "tests" / "fixtures" / "data"
DRIVER = ROOT / "tests" / "js" / "generate_bundle.mjs"
RUFF = Path(sys.executable).parent / "ruff"

PICKS = [
    "mini_age5:sex",
    "mini_age5:smoke5",
    "mini_age5:tenure5",
    "mini_age5:quote5",  # label with ", \ and a newline (FR-028)
    "mini_age10:sex",
    "mini_age10:alc10",
    "mini_age10:weight10",
    "mini_age10:mood10",
    "mini_grid:hhrel",
]
COLUMNS = ["PID", "sex", "smoke5", "tenure5", "quote5", "sex_10y", "alc10", "weight10", "mood10"]
INPUTS = ["tab", "csv", "dta", "sav"]
OUTPUTS = ["csv", "dta", "sav"]
FOLDERS = {"mini_age5": "sweep5", "mini_age10": "sweep10/nested", "mini_grid": "."}


def fabricate():
    """The three data files as deposited: fixed seed, overlapping people, a grid."""
    rng = np.random.default_rng(1970)
    people = [f"P{i:04d}" for i in range(1, 31)]
    age5 = pd.DataFrame(
        {
            "PID": people[:25],
            "sex": rng.choice([1, 2, -9], 25),
            "smoke5": rng.choice([1, 2], 25),
            "tenure5": rng.choice([1, 2, -1, -3], 25),
            "quote5": rng.choice([1, 2, 3, 4, 5], 25),
            "nolab5": rng.choice([0, 1], 25),
        }
    )
    n = 25
    age10 = pd.DataFrame(
        {
            # Spelt pid in this file, and padded: both must still link.
            "pid": [f" {p} " for p in people[5:]],
            "sex": rng.choice([1, 2], n),
            "alc10": rng.choice([1, 2, -1, -9, -5], n),
            "tenure10": rng.choice([1, 2], n),
            "weight10": np.round(rng.uniform(20, 45, n), 1),
            "mood10": rng.choice([1, -8], n),
            "misc10": rng.choice([7, 8], n),
        }
    )
    grid_ids = [p for p in people[:10] for _ in range(2)]
    grid = pd.DataFrame({"PID": grid_ids, "hhrel": rng.choice([1, 2], len(grid_ids))})
    return {"mini_age5": age5, "mini_age10": age10, "mini_grid": grid}


def write_data(frames, data_dir, ext, skip=()):
    for name, df in frames.items():
        if name in skip:
            continue
        folder = data_dir / FOLDERS[name]
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"{name}.{ext}"
        if ext == "tab":
            df.to_csv(path, sep="\t", index=False)
        elif ext == "csv":
            df.to_csv(path, index=False)
        elif ext == "dta":
            df.to_stata(path, write_index=False, version=118)
        else:
            pyreadstat.write_sav(df, str(path))


def generate(out, *, missing=False, fmt="csv", langs="r,python", picks=PICKS):
    subprocess.run(
        ["node", str(DRIVER), str(FIXTURE), "mini", str(out), str(missing).lower(), fmt, langs]
        + picks,
        check=True,
    )
    return out


def run(project, lang):
    cmd = ["Rscript", "R/merge.R"] if lang == "r" else [sys.executable, "python/merge.py"]
    return subprocess.run(cmd, cwd=project, capture_output=True, text=True, timeout=300)


def read(path):
    ext = path.suffix
    if ext == ".csv":
        return pd.read_csv(path)
    if ext == ".dta":
        return pd.read_stata(path, convert_categoricals=False)
    return pyreadstat.read_sav(str(path), apply_value_formats=False)[0]


def comparable(df):
    df = df.copy()
    df["PID"] = df["PID"].astype(str)
    for c in df.columns[1:]:
        df[c] = pd.to_numeric(df[c], errors="coerce").astype(float)
    return df.sort_values("PID").reset_index(drop=True)


def project_with_data(tmp_path, name, ext, **kwargs):
    project = generate(tmp_path / name, **kwargs)
    write_data(fabricate(), project / "data", ext)
    return project


def run_ok(project, lang):
    done = run(project, lang)
    assert done.returncode == 0, done.stdout + done.stderr
    return done


@pytest.mark.needs_r
@pytest.mark.parametrize("ext", INPUTS)
def test_r_and_python_agree_for_every_format(tmp_path, ext):
    for fmt in OUTPUTS:
        outs = {}
        for lang in ("r", "python"):
            project = project_with_data(tmp_path, f"{lang}-{fmt}", ext, fmt=fmt, missing=True)
            run_ok(project, lang)
            outs[lang] = {
                "merged": read(project / "output" / f"merged.{fmt}"),
                "long": read(project / "output" / f"mini_grid_long.{fmt}"),
            }
        r, py = outs["r"], outs["python"]
        assert list(r["merged"].columns) == COLUMNS
        assert list(py["merged"].columns) == COLUMNS
        pd.testing.assert_frame_equal(comparable(r["merged"]), comparable(py["merged"]))
        pd.testing.assert_frame_equal(comparable(r["long"]), comparable(py["long"]))


def test_merged_output_is_a_full_outer_join_with_the_grid_apart(tmp_path):
    project = project_with_data(tmp_path, "py", "tab", langs="python")
    run_ok(project, "python")
    merged = read(project / "output" / "merged.csv")
    frames = fabricate()
    assert list(merged.columns) == COLUMNS
    assert len(merged) == 30
    assert merged["PID"].is_unique
    only5 = merged.set_index("PID").loc["P0001"]
    assert only5["sex"] == frames["mini_age5"].set_index("PID").loc["P0001", "sex"]
    assert pd.isna(only5["alc10"])
    only10 = merged.set_index("PID").loc["P0030"]
    assert pd.isna(only10["smoke5"])
    assert not pd.isna(only10["weight10"])
    long = read(project / "output" / "mini_grid_long.csv")
    assert list(long.columns) == ["PID", "hhrel"]
    assert "hhrel" not in merged.columns


def expected_after_na(frames):
    a5 = frames["mini_age5"].set_index("PID")
    a10 = frames["mini_age10"].assign(pid=lambda d: d["pid"].str.strip()).set_index("pid")
    return {
        "sex": a5["sex"].where(a5["sex"] != -9),
        "tenure5": a5["tenure5"].where(a5["tenure5"] > -1),
        "alc10": a10["alc10"].where(~a10["alc10"].between(-9, -2)),
        "mood10": a10["mood10"].where(a10["mood10"] != -8),
        "smoke5": a5["smoke5"],
        "weight10": a10["weight10"],
    }


@pytest.mark.needs_r
@pytest.mark.parametrize("lang", ["r", "python"])
@pytest.mark.parametrize("missing", [True, False])
def test_missing_to_na_replaces_only_supplied_codes(tmp_path, lang, missing):
    project = project_with_data(tmp_path, lang, "csv", missing=missing, langs=lang)
    run_ok(project, lang)
    merged = read(project / "output" / "merged.csv").set_index("PID")
    frames = fabricate()
    if missing:
        expected = expected_after_na(frames)
        assert (merged["alc10"] == -1).any(), "kept code -1 'Dislike' must survive"
    else:
        a5 = frames["mini_age5"].set_index("PID")
        a10 = frames["mini_age10"].assign(pid=lambda d: d["pid"].str.strip()).set_index("pid")
        expected = {
            "sex": a5["sex"],
            "tenure5": a5["tenure5"],
            "alc10": a10["alc10"],
            "mood10": a10["mood10"],
            "smoke5": a5["smoke5"],
            "weight10": a10["weight10"],
        }
    for column, values in expected.items():
        got = merged[column].reindex(values.index).astype(float)
        pd.testing.assert_series_equal(got, values.astype(float), check_names=False)


@pytest.mark.needs_r
@pytest.mark.parametrize("lang", ["r", "python"])
def test_missing_file_stops_before_reading_and_lists_all(tmp_path, lang):
    project = generate(tmp_path / lang, langs=lang)
    write_data(fabricate(), project / "data", "csv", skip=("mini_age10", "mini_grid"))
    done = run(project, lang)
    assert done.returncode != 0
    said = done.stdout + done.stderr
    assert "mini_age10" in said and "mini_grid" in said
    assert "Reading" not in said
    assert not (project / "output").exists()


@pytest.mark.needs_r
@pytest.mark.parametrize("lang", ["r", "python"])
def test_selected_column_absent_from_data_is_warned_and_skipped(tmp_path, lang):
    project = generate(tmp_path / lang, langs=lang, picks=[*PICKS, "mini_age5:nolab5"])
    frames = fabricate()
    frames["mini_age5"] = frames["mini_age5"].drop(columns="nolab5")
    write_data(frames, project / "data", "csv")
    done = run_ok(project, lang)
    assert "nolab5" in done.stdout + done.stderr
    assert "nolab5" not in read(project / "output" / "merged.csv").columns


def labels_of(path):
    if path.suffix == ".sav":
        _, meta = pyreadstat.read_sav(str(path), metadataonly=True)
        return meta.column_names_to_labels, meta.variable_value_labels
    with pd.io.stata.StataReader(path) as reader:
        variable = reader.variable_labels()
        value_sets = reader.value_labels()
        reader.read(convert_categoricals=False)
        lbl = reader._lbllist
        names = reader._varlist
    values = {n: value_sets[lbl[i]] for i, n in enumerate(names) if lbl[i] in value_sets}
    return variable, values


@pytest.mark.needs_r
@pytest.mark.parametrize("lang", ["r", "python"])
@pytest.mark.parametrize("fmt", ["dta", "sav"])
def test_stata_and_spss_carry_labels(tmp_path, lang, fmt):
    project = project_with_data(tmp_path, lang, "csv", fmt=fmt, langs=lang)
    run_ok(project, lang)
    variable, values = labels_of(project / "output" / f"merged.{fmt}")
    assert variable["tenure5"] == "Housing tenure of the family home"
    assert variable["quote5"].startswith('Mother said "fine"')
    assert variable["PID"] == "Identifier: every file is merged on this"
    assert {int(k): v for k, v in values["tenure5"].items()} == {
        1: "Owned",
        2: "Rented",
        -1: "Not applicable",
    }
    assert "weight10" not in values


@pytest.mark.needs_r
@pytest.mark.parametrize("lang", ["r", "python"])
def test_settings_at_the_top_change_behaviour_without_regenerating(tmp_path, lang):
    project = generate(tmp_path / lang, langs=lang)
    write_data(fabricate(), project / "elsewhere", "csv")
    script = project / ("R/merge.R" if lang == "r" else "python/merge.py")
    text = script.read_text()
    if lang == "r":
        text = text.replace('DATA_DIR <- "data"', 'DATA_DIR <- "elsewhere"')
        text = text.replace('OUTPUT_FORMAT <- "csv"', 'OUTPUT_FORMAT <- "dta"')
        text = text.replace("MISSING_TO_NA <- FALSE", "MISSING_TO_NA <- TRUE")
    else:
        text = text.replace('HERE.parent / "data"', 'HERE.parent / "elsewhere"')
        text = text.replace('OUTPUT_FORMAT = "csv"', 'OUTPUT_FORMAT = "dta"')
        text = text.replace("MISSING_TO_NA = False", "MISSING_TO_NA = True")
    script.write_text(text)
    run_ok(project, lang)
    merged = read(project / "output" / "merged.dta")
    assert not (merged["mood10"] == -8).any()


def test_rendered_python_passes_ruff(tmp_path):
    project = generate(tmp_path / "py", langs="python", fmt="sav", missing=True)
    done = subprocess.run(
        [
            str(RUFF),
            "check",
            "--isolated",
            "--no-cache",
            "--line-length",
            "100",
            "--select",
            "E,F,W,I,B,UP,SIM,D",
            "--config",
            "lint.pydocstyle.convention='google'",
            str(project / "python"),
        ],
        capture_output=True,
        text=True,
    )
    assert done.returncode == 0, done.stdout + done.stderr


def test_driver_refuses_unselectable_variables(tmp_path):
    done = subprocess.run(
        [
            "node",
            str(DRIVER),
            str(FIXTURE),
            "mini",
            str(tmp_path),
            "false",
            "csv",
            "r",
            "mini_noid:areacode",
        ],
        capture_output=True,
        text=True,
    )
    assert done.returncode != 0
    assert shutil.which("node")
