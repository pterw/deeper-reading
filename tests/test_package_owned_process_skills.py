import pytest

from layout import SKILL_ROOT

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
    path = SKILL_ROOT / "modules" / f"{name}.md"
    assert path.is_file(), path
    text = path.read_text(encoding="utf-8")
    assert not text.startswith("---"), "a module has no YAML frontmatter"
    lowered = text.lower()
    for phrase in required:
        assert phrase.lower() in lowered, (name, phrase)


def test_only_the_root_is_named_skill_md_and_modules_resolve_from_the_root():
    assert [p for p in SKILL_ROOT.rglob("SKILL.md")] == [SKILL_ROOT / "SKILL.md"]
    for name, _ in CASES:
        text = (SKILL_ROOT / "modules" / f"{name}.md").read_text(encoding="utf-8")
        assert "../" not in text, name
