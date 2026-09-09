import copy
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "verify_run.py"


def load_module():
    spec = importlib.util.spec_from_file_location("verify_run", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def baseline(tmp_path):
    from tests.run_fixture import valid_run
    return valid_run(tmp_path)


def test_unmutated_rfc9110_baseline_passes(tmp_path):
    run = baseline(tmp_path)
    assert load_module().validate_run(run) == []


def assert_rejected(run, needle):
    errors = load_module().validate_run(run)
    assert errors, "mutation unexpectedly passed"
    assert any(needle in error for error in errors), errors


def test_mutation_skip_required_reference_read(tmp_path):
    run = baseline(tmp_path)
    run["preflight"]["required_references_read"] = False
    assert_rejected(run, "required_references_read")


def test_mutation_skip_written_plan(tmp_path):
    run = baseline(tmp_path)
    run["events"] = [e for e in run["events"] if e["type"] != "plan_written"]
    assert_rejected(run, "plan_written")


def test_mutation_move_to_sibling_after_failure(tmp_path):
    run = baseline(tmp_path)
    run["plan"]["nodes"] = ["acquire", "read-chunk-1", "read-chunk-2"]
    run["events"] = [
        {"type": "plan_written"},
        {"type": "execution_started"},
        {"type": "node_started", "node": "acquire"},
        {"type": "node_passed", "node": "acquire"},
        {"type": "node_started", "node": "read-chunk-1"},
        {"type": "node_failed", "node": "read-chunk-1", "evidence": "timeout"},
        {"type": "node_started", "node": "read-chunk-2"},
    ]
    assert_rejected(run, "failure_diagnosed")


def test_mutation_alternative_design_before_exhaustion(tmp_path):
    run = baseline(tmp_path)
    run["events"] = [
        {"type": "plan_written"},
        {"type": "execution_started"},
        {"type": "node_started", "node": "acquire"},
        {"type": "node_failed", "node": "acquire"},
        {"type": "failure_diagnosed", "node": "acquire"},
        {"type": "alternative_designed", "node": "acquire"},
    ]
    assert_rejected(run, "architecture_stop")


def test_mutation_claim_done_before_verification(tmp_path):
    run = baseline(tmp_path)
    run["events"] = [e for e in run["events"] if e["type"] != "verification_passed"]
    assert_rejected(run, "verification_passed")


def test_mutation_leave_failed_node_unresolved_at_done(tmp_path):
    run = baseline(tmp_path)
    run["plan"]["nodes"] = ["acquire", "read-chunk-1"]
    run["events"] = [
        {"type": "plan_written"},
        {"type": "execution_started"},
        {"type": "node_started", "node": "acquire"},
        {"type": "node_passed", "node": "acquire"},
        {"type": "node_started", "node": "read-chunk-1"},
        {"type": "node_failed", "node": "read-chunk-1"},
        {"type": "failure_diagnosed", "node": "read-chunk-1"},
        {"type": "verification_started"},
        {"type": "verification_passed"},
        {"type": "done"},
    ]
    assert_rejected(run, "unresolved failed node")

def test_mutation_rechunk_before_failure_diagnosis(tmp_path):
    run = baseline(tmp_path)
    run["events"] = [
        {"type": "plan_written"},
        {"type": "execution_started"},
        {"type": "node_started", "node": "acquire"},
        {"type": "node_failed", "node": "acquire", "evidence": "timeout"},
        {"type": "node_rechunked", "node": "acquire"},
    ]
    assert_rejected(run, "failure_diagnosed")


def test_mutation_repair_after_architecture_stop_without_redesign_or_replan(tmp_path):
    run = baseline(tmp_path)
    run["events"] = [
        {"type": "plan_written"},
        {"type": "execution_started"},
        {"type": "node_started", "node": "acquire"},
        {"type": "node_failed", "node": "acquire", "evidence": "repeated failure"},
        {"type": "failure_diagnosed", "node": "acquire"},
        {"type": "architecture_stop", "node": "acquire"},
        {"type": "node_rechunked", "node": "acquire"},
    ]
    assert_rejected(run, "architecture_stop")


def test_mutation_alternative_design_before_paths_exhausted_and_disclosure(tmp_path):
    run = baseline(tmp_path)
    run["events"] = [
        {"type": "plan_written"},
        {"type": "execution_started"},
        {"type": "node_started", "node": "acquire"},
        {"type": "node_failed", "node": "acquire", "evidence": "repeated failure"},
        {"type": "failure_diagnosed", "node": "acquire"},
        {"type": "architecture_stop", "node": "acquire"},
        {"type": "alternative_designed", "node": "acquire"},
    ]
    assert_rejected(run, "paths_exhausted")


def test_mutation_stale_final_verification_after_later_material_event(tmp_path):
    run = baseline(tmp_path)
    done_index = next(i for i, event in enumerate(run["events"]) if event["type"] == "done")
    run["events"].insert(done_index, {"type": "node_rechunked", "node": "acquire"})
    assert_rejected(run, "last material event")

