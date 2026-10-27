import ast
from pathlib import Path

ROOT = Path(__file__).parents[3]


def test_the_script_imports_nothing_from_the_tool():
    tree = ast.parse((ROOT / "scripts" / "topics.py").read_text(encoding="utf-8"))
    names = [a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names]
    names += [n.module or "" for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)]
    assert not [n for n in names if n.split(".")[0] in {"tools", "topic_tagger"}]


def test_the_site_does_not_refer_to_the_tool():
    site = ROOT / "site"
    hits = [
        str(p.relative_to(ROOT))
        for p in site.rglob("*")
        if p.is_file()
        and p.suffix in {".html", ".js", ".css", ".json", ".md"}
        and "data" not in p.relative_to(site).parts[:1]
        and "tools/" in p.read_text(encoding="utf-8", errors="ignore")
    ]
    assert hits == []
