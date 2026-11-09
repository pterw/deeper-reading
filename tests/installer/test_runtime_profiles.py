import pytest

from layout import SKILL_ROOT


def read(name: str) -> str:
    return (SKILL_ROOT / name).read_text(encoding="utf-8")


def test_runtime_profile_reference_exists_and_names_both_profiles():
    text = read("references/runtime-profiles.md")
    assert "## standalone" in text
    assert "## oai-native" in text
    assert "portable-openai" not in text


def test_native_profile_is_optional_enhancement_only():
    text = read("references/runtime-profiles.md")
    native = text.split("## oai-native", 1)[1]
    assert "optional enhancement" in native.lower()
    assert "may NEVER alter" in native


def _skill_prose_files():
    return [SKILL_ROOT / "SKILL.md", *SKILL_ROOT.glob("skills/*/SKILL.md"), *SKILL_ROOT.glob("references/*.md")]


@pytest.mark.parametrize("path", _skill_prose_files(), ids=lambda p: p.relative_to(SKILL_ROOT).as_posix())
def test_host_skill_path_appears_only_in_the_oai_native_reference(path):
    assert list(SKILL_ROOT.glob("skills/*/SKILL.md")), "skills glob matched nothing"
    assert list(SKILL_ROOT.glob("references/*.md")), "references glob matched nothing"
    assert ("/home/oai/skills" in path.read_text(encoding="utf-8")) == (path.name == "oai-native.md")


def test_standalone_profile_owns_extractors_and_process_modules():
    text = read("references/runtime-profiles.md")
    standalone = text.split("## standalone", 1)[1].split("## oai-native", 1)[0]
    for token in ("PDF/DOCX/HTML/Markdown", "planning-document-traversal", "executing-document-traversal", "debugging-document-workflows", "recovering-document-workflows", "verifying-exhaustive-traversal"):
        assert token in standalone
    assert "No external process framework is required" in standalone


def test_pdf_and_docx_references_route_by_profile():
    assert "document profile" in read("references/pdf.md").lower()
    assert "document profile" in read("references/docx.md").lower()
