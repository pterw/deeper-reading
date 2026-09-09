import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))
from verify_run import build_dod, validate_run
from run_fixture import valid_run
from test_extractors import _write_minimal_docx


def test_evidence_file_cannot_escape_run_root_evidence_dir(tmp_path):
    run = valid_run(tmp_path)
    outside = tmp_path.parent / "format-qa-outside.md"
    outside.write_text("qa\n", encoding="utf-8")
    run["evidence"]["format_qa"] = str(outside)
    errors = validate_run(run)
    assert any("evidence.format_qa must live under <run-root>/evidence" in e for e in errors)


def test_deliverable_file_cannot_escape_run_root_deliverables_dir(tmp_path):
    run = valid_run(tmp_path)
    outside = tmp_path / "answer.txt"
    outside.write_text("answer\n", encoding="utf-8")
    run["deliverable"]["paths"] = [str(outside)]
    errors = validate_run(run)
    assert any("deliverable path must live under <run-root>/deliverables" in e for e in errors)


def test_chunk_manifest_and_traversal_report_have_canonical_run_paths(tmp_path):
    run = valid_run(tmp_path)
    wrong_manifest = tmp_path / "chunks.json"
    shutil.copy2(tmp_path / "evidence" / "chunk-manifest.json", wrong_manifest)
    wrong_report = tmp_path / "TRAVERSAL_REPORT.md"
    shutil.copy2(tmp_path / "deliverables" / "TRAVERSAL_REPORT.md", wrong_report)
    run["chunking"]["manifest"] = "chunks.json"
    run["chunking"]["traversal_report"] = "TRAVERSAL_REPORT.md"
    run["evidence"]["traversal_report"] = "TRAVERSAL_REPORT.md"
    run["deliverable"]["traversal_report"] = "TRAVERSAL_REPORT.md"
    errors = validate_run(run)
    assert any("chunking.manifest must be <run-root>/evidence/chunk-manifest.json" in e for e in errors)
    assert any("chunking.traversal_report must be <run-root>/deliverables/TRAVERSAL_REPORT.md" in e for e in errors)


@pytest.mark.parametrize(
    "script_name,source_name,source_bytes",
    [
        ("extract_markdown.py", "source.md", b"# H\n\nalpha\n"),
        ("extract_html.py", "source.html", b"<h1>H</h1><p>alpha</p>"),
    ],
)
def test_text_extractors_support_canonical_run_root_output(tmp_path, script_name, source_name, source_bytes):
    source = tmp_path / source_name
    source.write_bytes(source_bytes)
    run_root = tmp_path / "run"
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / script_name), str(source), "--run-root", str(run_root)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert (run_root / "evidence" / "chunk-manifest.json").is_file()
    assert not (run_root / "chunk-manifest.json").exists()


def test_docx_extractor_supports_canonical_run_root_output(tmp_path):
    source = tmp_path / "source.docx"
    _write_minimal_docx(source)
    run_root = tmp_path / "run"
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / "extract_docx.py"), str(source), "--run-root", str(run_root)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert (run_root / "evidence" / "chunk-manifest.json").is_file()


def test_traversal_report_supports_canonical_run_root_output(tmp_path):
    legacy_root = tmp_path / "legacy"
    legacy_root.mkdir()
    run = valid_run(legacy_root)
    run_root = tmp_path / "canonical"
    evidence_dir = run_root / "evidence"
    evidence_dir.mkdir(parents=True)
    shutil.copy2(legacy_root / run["chunking"]["manifest"], evidence_dir / "chunk-manifest.json")
    shutil.copy2(legacy_root / run["chunking"]["evidence_ledger"], evidence_dir / "chunk-evidence.json")
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / "traversal_report.py"), "--run-root", str(run_root)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert (run_root / "deliverables" / "TRAVERSAL_REPORT.md").is_file()


def test_verifier_rejects_noncanonical_dod_output(tmp_path):
    run = valid_run(tmp_path)
    ledger = tmp_path / "run.json"
    ledger.write_text(json.dumps(run), encoding="utf-8")
    outside = tmp_path.parent / "dod-outside.json"
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / "verify_run.py"), str(ledger), "--write-dod", str(outside)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert "dod.json must be written to <run-root>/dod.json" in (result.stdout + result.stderr)


def test_dod_exposes_output_containment_predicate(tmp_path):
    run = valid_run(tmp_path)
    errors = validate_run(run)
    dod = build_dod(run, errors)
    assert dod["predicates"]["output_containment_valid"] is True

    outside = tmp_path.parent / "qa-outside.md"
    outside.write_text("qa\n", encoding="utf-8")
    run["evidence"]["format_qa"] = str(outside)
    errors = validate_run(run)
    dod = build_dod(run, errors)
    assert dod["predicates"]["output_containment_valid"] is False
