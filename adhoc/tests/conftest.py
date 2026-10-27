import sys
from pathlib import Path

# The ad hoc scripts are run as plain files, not installed; import them from their folder.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
