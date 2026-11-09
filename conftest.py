"""Put the skill folder and tests/ on sys.path so tests import the bundled modules."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SKILL_ROOT = ROOT / "skills" / "deeper-reading"

for entry in (SKILL_ROOT, ROOT / "tests"):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))
