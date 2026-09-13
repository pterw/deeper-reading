from scripts.verification_findings import Finding, codes_of, group_by_predicate


def test_finding_is_frozen_and_carries_all_four_fields():
    f = Finding("source.uri.required", "source_identity_verified",
                "source.uri is required")
    assert f.code == "source.uri.required"
    assert f.predicate == "source_identity_verified"
    assert f.message == "source.uri is required"
    assert f.detail == ""


def test_codes_of_preserves_order_and_grouping_is_by_predicate():
    findings = [
        Finding("source.uri.required", "source_identity_verified", "a"),
        Finding("plan.path.required", "plan_present", "b"),
        Finding("qa.missing", "format_qa_complete", "c", detail="markdown-q"),
    ]
    assert codes_of(findings) == ["source.uri.required", "plan.path.required",
                                  "qa.missing"]
    grouped = group_by_predicate(findings)
    assert set(grouped) == {"source_identity_verified", "plan_present",
                            "format_qa_complete"}
    assert grouped["plan_present"][0].code == "plan.path.required"


def test_finding_by_code_raises_when_absent():
    import pytest

    from scripts.verification_findings import Finding, finding_by_code

    with pytest.raises(LookupError):
        finding_by_code([Finding("a.b", "machine_checks_passed", "m")], "x.y")


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


def test_invalid_source_format_emits_its_code():
    from scripts.verification_findings import finding_by_code
    from scripts.verify_run import validate_findings

    run = _base_run()
    run["source"]["format"] = "epub"
    f = finding_by_code(validate_findings(run), "source.format.invalid")
    assert f.predicate == "source_identity_verified"
    assert f.message == "source.format must be html, pdf, docx, or markdown"


def test_false_preflight_emits_the_key_code():
    from scripts.verification_findings import finding_by_code
    from scripts.verify_run import validate_findings

    run = _base_run()
    run["preflight"]["traversal_plan_ready"] = False
    f = finding_by_code(validate_findings(run),
                        "preflight.traversal_plan_ready.false")
    assert f.detail == "traversal_plan_ready"
    assert f.message == "preflight.traversal_plan_ready must be true"