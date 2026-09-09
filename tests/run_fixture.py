import hashlib
import json
from pathlib import Path
import subprocess
import sys

REQUIRED_EVIDENCE_FILES = {
    "plan_status": "plan.md",
    "skill_preflight": "evidence/skill-preflight.md",
    "source_manifest": "evidence/source-manifest.md",
    "chunk_ledger": "evidence/chunk-evidence.json",
    "failure_ledger": "evidence/failure-ledger.md",
    "verification_log": "evidence/verification-log.txt",
    "format_qa": "evidence/format-qa.md",
    "traversal_report": "deliverables/TRAVERSAL_REPORT.md",
}


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write_json(path: Path, value: dict) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    return _sha(path.read_bytes())


def valid_run(tmp_path: Path) -> dict:
    source_dir = tmp_path / "source"
    source_dir.mkdir(parents=True, exist_ok=True)
    source_path = source_dir / "source.html"
    source_path.write_text("<p>alpha</p>", encoding="utf-8")
    source_sha = _sha(source_path.read_bytes())
    source_uri = "https://www.rfc-editor.org/rfc/rfc9110.html"

    manifest_path = tmp_path / "evidence" / "chunk-manifest.json"
    extractor = Path(__file__).resolve().parents[1] / "scripts" / "extract_html.py"
    result = subprocess.run(
        [
            sys.executable, str(extractor), str(source_path),
            "--run-root", str(tmp_path),
            "--max-bytes", "4096",
            "--source-uri", source_uri,
        ],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert len(manifest["chunks"]) == 1
    chunk = manifest["chunks"][0]
    chunk_id = chunk["id"]
    manifest_sha = _sha(manifest_path.read_bytes())

    evidence_path = tmp_path / "evidence" / "chunk-evidence.json"
    _write_json(evidence_path, {
        "schema_version": 1,
        "manifest_sha256": manifest_sha,
        "source_sha256": source_sha,
        "entries": [{
            "chunk_id": chunk_id,
            "ordinal": chunk["ordinal"],
            "chunk_sha256": chunk["content_sha256"],
            "outcome": "evidence",
            "assertions": [{
                "text": "alpha",
                "chunk_byte_start": chunk["content"].encode("utf-8").find(b"alpha"),
                "chunk_byte_end": chunk["content"].encode("utf-8").find(b"alpha") + len(b"alpha"),
            }],
            "constraints": [],
        }],
    })

    report_script = Path(__file__).resolve().parents[1] / "scripts" / "traversal_report.py"
    report_result = subprocess.run(
        [sys.executable, str(report_script), "--run-root", str(tmp_path)],
        capture_output=True, text=True, check=False,
    )
    assert report_result.returncode == 0, report_result.stdout + report_result.stderr

    for key, filename in REQUIRED_EVIDENCE_FILES.items():
        if key in {"chunk_ledger", "traversal_report"}:
            continue
        path = tmp_path / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("evidence\n", encoding="utf-8")

    return {
        "_ledger_path": str(tmp_path / "run.json"),
        "source": {
            "uri": source_uri,
            "local_path": str(source_path.resolve()),
            "sha256": source_sha,
            "format": "html",
            "authority": "primary",
            "identity_verified": True,
        },
        "fidelity": {"preserved": True, "substitutions": []},
        "preflight": {
            "skill_read": True,
            "required_references_read": True,
            "helper_help_read": True,
            "runtime_profile_resolved": True,
            "traversal_plan_ready": True,
        },
        "plan": {"path": "plan.md", "nodes": ["acquire", chunk_id]},
        "events": [
            {"type": "plan_written"},
            {"type": "execution_started"},
            {"type": "node_started", "node": "acquire"},
            {"type": "node_passed", "node": "acquire", "evidence": "evidence/source-manifest.md"},
            {"type": "node_started", "node": chunk_id},
            {"type": "chunk_verified", "chunk_id": chunk_id, "chunk_sha256": chunk["content_sha256"], "evidence": "evidence/chunk-evidence.json"},
            {"type": "node_passed", "node": chunk_id, "evidence": "evidence/chunk-evidence.json"},
            {"type": "verification_started"},
            {"type": "verification_passed", "evidence": "evidence/verification-log.txt"},
            {"type": "done"},
        ],
        "chunking": {
            "manifest": "evidence/chunk-manifest.json",
            "manifest_sha256": manifest_sha,
            "evidence_ledger": "evidence/chunk-evidence.json",
            "traversal_report": "deliverables/TRAVERSAL_REPORT.md",
        },
        "coverage": {"required": [chunk_id], "completed": [chunk_id]},
        "qa": {"required": ["html-structure"], "passed": ["html-structure"]},
        "deliverable": {"requested": "answer", "provided": True, "paths": [], "traversal_report": "deliverables/TRAVERSAL_REPORT.md"},
        "evidence": dict(REQUIRED_EVIDENCE_FILES),
    }
