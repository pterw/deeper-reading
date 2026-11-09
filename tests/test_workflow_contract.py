
from layout import SKILL_ROOT
SKILL = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")


def test_skill_has_quick_path_to_done():
    assert "## Quick path" in SKILL
    assert "START" in SKILL
    assert "DEFINITION OF DONE" in SKILL


def test_skill_links_terminal_contracts():
    assert "references/deliverable.md" in SKILL
    assert "references/definition-of-done.md" in SKILL
    assert "references/evidence.md" in SKILL
