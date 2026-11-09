import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

import pytest

from tests.run_fixture import valid_run

from layout import SKILL_ROOT
MODULE_PATH = SKILL_ROOT / "scripts" / "verify_run.py"


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


def _stale_dod_run(tmp_path):
    run = valid_run(tmp_path)
    run.pop("_ledger_path", None)
    ledger = tmp_path / "run.json"
    ledger.write_text(json.dumps(run), encoding="utf-8")
    stale = tmp_path / "dod.json"
    stale.write_text(json.dumps({"passed": True}), encoding="utf-8")
    return ledger, stale


def test_failed_dod_write_leaves_no_stale_passing_dod(tmp_path, monkeypatch):
    ledger, stale = _stale_dod_run(tmp_path)
    module = load_module()

    def broken_write(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(module, "write_text_atomic", broken_write)
    monkeypatch.setattr(sys, "argv", ["verify_run.py", str(ledger)])
    with pytest.raises(OSError, match="disk full"):
        module.main()
    assert not stale.exists()


def test_mismatched_write_dod_leaves_no_stale_passing_dod(tmp_path):
    ledger, stale = _stale_dod_run(tmp_path)
    result = subprocess.run(
        [sys.executable, str(MODULE_PATH), str(ledger), "--write-dod", str(tmp_path / "other.json")],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1
    assert "dod.json must be written to" in result.stdout
    assert not stale.exists()


def test_failing_ledger_replaces_stale_passing_dod(tmp_path):
    ledger = tmp_path / "run.json"
    ledger.write_text("[]", encoding="utf-8")
    (tmp_path / "dod.json").write_text(json.dumps({"passed": True}), encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(MODULE_PATH), str(ledger)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1
    dod = json.loads((tmp_path / "dod.json").read_text(encoding="utf-8"))
    assert dod["passed"] is False


def test_dod_directory_fails_without_removing_it(tmp_path):
    ledger = tmp_path / "run.json"
    ledger.write_text("{}", encoding="utf-8")
    (tmp_path / "dod.json").mkdir()
    result = subprocess.run(
        [sys.executable, str(MODULE_PATH), str(ledger)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1
    assert "FAIL:" in result.stderr
    assert (tmp_path / "dod.json").is_dir()


def _upgrade_fixture_ledger_to_v2(run):
    sys.path.insert(0, str(SKILL_ROOT / "scripts"))
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


def _drop_done(events):
    return [e for e in events if e["type"] != "done"]


def _without_chunk_pass(events):
    return [
        e for e in _drop_done(events)
        if not (e["type"] == "node_passed" and e["node"].startswith("html-"))
    ]


def _failed_acquire_unrecovered(events):
    out = []
    for e in _drop_done(events):
        if e["type"] == "node_passed" and e["node"] == "acquire":
            out.append({"type": "node_failed", "node": "acquire", "evidence": "timeout"})
            out.append({"type": "failure_diagnosed", "node": "acquire", "evidence": "timeout"})
        else:
            out.append(e)
    return out


@pytest.mark.parametrize(
    ("rewrite", "expected_codes"),
    [
        (_without_chunk_pass, ["done.node.unresolved"]),
        (_failed_acquire_unrecovered, ["done.failure.unresolved", "done.node.unresolved"]),
        (_drop_done, []),
    ],
    ids=["unresolved-node", "unresolved-failure", "no-done-valid-passes"],
)
def test_end_of_run_checks_run_before_done_is_appended(tmp_path, rewrite, expected_codes):
    module = load_module()
    run = valid_run(tmp_path)
    run["events"] = rewrite(run["events"])
    codes = sorted({f.code for f in module.validate_findings(run)})
    assert codes == expected_codes


BAD_SHA = "0" * 64


def _evidence_files(run):
    root = Path(run["_ledger_path"]).parent
    return root, root / run["chunking"]["manifest"], root / run["chunking"]["evidence_ledger"]


def _edit_ledger(change):
    def mutate(run):
        _, _, ledger_path = _evidence_files(run)
        ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
        change(ledger)
        ledger_path.write_text(json.dumps(ledger, indent=2) + "\n", encoding="utf-8")
    return mutate


def _edit_manifest(change):
    """Rewrite the manifest and re-hash it into the run and the ledger, so only
    the field the row targets disagrees."""
    def mutate(run):
        _, manifest_path, ledger_path = _evidence_files(run)
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        change(manifest)
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        new_sha = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
        run["chunking"]["manifest_sha256"] = new_sha
        _edit_ledger(lambda ledger: ledger.update(manifest_sha256=new_sha))(run)
    return mutate


def _edit_events(change):
    def mutate(run):
        run["events"] = change(run["events"])
    return mutate


def _change_source_bytes(run):
    Path(run["source"]["local_path"]).write_text("<p>beta</p>", encoding="utf-8")


def _verified(events):
    return [e for e in events if e["type"] == "chunk_verified"]


SOURCE_COVERAGE = "source_coverage_complete"


@pytest.mark.parametrize(
    ("mutation", "expected_code"),
    [
        (_edit_ledger(lambda l: l.update(manifest_sha256=BAD_SHA)),
         "coverage.ledger.manifest_sha.mismatch"),
        (_edit_ledger(lambda l: l.update(source_sha256=BAD_SHA)),
         "coverage.ledger.source_sha.mismatch"),
        (_edit_ledger(lambda l: l.update(schema_version=3)),
         "coverage.ledger.schema_version"),
        (_edit_ledger(lambda l: l["entries"][0].update(ordinal=2)),
         "coverage.entry.ordinal.mismatch"),
        (_edit_ledger(lambda l: l["entries"][0].update(outcome="skipped")),
         "coverage.entry.outcome.invalid"),
        (_edit_ledger(lambda l: l["entries"][0].update(chunk_sha256=BAD_SHA)),
         "coverage.entry.hash.mismatch"),
        (_edit_manifest(lambda m: m["chunks"][0].update(content_sha256=BAD_SHA)),
         "coverage.chunk.content_sha.mismatch"),
        (_edit_manifest(lambda m: m["source"].update(sha256=BAD_SHA)),
         "coverage.manifest_source.sha.mismatch"),
        (_change_source_bytes, "coverage.source_sha.mismatch"),
        (lambda run: run["source"].pop("sha256"), "coverage.source_sha.missing"),
        (lambda run: run["source"].pop("local_path"), "coverage.source_local_path.missing"),
        (lambda run: Path(run["source"]["local_path"]).unlink(), "coverage.source_local_path.missing"),
        (_edit_events(lambda ev: ev + [dict(_verified(ev)[0])]),
         "events.chunk_verified.duplicate"),
        (_edit_events(lambda ev: ev + [{"type": "chunk_verified", "chunk_id": "ghost"}]),
         "events.chunk_verified.unknown"),
        (_edit_events(lambda ev: [e for e in ev if e["type"] != "chunk_verified"]),
         "events.chunk_verified.mirror"),
        (lambda run: run["coverage"].update(completed=[]), "coverage.mirror.completed.mismatch"),
    ],
    ids=lambda value: value if isinstance(value, str) else "",
)
def test_ledger_and_manifest_binding_failures_carry_their_code(tmp_path, mutation, expected_code):
    module = load_module()
    run = valid_run(tmp_path)
    assert module.validate_findings(run) == []
    mutation(run)
    hits = [f for f in module.validate_findings(run) if f.code == expected_code]
    assert hits, f"{expected_code} not emitted"
    assert {f.predicate for f in hits} == {SOURCE_COVERAGE}


def _codes(module, run):
    return [f.code for f in module.validate_findings(run)]


def test_relocated_run_folder_verifies_with_no_findings(tmp_path):
    module = load_module()
    old = tmp_path / "old"
    run = valid_run(old)
    run["source"]["local_path"] = "source/source.html"
    new = tmp_path / "new"
    shutil.copytree(old, new)
    shutil.rmtree(old)
    run["_ledger_path"] = str(new / "run.json")
    assert module.validate_findings(run) == []


@pytest.mark.parametrize(
    "mutation",
    [
        _change_source_bytes,
        _edit_manifest(lambda m: m["source"].update(size_bytes=999)),
    ],
    ids=["source_bytes", "source_size_bytes"],
)
def test_reproduction_still_mismatches_on_bound_source_fields(tmp_path, mutation):
    module = load_module()
    run = valid_run(tmp_path)
    mutation(run)
    assert "reproduction.mismatch" in _codes(module, run)


def test_reproduction_compares_source_uri(tmp_path, monkeypatch):
    """The extractor echoes the manifest's own uri, so a stub extractor that
    reports a different one is the only way to reach the uri comparison."""
    module = load_module()
    run = valid_run(tmp_path)
    manifest = json.loads((tmp_path / run["chunking"]["manifest"]).read_text(encoding="utf-8"))

    def fake_extractor(args, **kwargs):
        reproduced = json.loads(json.dumps(manifest))
        reproduced["source"]["uri"] = "https://example.org/other"
        Path(args[args.index("--out") + 1]).write_text(json.dumps(reproduced), encoding="utf-8")
        return subprocess.CompletedProcess(args, 0, "", "")

    monkeypatch.setattr(module.subprocess, "run", fake_extractor)
    findings = []
    module._reproduce_extraction_manifest(Path(run["source"]["local_path"]), manifest, findings)
    assert [f.code for f in findings] == ["reproduction.mismatch"]


BIG = 20_000
BIG_CHUNKS = 40_000  # list-membership pre-fix time must clearly exceed the bound
LINEAR_BOUND_SECONDS = 3.0


def _codes_for(module, run):
    return [f.code for f in module._validate_findings(run)]


def test_many_plan_nodes_resolve_in_linear_time():
    module = load_module()
    nodes = [f"n{i}" for i in range(BIG)]
    events = [{"type": "node_passed", "node": n} for n in nodes]
    events += [{"type": "verification_started"}, {"type": "verification_passed"}, {"type": "done"}]
    run = {"plan": {"nodes": nodes}, "events": events}
    started = time.perf_counter()
    codes = _codes_for(module, run)
    assert time.perf_counter() - started < LINEAR_BOUND_SECONDS
    assert "done.node.unresolved" not in codes


@pytest.mark.parametrize(
    ("nodes", "events", "unresolved_nodes"),
    [
        (
            ["a", "b"],
            [
                {"type": "node_passed", "node": "a"},
                {"type": "node_passed", "node": ["unhashable"]},
                {"type": "done"},
            ],
            ["b"],
        ),
        (
            ["a", "b"],
            [
                {"type": "node_passed", "node": "a"},
                {"type": "done"},
                {"type": "node_passed", "node": "b"},
            ],
            ["b"],
        ),
        (
            ["a", "b"],
            [
                {"type": "node_passed", "node": "a"},
                {"type": "node_superseded", "node": "b"},
                {"type": "done"},
            ],
            [],
        ),
        (
            [1],
            [{"type": "node_passed", "node": "1"}, {"type": "done"}],
            [],
        ),
    ],
    ids=["unhashable-event-node", "passed-after-done", "superseded-resolves", "non-str-plan-node"],
)
def test_node_resolution_uses_events_before_done(nodes, events, unresolved_nodes):
    module = load_module()
    findings = module._validate_findings({"plan": {"nodes": nodes}, "events": events})
    unresolved = [f for f in findings if f.code == "done.node.unresolved"]
    assert [f.detail for f in unresolved] == unresolved_nodes


def test_many_chunk_verified_events_check_in_linear_time(monkeypatch):
    module = load_module()
    ids = [f"c{i}" for i in range(BIG_CHUNKS)]
    monkeypatch.setattr(module, "_validate_chunk_evidence", lambda run, base, findings: (ids, ids))
    events = [{"type": "chunk_verified", "chunk_id": c} for c in ids]
    run = {"chunking": {}, "events": events}
    started = time.perf_counter()
    codes = _codes_for(module, run)
    assert time.perf_counter() - started < LINEAR_BOUND_SECONDS
    assert not [c for c in codes if c.startswith("events.chunk_verified.")]


def test_chunk_verified_missing_and_unknown_keep_manifest_then_event_order(monkeypatch):
    module = load_module()
    monkeypatch.setattr(module, "_validate_chunk_evidence", lambda run, base, findings: (["a", "b"], ["a", "b"]))
    events = [{"type": "chunk_verified", "chunk_id": c} for c in ("z", "a", "y")]
    findings = module._validate_findings({"chunking": {}, "events": events})
    coverage = [(f.code, f.detail) for f in findings if f.code.startswith("events.chunk_verified.")]
    assert coverage[:3] == [
        ("events.chunk_verified.missing", "b"),
        ("events.chunk_verified.unknown", "z"),
        ("events.chunk_verified.unknown", "y"),
    ]
