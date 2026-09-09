from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")

def test_root_declares_exhaustive_traversal_as_product():
    text = read("SKILL.md")
    assert "Chunking is the mechanism" in text
    assert "exhaustive traversal" in text.lower()

def test_root_routes_through_package_owned_process_skills():
    text = read("SKILL.md")
    for name in (
        "planning-document-traversal",
        "executing-document-traversal",
        "debugging-document-workflows",
        "recovering-document-workflows",
        "verifying-exhaustive-traversal",
    ):
        assert name in text

def test_root_default_profile_is_standalone():
    text = read("SKILL.md")
    assert "standalone" in text
    assert "oai-native" in text
    assert text.index("standalone") < text.index("oai-native")

def test_prerequisites_are_package_native():
    text = read("references/prerequisites.md")
    assert "package-owned" in text
    assert "Superpowers" not in text
    assert "traversal_plan_ready" in text

def test_control_flow_uses_native_failure_and_recovery_states():
    text = read("references/control-flow.md")
    for token in ("failure_diagnosed", "architecture_stop", "paths_exhausted", "alternative_designed", "plan_revised"):
        assert token in text
    assert "systematic-debugging" not in text
    assert "brainstorming" not in text

def test_runtime_profiles_define_standalone_default_and_optional_oai_native():
    text = read("references/runtime-profiles.md")
    assert "## standalone" in text
    assert "## oai-native" in text
    assert "optional enhancement" in text.lower()

def test_failure_recovery_is_package_owned():
    text = read("references/failure-recovery.md")
    assert "failure_diagnosed" in text
    assert "alternative_designed" in text
    assert "Superpowers" not in text
