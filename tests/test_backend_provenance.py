import pytest

from scripts.verification_findings import codes_of, finding_by_code
from scripts.verify_run import validate_findings


def _base_run():
    return {
        "source": {"uri": "u", "format": "markdown", "authority": "primary",
                   "identity_verified": True},
        "fidelity": {"preserved": True, "substitutions": []},
        "preflight": {k: True for k in (
            "skill_read", "required_references_read", "helper_help_read",
            "runtime_profile_resolved", "traversal_plan_ready")},
        "plan": {"path": "plan.md", "nodes": ["n1"]},
        "deliverable": {"requested": "r", "provided": True,
                        "traversal_report": "deliverables/TRAVERSAL_REPORT.md",
                        "paths": []},
        "chunking": {"manifest": "evidence/chunk-manifest.json",
                     "manifest_sha256": "x",
                     "evidence_ledger": "evidence/chunk-evidence.json",
                     "traversal_report": "deliverables/TRAVERSAL_REPORT.md"},
        "qa": {"required": [], "passed": []},
        "evidence": {k: "evidence/f.md" for k in (
            "plan_status", "skill_preflight", "source_manifest", "chunk_ledger",
            "failure_ledger", "verification_log", "format_qa",
            "traversal_report")},
        "events": [{"type": "plan_written"}, {"type": "execution_started"}],
    }


def test_pdf_run_without_backend_provenance_is_a_violation():
    run = _base_run()
    run["source"]["format"] = "pdf"
    f = finding_by_code(validate_findings(run), "extraction.backend.missing")
    assert f.detail == "pdf"
    assert f.predicate == "format_qa_complete"
    assert f.message == "extraction.backend is required for pdf runs"


def test_markdown_run_does_not_require_backend_provenance():
    run = _base_run()
    assert "extraction.backend.missing" not in codes_of(validate_findings(run))


def test_declared_qa_must_match_recorded_backend():
    run = _base_run()
    run["source"]["format"] = "pdf"
    run["extraction"] = {"backend": "pypdf 5.6", "format": "pdf",
                         "capabilities": ["text"]}
    run["qa"] = {"required": ["ocr-verified"], "passed": ["ocr-verified"]}
    assert finding_by_code(validate_findings(run), "extraction.qa.mismatch")


def test_passed_ocr_claim_cannot_bypass_capability_check():
    run = _base_run()
    run['source']['format'] = 'pdf'
    run['extraction'] = {'backend':'pypdf 5.3.0','format':'pdf','capabilities':['text']}
    run['qa'] = {'required':[], 'passed':['ocr-verified']}
    assert finding_by_code(validate_findings(run), 'extraction.qa.mismatch')
