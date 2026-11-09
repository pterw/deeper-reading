import pytest

from layout import SKILL_ROOT

def read(rel):
    return (SKILL_ROOT / rel).read_text(encoding="utf-8")

def test_root_default_profile_is_standalone():
    text = read("SKILL.md")
    assert "standalone" in text
    assert "oai-native" in text
    assert text.index("standalone") < text.index("oai-native")

def test_prerequisites_are_package_native():
    text = read("references/prerequisites.md")
    assert "package-owned" in text
    assert "traversal_plan_ready" in text

def test_failure_recovery_owns_the_native_failure_and_recovery_states():
    text = read("references/failure-recovery.md")
    for token in ("failure_diagnosed", "architecture_stop", "paths_exhausted", "alternative_designed", "plan_revised"):
        assert token in text


@pytest.mark.parametrize("needle", ["systematic-debugging", "invoke systematic debugging", "brainstorm alternatives"])
def test_no_prose_hands_a_failure_to_a_foreign_skill(needle):
    files = [SKILL_ROOT / "SKILL.md", *SKILL_ROOT.glob("modules/*.md"), *SKILL_ROOT.glob("references/*.md")]
    assert list(SKILL_ROOT.glob("modules/*.md")), "modules glob matched nothing"
    assert len(files) > 2
    assert [f.name for f in files if needle in f.read_text(encoding="utf-8")] == []


def test_root_docs_do_not_overclaim_evidence_semantics():
    skill = read("SKILL.md").lower()
    evidence = read("references/evidence.md").lower()
    assert "semantic truth" in skill or "semantic truth" in evidence
    assert "model comprehension" in skill or "model comprehension" in evidence
