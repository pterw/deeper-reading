from pathlib import Path

from installer.prerequisites import BUNDLED_EXTRACTORS, document_profile_status


def _bundle(root: Path):
    scripts = root / "scripts"
    scripts.mkdir(parents=True)
    for name in BUNDLED_EXTRACTORS:
        (scripts / name).write_text("# extractor\n", encoding="utf-8")


def test_standalone_ready_when_bundled_extractors_exist(tmp_path):
    _bundle(tmp_path)
    status = document_profile_status("standalone", package_root=tmp_path)
    assert status.state == "ready"
    assert len(status.evidence) == 4


def test_standalone_fails_closed_when_bundled_extractor_missing(tmp_path):
    _bundle(tmp_path)
    (tmp_path / "scripts" / "extract_pdf.py").unlink()
    status = document_profile_status("standalone", package_root=tmp_path)
    assert status.state == "missing"
    assert any("extract_pdf.py" in item for item in status.evidence)


def test_oai_native_is_optional_and_requires_live_skill_roots(tmp_path):
    pdf = tmp_path / "pdfs"
    docx = tmp_path / "docx"
    pdf.mkdir(); docx.mkdir()
    (pdf / "SKILL.md").write_text("pdf", encoding="utf-8")
    (docx / "SKILL.md").write_text("docx", encoding="utf-8")
    status = document_profile_status("oai-native", native_pdf=pdf, native_docx=docx)
    assert status.state == "ready"
    assert any("does-not-alter-anti-skimming-contract" in item for item in status.evidence)


def test_unknown_profile_is_unsupported(tmp_path):
    status = document_profile_status("unknown", package_root=tmp_path)
    assert status.state == "unsupported"
