from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

CASES = [
    ("exhaustive-document-traversal", ("every canonical chunk", "evidence", "non_match", "premature")),
    ("planning-document-traversal", ("traversal plan", "bounded", "verification")),
    ("executing-document-traversal", ("one bounded", "chunk_verified", "failed")),
    ("debugging-document-workflows", ("failure_diagnosed", "before", "sibling")),
    ("recovering-document-workflows", ("paths_exhausted", "disclosure", "alternative_designed", "plan_revised")),
    ("verifying-exhaustive-traversal", ("re-extract", "canonical chunk", "TRAVERSAL_REPORT.md", "done")),
]


@pytest.mark.parametrize(("name", "required"), CASES)
def test_package_owned_process_skill_contract(name, required):
    path = ROOT / "skills" / name / "SKILL.md"
    assert path.is_file(), path
    text = path.read_text(encoding="utf-8")
    assert f"name: {name}" in text
    assert "description: Use when" in text
    lowered = text.lower()
    for phrase in required:
        assert phrase.lower() in lowered, (name, phrase)
    assert "superpowers:" not in lowered
    assert "@superpowers" not in lowered
