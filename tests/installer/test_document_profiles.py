from pathlib import Path

from installer.prerequisites import BUNDLED_EXTRACTORS, document_profile_status


def test_standalone_ready_from_package_owned_extractors(tmp_path):
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    for name in BUNDLED_EXTRACTORS:
        (scripts / name).write_text("# extractor\n", encoding="utf-8")
    status = document_profile_status("standalone", package_root=tmp_path)
    assert status.state == "ready"


def test_standalone_missing_extractor_fails_closed(tmp_path):
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    for name in BUNDLED_EXTRACTORS[:-1]:
        (scripts / name).write_text("# extractor\n", encoding="utf-8")
    status = document_profile_status("standalone", package_root=tmp_path)
    assert status.state == "missing"


def test_oai_native_ready_when_internal_skill_roots_exist(tmp_path):
    pdf = tmp_path / "pdf"; docx = tmp_path / "docx"
    pdf.mkdir(); docx.mkdir()
    (pdf / "SKILL.md").write_text("pdf", encoding="utf-8")
    (docx / "SKILL.md").write_text("docx", encoding="utf-8")
    status = document_profile_status("oai-native", native_pdf=pdf, native_docx=docx)
    assert status.state == "ready"


def test_oai_native_fails_closed_when_internal_root_missing(tmp_path):
    status = document_profile_status("oai-native", native_pdf=tmp_path / "missing-pdf", native_docx=tmp_path / "missing-docx")
    assert status.state == "missing"


def test_unknown_document_profile_is_unsupported(tmp_path):
    status = document_profile_status("nonsense", package_root=tmp_path)
    assert status.state == "unsupported"
