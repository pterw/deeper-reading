import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "verify_run.py"
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from evidence_atoms import AmbiguousEvidenceError, EvidenceBindingError, atom_id, bind_atom


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


def _ledger_path(run):
    return Path(run["_ledger_path"]).parent / run["chunking"]["evidence_ledger"]


def _manifest_path(run):
    return Path(run["_ledger_path"]).parent / run["chunking"]["manifest"]


def _upgrade_ledger_to_v2(run):
    path = _ledger_path(run)
    ledger = json.loads(path.read_text(encoding="utf-8"))
    ledger["schema_version"] = 2
    for entry in ledger["entries"]:
        chunk_id = entry["chunk_id"]
        for plural, singular in (("assertions", "assertion"), ("constraints", "constraint")):
            for atom in entry.get(plural, []):
                atom["atom_id"] = atom_id(
                    chunk_id,
                    singular,
                    atom["chunk_byte_start"],
                    atom["chunk_byte_end"],
                    atom["text"],
                )
    path.write_text(json.dumps(ledger, indent=2) + "\n", encoding="utf-8")
    return ledger


def _rewrite_report(run):
    module = load_module()
    root = Path(run["_ledger_path"]).parent
    manifest = json.loads(_manifest_path(run).read_text(encoding="utf-8"))
    ledger = json.loads(_ledger_path(run).read_text(encoding="utf-8"))
    report_path = root / run["chunking"]["traversal_report"]
    report_path.write_text(module.render_traversal_report(manifest, ledger), encoding="utf-8")


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



def test_mutation_html_generic_container_text_is_not_dropped(tmp_path):
    source = tmp_path / "generic.html"
    source.write_text(
        "<main>lead<div>div proof</div><section><span>section proof</span></section>tail</main>",
        encoding="utf-8",
    )
    out = tmp_path / "manifest.json"
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / "extract_html.py"), str(source), "--out", str(out)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    manifest = json.loads(out.read_text(encoding="utf-8"))
    extracted = "".join(chunk["content"] for chunk in manifest["chunks"])
    for phrase in ("lead", "div proof", "section proof", "tail"):
        assert extracted.count(phrase) == 1, f"HTML generic-text deletion/duplication escaped for {phrase!r}"


def test_mutation_schema_v2_forged_atom_id_is_rejected(tmp_path):
    run = baseline(tmp_path)
    ledger = _upgrade_ledger_to_v2(run)
    ledger["entries"][0]["assertions"][0]["atom_id"] = "forged"
    _ledger_path(run).write_text(json.dumps(ledger, indent=2) + "\n", encoding="utf-8")
    _rewrite_report(run)
    assert_rejected(run, "atom_id does not match deterministic identity")


def test_mutation_schema_v2_duplicate_atom_id_is_rejected_for_intended_predicate(tmp_path):
    run = baseline(tmp_path)
    ledger = _upgrade_ledger_to_v2(run)
    entry = ledger["entries"][0]
    original = entry["assertions"][0]
    entry["constraints"].append(dict(original))
    _ledger_path(run).write_text(json.dumps(ledger, indent=2) + "\n", encoding="utf-8")
    _rewrite_report(run)
    assert_rejected(run, "duplicate atom_id")


def test_mutation_wrong_explicit_evidence_span_is_rejected():
    with pytest.raises(EvidenceBindingError, match="does not match"):
        bind_atom(
            "markdown-1",
            "assertion",
            "alpha beta",
            {"text": "beta", "chunk_byte_start": 0, "chunk_byte_end": 4},
        )


def test_mutation_repeated_quote_without_explicit_span_is_rejected():
    with pytest.raises(AmbiguousEvidenceError, match=r"byte starts \[0, 19\]"):
        bind_atom(
            "markdown-1",
            "assertion",
            "same phrase\nmiddle\nsame phrase\n",
            {"text": "same phrase"},
        )


def test_mutation_malformed_event_entry_is_rejected_for_event_shape(tmp_path):
    run = baseline(tmp_path)
    run["events"].insert(0, "oops")
    assert_rejected(run, "events[1] must be an object")


@pytest.mark.parametrize("field", ["source", "preflight", "evidence"])
def test_mutation_malformed_mapping_is_rejected_for_field_shape(tmp_path, field):
    run = baseline(tmp_path)
    run[field] = []
    assert_rejected(run, f"{field} must be an object")


def test_mutation_reproduced_extraction_timeout_is_rejected(monkeypatch, tmp_path):
    module = load_module()
    source = tmp_path / "source.md"
    source.write_text("# A\nproof\n", encoding="utf-8")
    manifest = {
        "source": {"format": "markdown"},
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


def test_mutation_forged_grouped_traversal_report_is_rejected(tmp_path):
    run = baseline(tmp_path)
    root = Path(run["_ledger_path"]).parent
    report = root / run["chunking"]["traversal_report"]
    report.write_text(report.read_text(encoding="utf-8") + "\nforged\n", encoding="utf-8")
    assert_rejected(run, "traversal report does not match canonical manifest/evidence rendering")
