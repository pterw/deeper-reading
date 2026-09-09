from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


def test_prerequisites_resolve_initial_brainstorming_order():
    text = read("references/prerequisites.md")
    assert "user-approved orchestration" in text.lower()
    assert "already-brainstormed" in text.lower()
    assert "novel design" in text.lower()


def test_prerequisites_resolve_non_repo_executing_plans_lifecycle():
    text = read("references/prerequisites.md")
    assert "document-run" in text
    assert "not_applicable" in text
    assert "do not create a git repository" in text.lower()


def test_document_plan_location_and_shape_are_explicit():
    text = read("references/control-flow.md")
    assert "<run-root>/plan.md" in text
    assert "document-specific" in text.lower()


def test_source_acquisition_says_one_recovery_branch_at_a_time():
    text = read("references/source-acquisition.md")
    assert "one recovery branch at a time" in text.lower()


def test_failure_recovery_honors_systematic_debugging_architecture_stop():
    text = read("references/failure-recovery.md")
    assert "three" in text.lower() or "3" in text
    assert "fourth fix" in text.lower()


def test_evidence_bundle_names_are_consistent():
    deliverable = read("references/deliverable.md")
    evidence = read("references/evidence.md")
    dod = read("references/definition-of-done.md")
    assert "skill-preflight.md" in deliverable
    assert "format-qa.md" in deliverable
    assert "skill-preflight.md" in evidence
    assert '"skill_preflight": "evidence/skill-preflight.md"' in evidence
    assert "skill-preflight.md" in dod
