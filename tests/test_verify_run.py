import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest

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


@pytest.mark.parametrize(
    "field",
    ["source", "preflight", "plan", "deliverable", "evidence", "qa", "fidelity", "chunking"],
)
def test_mapping_contracts_fail_diagnostically(tmp_path, field):
    module = load_module()
    run = valid_run(tmp_path)
    run[field] = []
    errors = module.validate_run(run)
    assert any(f"{field} must be an object" in e for e in errors)


def test_event_entries_must_be_objects(tmp_path):
    module = load_module()
    run = valid_run(tmp_path)
    run["events"] = ["oops"]
    errors = module.validate_run(run)
    assert any("events[1] must be an object" in e for e in errors)


def test_reproduced_extraction_timeout_is_a_violation(tmp_path, monkeypatch):
    module = load_module()
    source = tmp_path / "source.md"
    source.write_text("# A\nproof\n", encoding="utf-8")
    manifest = {
        "source": {"format": "markdown", "uri": str(source)},
        "chunking": {"max_bytes": 12000},
    }

    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=args[0], timeout=module.EXTRACTION_TIMEOUT_SECONDS)

    monkeypatch.setattr(module.subprocess, "run", timeout)
    findings = []
    module._reproduce_extraction_manifest(source, manifest, findings)
    assert [f.message for f in findings] == [
        f"reproduced extraction timed out after {module.EXTRACTION_TIMEOUT_SECONDS}s"
    ]


def test_cli_rejects_non_object_run_json_without_traceback(tmp_path):
    ledger = tmp_path / "run.json"
    ledger.write_text("[]\n", encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(MODULE_PATH), str(ledger)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1
    assert "FAIL:" in result.stdout
    assert "Traceback" not in result.stdout + result.stderr
    dod = json.loads((tmp_path / "dod.json").read_text(encoding="utf-8"))
    assert dod["passed"] is False


def _upgrade_fixture_ledger_to_v2(run):
    sys.path.insert(0, str(ROOT / "scripts"))
    from evidence_atoms import atom_id

    ledger_path = Path(run["_ledger_path"]).parent / run["chunking"]["evidence_ledger"]
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    ledger["schema_version"] = 2
    for entry in ledger["entries"]:
        for plural, singular in (("assertions", "assertion"), ("constraints", "constraint")):
            for atom in entry.get(plural, []):
                atom["atom_id"] = atom_id(
                    entry["chunk_id"], singular,
                    atom["chunk_byte_start"], atom["chunk_byte_end"], atom["text"],
                )
    ledger_path.write_text(json.dumps(ledger, indent=2) + "\n", encoding="utf-8")
    return ledger_path, ledger


def test_schema_v2_atom_ids_are_accepted(tmp_path):
    module = load_module()
    run = valid_run(tmp_path)
    ledger_path, _ = _upgrade_fixture_ledger_to_v2(run)
    manifest_path = tmp_path / run["chunking"]["manifest"]
    from scripts.chunk_common import render_traversal_report
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    (tmp_path / run["chunking"]["traversal_report"]).write_text(
        render_traversal_report(manifest, ledger), encoding="utf-8"
    )
    errors = module.validate_run(run)
    assert not [e for e in errors if "schema_version" in e or "atom_id" in e], errors


def test_schema_v2_forged_atom_id_is_rejected(tmp_path):
    module = load_module()
    run = valid_run(tmp_path)
    ledger_path, ledger = _upgrade_fixture_ledger_to_v2(run)
    ledger["entries"][0]["assertions"][0]["atom_id"] = "forged"
    ledger_path.write_text(json.dumps(ledger, indent=2) + "\n", encoding="utf-8")
    errors = module.validate_run(run)
    assert any("atom_id does not match deterministic identity" in e for e in errors)


def test_schema_v2_duplicate_atom_id_is_rejected(tmp_path):
    module = load_module()
    run = valid_run(tmp_path)
    ledger_path, ledger = _upgrade_fixture_ledger_to_v2(run)
    original = dict(ledger["entries"][0]["assertions"][0])
    ledger["entries"][0]["constraints"] = [original]
    ledger_path.write_text(json.dumps(ledger, indent=2) + "\n", encoding="utf-8")
    errors = module.validate_run(run)
    assert any("duplicate atom_id" in e for e in errors)
