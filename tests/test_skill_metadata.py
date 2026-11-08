from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

SHARED_SKILLS = ("security-review", "shipping-a-change")


def _frontmatter_lines(path):
    lines = path.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "---", path
    return lines[1 : lines.index("---", 1)]


def _metadata(lines):
    """Return the indented `key: value` pairs under a top-level `metadata:` key."""
    if "metadata:" not in lines:
        return {}
    pairs = {}
    for line in lines[lines.index("metadata:") + 1 :]:
        if not line.startswith((" ", "\t")):
            break
        key, _, value = line.strip().partition(":")
        pairs[key] = value.strip()
    return pairs


@pytest.mark.parametrize("name", SHARED_SKILLS)
def test_repository_working_skill_is_internal(name):
    path = ROOT / ".github" / "skills" / name / "SKILL.md"
    assert _metadata(_frontmatter_lines(path)).get("internal") == "true", path
