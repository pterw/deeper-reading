from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_control_flow_routes_through_package_owned_modules():
    text = read("references/control-flow.md")
    assert "planning-document-traversal" in text
    assert "executing-document-traversal" in text
    assert "Superpowers" not in text


def test_anti_patterns_use_package_native_failure_vocabulary():
    text = read("references/anti-patterns.md")
    assert "failure_diagnosed" in text
    assert "alternative_designed" in text
    assert "Superpowers" not in text


def test_root_required_reading_names_dependencies_portably():
    text = read("SKILL.md")
    assert "[Live OAI dependencies]" not in text
    required = text.split("## Required reading", 1)[1] if "## Required reading" in text else text
    assert "dependencies.md" in required
