"""The tool stands on its own: it depends on nothing in the repository around it (SC-006)."""

import ast
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
ALLOWED = {"openai", "pydantic", "rich", "langchain_core", "topic_tagger"}


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names = {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    names |= {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.level == 0}
    return {n.split(".")[0] for n in names}


def test_the_code_imports_only_the_standard_library_and_its_dependencies():
    outside = {
        f"{p.relative_to(ROOT)}: {name}"
        for p in (ROOT / "src").rglob("*.py")
        for name in _imports(p)
        if name not in ALLOWED and name not in sys.stdlib_module_names
    }
    assert outside == set()


def test_no_file_refers_to_a_path_outside_the_tool():
    hits = []
    for p in [*(ROOT / "src").rglob("*.py"), *(ROOT / "tests").rglob("*.py")]:
        if p.name == "test_independence.py":
            continue
        for n, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            if any(s in line for s in ("../", "site/", "PoC", "scripts/")):
                hits.append(f"{p.relative_to(ROOT)}:{n}: {line.strip()}")
    assert hits == []


@pytest.mark.skipif(shutil.which("uv") is None, reason="needs uv")
def test_a_copy_outside_the_repository_passes_its_tests(tmp_path):
    copy = tmp_path / "topic-tagger"
    shutil.copytree(
        ROOT,
        copy,
        ignore=shutil.ignore_patterns(".venv", "__pycache__", ".pytest_cache", ".ruff_cache"),
    )
    run = subprocess.run(
        ["uv", "run", "--offline", "pytest", "-q", "-k", "not independence"],
        cwd=copy,
        capture_output=True,
        text=True,
        timeout=600,
    )
    assert run.returncode == 0, run.stdout[-2000:] + run.stderr[-2000:]
