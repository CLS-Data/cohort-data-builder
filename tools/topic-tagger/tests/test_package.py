import subprocess
import sys

import topic_tagger


def test_the_version_agrees_with_pyproject():
    import tomllib
    from pathlib import Path

    pyproject = Path(__file__).parents[1] / "pyproject.toml"
    project = tomllib.loads(pyproject.read_text(encoding="utf-8"))["project"]
    assert project["version"] == topic_tagger.__version__


def test_it_runs_as_a_module():
    done = subprocess.run([sys.executable, "-m", "topic_tagger", "--help"], capture_output=True)
    assert done.returncode == 0


def test_the_example_schemes_are_packaged_and_load(tmp_path):
    from importlib import resources

    from topic_tagger.scheme import load_scheme

    schemes = resources.files("topic_tagger") / "schemes"
    for name, tiers in (("example-1-tier.toml", 1), ("example-3-tier.toml", 3)):
        path = tmp_path / name
        path.write_text((schemes / name).read_text(encoding="utf-8"), encoding="utf-8")
        scheme = load_scheme(path)
        assert scheme.tiers == tiers
    three = load_scheme(tmp_path / "example-3-tier.toml")
    assert three.questions and three.run is not None
    # uneven: a leaf sits beside groups below tier 1
    assert any(c.is_leaf for g in three.root.children for c in g.children) and any(
        not c.is_leaf for g in three.root.children for c in g.children
    )
