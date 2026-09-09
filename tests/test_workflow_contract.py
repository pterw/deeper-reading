from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = (ROOT / "SKILL.md").read_text(encoding="utf-8")


def test_skill_has_quick_path_to_done():
    assert "## Quick path" in SKILL
    assert "START" in SKILL
    assert "DEFINITION OF DONE" in SKILL


def test_skill_links_terminal_contracts():
    assert "references/deliverable.md" in SKILL
    assert "references/definition-of-done.md" in SKILL
    assert "references/evidence.md" in SKILL


def test_terminal_contract_references_exist():
    for rel in [
        "references/deliverable.md",
        "references/definition-of-done.md",
        "references/evidence.md",
    ]:
        assert (ROOT / rel).is_file(), rel


def test_executable_run_verifier_exists():
    assert (ROOT / "scripts/verify_run.py").is_file()


def test_mutation_tests_exist():
    assert (ROOT / "tests/test_mutations.py").is_file()
