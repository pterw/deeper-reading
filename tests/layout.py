"""The repository layout the tests rely on, stated rather than read from the manifest."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = ROOT / "skills" / "deeper-reading"
