import re

import pytest

from layout import SKILL_ROOT
from scripts.verification_findings import Finding, codes_of, group_by_predicate
from tests.run_fixture import valid_run


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


def test_every_finding_literal_has_one_predicate_from_predicates():
    """Structural coverage from source, not proof that each branch executes."""
    import ast
    from scripts.verification_findings import PREDICATES
    from scripts.verify_run import REQUIRED_EVIDENCE, REQUIRED_PREFLIGHT
    tree = ast.parse((SKILL_ROOT / 'scripts/verify_run.py').read_text(encoding="utf-8"))
    owner = {}
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'Finding'):
            continue
        code, predicate = node.args[:2]
        if isinstance(code, ast.Constant):
            codes = [code.value]
        else:
            template = ''.join(part.value if isinstance(part, ast.Constant) else '{key}' for part in code.values)
            keys = REQUIRED_PREFLIGHT if template.startswith('preflight.') else REQUIRED_EVIDENCE
            codes = [template.format(key=key) for key in keys]
        assert predicate.value in PREDICATES, predicate.value
        for c in codes:
            assert owner.setdefault(c, predicate.value) == predicate.value, c
    assert owner


def test_finding_rejects_an_unknown_predicate():
    import pytest

    with pytest.raises(ValueError):
        Finding("x", "not_a_predicate", "m")


def test_dod_predicate_keys_are_predicates_plus_the_deliverable_alias(tmp_path):
    from scripts.verification_findings import PREDICATES
    from scripts.verify_run import build_dod, validate_findings

    passing = valid_run(tmp_path)
    passing["_ledger_path"] = str(tmp_path / "run.json")
    failing = valid_run(tmp_path)
    failing["_ledger_path"] = str(tmp_path / "run.json")
    failing["deliverable"]["provided"] = False
    for run, expected in ((passing, True), (failing, False)):
        predicates = build_dod(run, validate_findings(run))["predicates"]
        assert set(predicates) == set(PREDICATES) | {"deliverable_provided"}
        assert predicates["deliverable_provided"] is predicates["requested_deliverable_produced"]
        assert predicates["requested_deliverable_produced"] is expected


def _documented_events(prefix):
    text = (SKILL_ROOT / "references/evidence.md").read_text(encoding="utf-8")
    line = next(ln for ln in text.splitlines() if ln.startswith(prefix))
    return re.findall(r"`(\w+)`", line)


_VOCABULARY = _documented_events("Core event vocabulary")
_MATERIAL = set(_documented_events("Material events"))


@pytest.mark.parametrize(
    "event",
    [e for e in _VOCABULARY if e not in {"verification_started", "verification_passed", "done"}],
)
def test_documented_material_events_are_the_ones_that_stale_verification(tmp_path, event):
    from scripts.verify_run import validate_findings

    run = valid_run(tmp_path)
    run["_ledger_path"] = str(tmp_path / "run.json")
    run["events"].insert(-1, {"type": event})
    stale = "done.verification.stale" in codes_of(validate_findings(run))
    assert stale is (event in _MATERIAL)


def _resolved_run(tmp_path):
    """A done-sealed run whose only gaps are the chunk files this table never builds."""
    run = _base_run()
    (tmp_path / "plan.md").write_text("plan", encoding="utf-8")
    (tmp_path / "evidence").mkdir()
    (tmp_path / "evidence" / "f.md").write_text("e", encoding="utf-8")
    run["_ledger_path"] = str(tmp_path / "run.json")
    run["events"] = [{"type": t} for t in (
        "plan_written", "execution_started")] + [
        {"type": "node_passed", "node": "n1"}] + [{"type": t} for t in (
        "verification_started", "verification_passed", "done")]
    return run


def _set(section, key, value):
    def mutate(run):
        run[section][key] = value
    return mutate


def _insert_events(*events):
    def mutate(run):
        run["events"][2:2] = list(events)
    return mutate


def _drop_event(type_):
    def mutate(run):
        run["events"] = [e for e in run["events"] if e["type"] != type_]
    return mutate


def _swap_first_two_events(run):
    run["events"][:2] = reversed(run["events"][:2])


def _E(type_):
    return {"type": type_}


_FINDING_ROWS = [
    (_set("source", "identity_verified", False), "source.identity.unverified", "source_identity_verified"),
    (_set("source", "authority", "blog"), "source.authority.invalid", "source_identity_verified"),
    (_set("source", "uri", ""), "source.uri.required", "source_identity_verified"),
    (_set("plan", "path", ""), "plan.path.required", "plan_present"),
    (_set("plan", "nodes", []), "plan.nodes.required", "plan_present"),
    (_set("deliverable", "requested", ""), "deliverable.requested.required", "requested_deliverable_produced"),
    (_set("deliverable", "provided", False), "deliverable.provided.required", "requested_deliverable_produced"),
    (_set("preflight", "skill_read", False), "preflight.skill_read.false", "skill_preflight_complete"),
    (_drop_event("execution_started"), "events.execution_started.missing", "plan_resolved"),
    (_swap_first_two_events, "events.execution.order", "plan_resolved"),
    (_insert_events(_E("architecture_stop"), _E("disclosure"), _E("paths_exhausted"), _E("alternative_designed")),
     "failure.protocol.alternative.order", "failure_protocol_respected"),
    (_insert_events(_E("plan_revised")), "failure.protocol.plan_revised", "failure_protocol_respected"),
    (_drop_event("node_passed"), "done.node.unresolved", "plan_resolved"),
    (_insert_events({"type": "node_failed", "node": "n2"}),
     "done.failure.unresolved", "no_unresolved_required_failures"),
    (_drop_event("verification_passed"), "done.verification_passed.missing", "fresh_final_verification"),
    (_set("fidelity", "preserved", False), "fidelity.preserved.required", "source_fidelity_preserved"),
    (_set("qa", "required", ["x"]), "qa.missing", "format_qa_complete"),
    (_set("evidence", "plan_status", ""), "evidence.plan_status.invalid", "evidence_complete"),
]


@pytest.mark.parametrize(
    ("mutate", "code", "predicate"), _FINDING_ROWS, ids=[r[1] for r in _FINDING_ROWS])
def test_a_broken_requirement_emits_its_code_and_fails_its_own_predicate(
        tmp_path, mutate, code, predicate):
    from scripts.verify_run import _build_dod_from_findings, validate_findings

    run = _resolved_run(tmp_path)
    base = _build_dod_from_findings(run, validate_findings(run))
    assert base["predicates"][predicate] is True, "row would be vacuous"

    mutate(run)
    findings = validate_findings(run)
    assert code in codes_of(findings)
    assert {f.predicate for f in findings if f.code == code} == {predicate}
    predicates = _build_dod_from_findings(run, findings)["predicates"]
    assert predicates[predicate] is False
    assert predicates["machine_checks_passed"] is False
