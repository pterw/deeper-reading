import importlib.util
from pathlib import Path

from tests.run_fixture import REQUIRED_EVIDENCE_FILES, valid_run

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "verify_run.py"


def load_module():
    spec = importlib.util.spec_from_file_location("verify_run", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_valid_run_has_no_violations(tmp_path):
    module = load_module()
    assert module.validate_run(valid_run(tmp_path)) == []


def test_done_requires_final_verification(tmp_path):
    module = load_module()
    run = valid_run(tmp_path)
    run["events"] = [e for e in run["events"] if e["type"] != "verification_passed"]
    errors = module.validate_run(run)
    assert any("verification_passed" in e for e in errors)


def test_failure_requires_diagnosis_before_traversal(tmp_path):
    module = load_module()
    run = valid_run(tmp_path)
    run["plan"]["nodes"] = ["acquire", "read-chunk-1", "read-chunk-2"]
    run["events"] = [
        {"type": "plan_written"},
        {"type": "execution_started"},
        {"type": "node_started", "node": "acquire"},
        {"type": "node_passed", "node": "acquire", "evidence": "source-manifest.md"},
        {"type": "node_started", "node": "read-chunk-1"},
        {"type": "node_failed", "node": "read-chunk-1", "evidence": "timeout"},
        {"type": "node_started", "node": "read-chunk-2"},
    ]
    errors = module.validate_run(run)
    assert any("failure_diagnosed" in e for e in errors)


def test_alternative_design_requires_architecture_stop_exhaustion_and_disclosure(tmp_path):
    module = load_module()
    run = valid_run(tmp_path)
    run["events"] = [
        {"type": "plan_written"},
        {"type": "execution_started"},
        {"type": "node_started", "node": "acquire"},
        {"type": "node_failed", "node": "acquire", "evidence": "blocked"},
        {"type": "failure_diagnosed", "node": "acquire", "evidence": "root-cause"},
        {"type": "alternative_designed", "node": "acquire"},
    ]
    errors = module.validate_run(run)
    assert any("alternative_designed" in e and "architecture_stop" in e for e in errors)


def test_preflight_is_mandatory(tmp_path):
    module = load_module()
    run = valid_run(tmp_path)
    run["preflight"]["required_references_read"] = False
    errors = module.validate_run(run)
    assert any("required_references_read" in e for e in errors)


def test_evidence_paths_must_exist(tmp_path):
    module = load_module()
    run = valid_run(tmp_path)
    run["evidence"]["source_manifest"] = "missing-source-manifest.md"
    errors = module.validate_run(run)
    assert any("evidence.source_manifest" in e and "does not exist" in e for e in errors)


def test_requested_deliverable_file_must_exist(tmp_path):
    module = load_module()
    run = valid_run(tmp_path)
    run["deliverable"] = {
        "requested": "PDF file",
        "provided": True,
        "paths": ["missing.pdf"],
    }
    errors = module.validate_run(run)
    assert any("deliverable path does not exist" in e for e in errors)


def test_cli_resolves_evidence_relative_to_ledger(tmp_path):
    import json
    import subprocess
    run = valid_run(tmp_path)
    run.pop("_ledger_path", None)
    ledger = tmp_path / "run.json"
    ledger.write_text(json.dumps(run), encoding="utf-8")
    result = subprocess.run(
        ["python", str(MODULE_PATH), str(ledger)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_coverage_report_cannot_expand_or_shrink_manifest_universe(tmp_path):
    module = load_module()
    run = valid_run(tmp_path)
    run["coverage"]["required"].append("forged-extra-chunk")
    errors = module.validate_run(run)
    assert any("coverage.required must exactly mirror manifest chunk ids" in e for e in errors)


def test_required_format_qa_must_pass(tmp_path):
    module = load_module()
    run = valid_run(tmp_path)
    run["qa"]["required"].append("figure-inspection")
    errors = module.validate_run(run)
    assert any("qa missing required check" in e for e in errors)


def test_final_verification_must_follow_last_material_event(tmp_path):
    module = load_module()
    run = valid_run(tmp_path)
    run["events"] = [
        {"type": "plan_written"},
        {"type": "execution_started"},
        {"type": "node_started", "node": "acquire"},
        {"type": "node_passed", "node": "acquire"},
        {"type": "verification_started"},
        {"type": "verification_passed"},
        {"type": "node_started", "node": "read-chunk-1"},
        {"type": "node_passed", "node": "read-chunk-1"},
        {"type": "done"},
    ]
    errors = module.validate_run(run)
    assert any("verification_passed must follow the last material event" in e for e in errors)


def test_plan_path_must_exist(tmp_path):
    module = load_module()
    run = valid_run(tmp_path)
    run["plan"]["path"] = "missing-plan.md"
    errors = module.validate_run(run)
    assert any("plan.path does not exist" in e for e in errors)


def test_coverage_report_is_optional_because_manifest_evidence_is_authoritative(tmp_path):
    module = load_module()
    run = valid_run(tmp_path)
    run.pop("coverage")
    errors = module.validate_run(run)
    assert not any(e.startswith("coverage") for e in errors)


def test_qa_contract_is_required(tmp_path):
    module = load_module()
    run = valid_run(tmp_path)
    run.pop("qa")
    errors = module.validate_run(run)
    assert any("qa contract is required" in e for e in errors)


def test_format_qa_evidence_is_required(tmp_path):
    module = load_module()
    run = valid_run(tmp_path)
    run["evidence"].pop("format_qa")
    errors = module.validate_run(run)
    assert any("evidence.format_qa" in e for e in errors)


def test_fidelity_contract_is_required(tmp_path):
    module = load_module()
    run = valid_run(tmp_path)
    run.pop("fidelity")
    errors = module.validate_run(run)
    assert any("fidelity contract is required" in e for e in errors)


def test_unpreserved_fidelity_is_rejected(tmp_path):
    module = load_module()
    run = valid_run(tmp_path)
    run["fidelity"] = {"preserved": False, "substitutions": ["primary->secondary"]}
    errors = module.validate_run(run)
    assert any("source fidelity must be preserved" in e for e in errors)


def test_dod_output_exposes_terminal_predicates(tmp_path):
    module = load_module()
    run = valid_run(tmp_path)
    errors = module.validate_run(run)
    dod = module.build_dod(run, errors)
    required = {
        "source_identity_verified",
        "skill_preflight_complete",
        "plan_resolved",
        "source_coverage_complete",
        "failure_protocol_respected",
        "source_fidelity_preserved",
        "format_qa_complete",
        "requested_deliverable_produced",
        "no_unresolved_required_failures",
        "fresh_final_verification",
        "machine_checks_passed",
    }
    assert required <= set(dod["predicates"])
