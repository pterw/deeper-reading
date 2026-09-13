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