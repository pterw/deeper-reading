import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERIFY = ROOT / "scripts" / "verify_run.py"
REPORT = ROOT / "scripts" / "traversal_report.py"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_verify():
    spec = importlib.util.spec_from_file_location("verify_run_report", VERIFY)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def make_run(tmp_path: Path) -> dict:
    source_dir = tmp_path / "source"
    source_dir.mkdir(parents=True, exist_ok=True)
    source = source_dir / "source.html"
    source.write_text("<h1>A</h1><p>Alpha proof.</p><h1>B</h1><p>Beta caveat.</p>", encoding="utf-8")
    manifest_path = tmp_path / "evidence" / "chunk-manifest.json"
    result = subprocess.run([sys.executable, str(ROOT / "scripts" / "extract_html.py"), str(source), "--run-root", str(tmp_path), "--max-bytes", "80"], capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stdout + result.stderr
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert len(manifest["chunks"]) == 2
    entries = []
    for chunk in manifest["chunks"]:
        content = chunk["content"]
        text = content.strip().split("\n")[-1]
        start = content.encode("utf-8").find(text.encode("utf-8"))
        entries.append({
            "chunk_id": chunk["id"],
            "ordinal": chunk["ordinal"],
            "chunk_sha256": chunk["content_sha256"],
            "outcome": "evidence",
            "assertions": [{"text": text, "chunk_byte_start": start, "chunk_byte_end": start + len(text.encode("utf-8"))}],
            "constraints": [],
        })
    ledger = {
        "schema_version": 1,
        "manifest_sha256": sha(manifest_path.read_bytes()),
        "source_sha256": sha(source.read_bytes()),
        "entries": entries,
    }
    evidence_path = tmp_path / "evidence" / "chunk-evidence.json"
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    evidence_path.write_text(json.dumps(ledger, indent=2) + "\n", encoding="utf-8")
    (tmp_path / "plan.md").write_text("evidence\n", encoding="utf-8")
    for name in ["skill-preflight.md", "source-manifest.md", "failure-ledger.md", "verification-log.txt", "format-qa.md"]:
        path = tmp_path / "evidence" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("evidence\n", encoding="utf-8")
    return {
        "_ledger_path": str(tmp_path / "run.json"),
        "source": {"uri": manifest["source"]["uri"], "local_path": str(source.resolve()), "sha256": sha(source.read_bytes()), "format": "html", "authority": "primary", "identity_verified": True},
        "fidelity": {"preserved": True, "substitutions": []},
        "preflight": {"skill_read": True, "required_references_read": True, "helper_help_read": True, "runtime_profile_resolved": True, "traversal_plan_ready": True},
        "plan": {"path": "plan.md", "nodes": ["read-document"]},
        "events": [{"type": "plan_written"}, {"type": "execution_started"}, {"type": "node_started", "node": "read-document"}, *[{"type": "chunk_verified", "chunk_id": c["id"], "chunk_sha256": c["content_sha256"], "evidence": "evidence/chunk-evidence.json"} for c in manifest["chunks"]], {"type": "node_passed", "node": "read-document", "evidence": "evidence/chunk-evidence.json"}, {"type": "verification_started"}, {"type": "verification_passed", "evidence": "evidence/verification-log.txt"}, {"type": "done"}],
        "chunking": {"manifest": "evidence/chunk-manifest.json", "manifest_sha256": sha(manifest_path.read_bytes()), "evidence_ledger": "evidence/chunk-evidence.json", "traversal_report": "deliverables/TRAVERSAL_REPORT.md"},
        "coverage": {"required": [c["id"] for c in manifest["chunks"]], "completed": [c["id"] for c in manifest["chunks"]]},
        "qa": {"required": ["html-structure"], "passed": ["html-structure"]},
        "deliverable": {"requested": "answer", "provided": True, "paths": [], "traversal_report": "deliverables/TRAVERSAL_REPORT.md"},
        "evidence": {"plan_status": "plan.md", "skill_preflight": "evidence/skill-preflight.md", "source_manifest": "evidence/source-manifest.md", "chunk_ledger": "evidence/chunk-evidence.json", "failure_ledger": "evidence/failure-ledger.md", "verification_log": "evidence/verification-log.txt", "format_qa": "evidence/format-qa.md", "traversal_report": "deliverables/TRAVERSAL_REPORT.md"},
    }


def write_report(tmp_path: Path) -> None:
    result = subprocess.run([sys.executable, str(REPORT), "--run-root", str(tmp_path)], capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stdout + result.stderr


def test_abstractive_string_assertions_are_rejected(tmp_path):
    module = load_verify()
    run = make_run(tmp_path)
    ledger_path = tmp_path / "evidence" / "chunk-evidence.json"
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    ledger["entries"][0]["assertions"] = ["This is a prose summary, not extractive evidence."]
    ledger_path.write_text(json.dumps(ledger, indent=2) + "\n", encoding="utf-8")
    errors = module.validate_run(run)
    assert any("atomic extractive assertion" in e for e in errors)


def test_atomic_assertion_span_must_match_exact_chunk_bytes(tmp_path):
    module = load_verify()
    run = make_run(tmp_path)
    ledger_path = tmp_path / "evidence" / "chunk-evidence.json"
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    ledger["entries"][0]["assertions"][0]["text"] = "fabricated"
    ledger_path.write_text(json.dumps(ledger, indent=2) + "\n", encoding="utf-8")
    errors = module.validate_run(run)
    assert any("extractive span does not match chunk bytes" in e for e in errors)


def test_traversal_report_is_required_and_must_be_reproducible(tmp_path):
    module = load_verify()
    run = make_run(tmp_path)
    errors = module.validate_run(run)
    assert any("traversal report" in e.lower() for e in errors)
    write_report(tmp_path)
    assert module.validate_run(run) == []
    (tmp_path / "deliverables" / "TRAVERSAL_REPORT.md").write_text("# forged report\n", encoding="utf-8")
    errors = module.validate_run(run)
    assert any("traversal report does not match" in e.lower() for e in errors)


def test_traversal_report_has_one_chunk_mapping_with_locator_outcome_and_atomic_text(tmp_path):
    run = make_run(tmp_path)
    write_report(tmp_path)
    text = (tmp_path / "deliverables" / "TRAVERSAL_REPORT.md").read_text(encoding="utf-8")
    manifest = json.loads((tmp_path / "evidence" / "chunk-manifest.json").read_text(encoding="utf-8"))
    for chunk in manifest["chunks"]:
        assert chunk["id"] in text
    assert "Locator" in text
    assert "Outcome" in text
    assert "Verified assertion / reason" in text
    assert "Alpha proof." in text
    assert "Beta caveat." in text


def test_deliverable_contract_makes_traversal_report_user_visible():
    body = (ROOT / "references" / "deliverable.md").read_text(encoding="utf-8").lower()
    assert "traversal_report.md" in body
    assert "user-visible" in body
    assert "requested" in body and "deliverable" in body
