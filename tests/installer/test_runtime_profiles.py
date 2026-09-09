from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def read(name: str) -> str:
    return (ROOT / name).read_text(encoding="utf-8")


def test_runtime_profile_reference_exists_and_names_both_profiles():
    text = read("references/runtime-profiles.md")
    assert "## standalone" in text
    assert "## oai-native" in text
    assert "portable-openai" not in text


def test_root_skill_makes_standalone_canonical_without_external_process_dependency():
    text = read("SKILL.md")
    assert "standalone" in text.lower()
    assert "package-owned" in text.lower()
    assert "Superpowers" not in text


def test_native_profile_is_optional_enhancement_only():
    text = read("references/runtime-profiles.md")
    native = text.split("## oai-native", 1)[1]
    assert "optional enhancement" in native.lower()
    assert "may NEVER alter" in native
    assert "/home/oai/skills" not in native


def test_standalone_profile_owns_extractors_and_process_modules():
    text = read("references/runtime-profiles.md")
    standalone = text.split("## standalone", 1)[1].split("## oai-native", 1)[0]
    for token in ("PDF/DOCX/HTML/Markdown", "planning-document-traversal", "executing-document-traversal", "debugging-document-workflows", "recovering-document-workflows", "verifying-exhaustive-traversal"):
        assert token in standalone
    assert "No external process framework is required" in standalone


def test_pdf_and_docx_references_route_by_profile():
    assert "document profile" in read("references/pdf.md").lower()
    assert "document profile" in read("references/docx.md").lower()
