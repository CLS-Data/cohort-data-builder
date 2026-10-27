import subprocess
import sys

import topic_tagger


def test_the_package_has_a_version():
    assert topic_tagger.__version__ == "0.1.0"


def test_it_runs_as_a_module():
    done = subprocess.run([sys.executable, "-m", "topic_tagger", "--help"], capture_output=True)
    assert done.returncode == 0
