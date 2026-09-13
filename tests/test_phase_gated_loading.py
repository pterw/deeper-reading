from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ROOT_SKILL = (ROOT / "SKILL.md").read_text(encoding="utf-8")

MODULES = {
    "exhaustive": ROOT / "skills" / "exhaustive-document-traversal" / "SKILL.md",
    "planning": ROOT / "skills" / "planning-document-traversal" / "SKILL.md",
    "execution": ROOT / "skills" / "executing-document-traversal" / "SKILL.md",
    "debugging": ROOT / "skills" / "debugging-document-workflows" / "SKILL.md",
    "recovery": ROOT / "skills" / "recovering-document-workflows" / "SKILL.md",
    "verification": ROOT / "skills" / "verifying-exhaustive-traversal" / "SKILL.md",
}


def read_module(name: str) -> str:
    return MODULES[name].read_text(encoding="utf-8")


def section(body: str, heading: str) -> str:
    marker = f"{heading}\n"
    start = body.index(marker) + len(marker)
    end = body.find("\n## ", start)
    return body[start:] if end == -1 else body[start:end]


def test_root_routes_lifecycle_modules_without_a_reference_bundle() -> None:
    routing = section(ROOT_SKILL, "## Phase-gated loading")
    assert "Read these in full when this skill activates" not in ROOT_SKILL
    for path in MODULES.values():
        relative = path.relative_to(ROOT).as_posix()
        assert relative in routing
    assert "references/" not in routing


def test_planning_module_owns_planning_inputs() -> None:
    body = read_module("planning")
    assert "../../references/deliverable.md" in body
    assert "../../references/definition-of-done.md" in body
    assert "../../references/evidence.md" not in body
    assert "../../references/failure-recovery.md" not in body


def test_exhaustive_module_owns_all_four_format_routes() -> None:
    body = read_module("exhaustive")
    for reference in (
        "../../references/prerequisites.md",
        "../../references/runtime-profiles.md",
        "../../references/control-flow.md",
        "../../references/source-acquisition.md",
        "../../references/dependencies.md",
        "../../references/pdf.md",
        "../../references/docx.md",
        "../../references/html.md",
        "../../references/lengthy-markdown.md",
    ):
        assert reference in body
    for helper in (
        "../../scripts/extract_pdf.py",
        "../../scripts/extract_docx.py",
        "../../scripts/extract_html.py",
        "../../scripts/extract_markdown.py",
    ):
        assert helper in body
    assert "selected format" in body.lower()
    assert "only for large markdown" in body.lower()


def test_execution_and_failure_modules_own_later_inputs() -> None:
    execution = read_module("execution")
    debugging = read_module("debugging")
    recovery = read_module("recovery")
    assert "../../references/evidence.md" in execution
    assert "../../references/anti-patterns.md" in execution
    assert "../../references/failure-recovery.md" in debugging
    assert "after a node fails" in debugging.lower()
    assert "../../references/failure-recovery.md" in recovery
    assert "before alternative design" in recovery.lower()


def test_verification_module_owns_fresh_completion_inputs() -> None:
    body = read_module("verification")
    assert "../../references/definition-of-done.md" in body
    assert "../../references/evidence.md" in body
    assert "../../scripts/verify_run.py" in body
    assert "--help" in body


def test_skill_preflight_records_phase_receipts() -> None:
    prerequisites = (ROOT / "references" / "prerequisites.md").read_text(
        encoding="utf-8"
    )
    evidence = (ROOT / "references" / "evidence.md").read_text(encoding="utf-8")
    done = (ROOT / "references" / "definition-of-done.md").read_text(
        encoding="utf-8"
    )
    for body in (prerequisites, evidence, done):
        assert "reference path" in body.lower()
        assert "required gate" in body.lower()
        assert "completed" in body.lower()
