from __future__ import annotations

import copy
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from verify_run import validate_run
from run_fixture import valid_run

NEW_PREFLIGHT = {
    "skill_read": True,
    "required_references_read": True,
    "helper_help_read": True,
    "runtime_profile_resolved": True,
    "traversal_plan_ready": True,
}

def errors_for(run):
    return validate_run(copy.deepcopy(run))

def test_native_preflight_is_accepted(tmp_path):
    run = valid_run(tmp_path)
    run["preflight"] = dict(NEW_PREFLIGHT)
    errors = errors_for(run)
    assert not [e for e in errors if e.startswith("preflight.")], errors

def test_sibling_traversal_after_failure_requires_diagnosis(tmp_path):
    run = valid_run(tmp_path)
    run["preflight"] = dict(NEW_PREFLIGHT)
    run["plan"]["nodes"].extend(["broken", "sibling"])
    insert_at = run["events"].index({"type": "verification_started"})
    run["events"][insert_at:insert_at] = [
        {"type": "node_started", "node": "broken"},
        {"type": "node_failed", "node": "broken"},
        {"type": "node_started", "node": "sibling"},
        {"type": "node_passed", "node": "sibling", "evidence": "evidence/source-manifest.md"},
        {"type": "node_superseded", "node": "broken"},
    ]
    errors = errors_for(run)
    assert any("failure_diagnosed" in e for e in errors), errors

def test_repair_after_failure_requires_diagnosis(tmp_path):
    run = valid_run(tmp_path)
    run["preflight"] = dict(NEW_PREFLIGHT)
    run["plan"]["nodes"].append("broken")
    insert_at = run["events"].index({"type": "verification_started"})
    run["events"][insert_at:insert_at] = [
        {"type": "node_started", "node": "broken"},
        {"type": "node_failed", "node": "broken"},
        {"type": "node_rechunked", "node": "broken", "children": ["broken-a", "broken-b"]},
        {"type": "node_superseded", "node": "broken"},
    ]
    errors = errors_for(run)
    assert any("failure_diagnosed" in e for e in errors), errors

def test_architecture_stop_blocks_further_repair_until_replan(tmp_path):
    run = valid_run(tmp_path)
    run["preflight"] = dict(NEW_PREFLIGHT)
    insert_at = run["events"].index({"type": "verification_started"})
    run["events"][insert_at:insert_at] = [
        {"type": "architecture_stop", "node": "acquire"},
        {"type": "node_rechunked", "node": "acquire", "children": ["a", "b"]},
    ]
    errors = errors_for(run)
    assert any("architecture_stop" in e and "repair" in e for e in errors), errors

def test_alternative_design_requires_architecture_stop_exhaustion_and_disclosure(tmp_path):
    run = valid_run(tmp_path)
    run["preflight"] = dict(NEW_PREFLIGHT)
    insert_at = run["events"].index({"type": "verification_started"})
    run["events"].insert(insert_at, {"type": "alternative_designed"})
    errors = errors_for(run)
    assert any("alternative_designed" in e and "architecture_stop" in e for e in errors), errors


@pytest.mark.parametrize(
    "key",
    [
        "using_superpowers_read",
        "superpowers_list_consumed",
        "applicable_skills_read",
        "live_dependencies_read",
    ],
)
def test_legacy_preflight_key_is_accepted(tmp_path, key):
    run = valid_run(tmp_path)
    run["preflight"] = {**NEW_PREFLIGHT, key: True}
    assert errors_for(run) == []


@pytest.mark.parametrize("event_type", ["systematic_debugging", "brainstorming"])
def test_legacy_process_event_is_accepted(tmp_path, event_type):
    run = valid_run(tmp_path)
    run["preflight"] = dict(NEW_PREFLIGHT)
    insert_at = run["events"].index({"type": "verification_started"})
    run["events"].insert(insert_at, {"type": event_type})
    assert errors_for(run) == []
