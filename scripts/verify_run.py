#!/usr/bin/env python3
"""Validate a deeper-reading execution ledger.

Standard-library only. Returns exit 0 when every required workflow predicate
passes; returns exit 1 and prints violations otherwise.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
from chunk_common import canonical_run_paths, render_traversal_report

REQUIRED_PREFLIGHT = (
    "skill_read",
    "required_references_read",
    "helper_help_read",
    "runtime_profile_resolved",
    "traversal_plan_ready",
)

LEGACY_PREFLIGHT = (
    "using_superpowers_read",
    "superpowers_list_consumed",
    "applicable_skills_read",
    "live_dependencies_read",
)

LEGACY_PROCESS_EVENTS = {"systematic_debugging", "brainstorming"}

MAX_VERIFIED_CHUNK_BYTES = 12000

EXTRACTOR_SCRIPTS = {
    "html": "extract_html.py",
    "markdown": "extract_markdown.py",
    "docx": "extract_docx.py",
    "pdf": "extract_pdf.py",
}

REQUIRED_EVIDENCE = (
    "plan_status",
    "skill_preflight",
    "source_manifest",
    "chunk_ledger",
    "failure_ledger",
    "verification_log",
    "format_qa",
    "traversal_report",
)



def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _resolve_path(base_dir: Path, raw: Any) -> Path:
    path = Path(str(raw))
    return path if path.is_absolute() else base_dir / path


def _resolved(path: Path) -> Path:
    return path.resolve(strict=False)


def _is_within(path: Path, root: Path) -> bool:
    try:
        _resolved(path).relative_to(_resolved(root))
        return True
    except ValueError:
        return False


def _same_path(path: Path, expected: Path) -> bool:
    return _resolved(path) == _resolved(expected)


def _load_json_file(path: Path, label: str, errors: list[str]) -> dict[str, Any] | None:
    if not path.is_file():
        errors.append(f"{label} does not exist: {path}")
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        errors.append(f"{label} is not valid JSON: {exc}")
        return None
    if not isinstance(value, dict):
        errors.append(f"{label} must contain a JSON object")
        return None
    return value


def _reproduce_extraction_manifest(
    source_path: Path, manifest: dict[str, Any], errors: list[str]
) -> None:
    source_meta = manifest.get("source", {})
    chunking_meta = manifest.get("chunking", {})
    fmt = source_meta.get("format") if isinstance(source_meta, dict) else None
    script_name = EXTRACTOR_SCRIPTS.get(str(fmt))
    if script_name is None:
        errors.append(f"reproduced extraction unsupported format: {fmt}")
        return
    max_bytes = chunking_meta.get("max_bytes") if isinstance(chunking_meta, dict) else None
    if not isinstance(max_bytes, int) or not (1 <= max_bytes <= MAX_VERIFIED_CHUNK_BYTES):
        errors.append(
            f"chunk manifest max_bytes must be between 1 and {MAX_VERIFIED_CHUNK_BYTES}"
        )
        return

    script = Path(__file__).resolve().parent / script_name
    if not script.is_file():
        errors.append(f"reproduced extraction script is missing: {script}")
        return

    with tempfile.TemporaryDirectory(prefix="chunk-reproduce-") as tmp:
        out = Path(tmp) / "chunks.json"
        args = [
            sys.executable, str(script), str(source_path), "--out", str(out),
            "--max-bytes", str(max_bytes),
        ]
        source_uri = source_meta.get("uri") if isinstance(source_meta, dict) else None
        if isinstance(source_uri, str) and source_uri:
            args.extend(["--source-uri", source_uri])
        if fmt == "pdf":
            backend = chunking_meta.get("backend")
            if not isinstance(backend, str) or not backend:
                errors.append("chunk manifest PDF backend is required for reproduced extraction")
                return
            args.extend(["--backend", backend])
        result = subprocess.run(args, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            detail = (result.stderr or result.stdout).strip()
            errors.append(f"reproduced extraction failed: {detail}")
            return
        try:
            reproduced = json.loads(out.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            errors.append(f"reproduced extraction manifest is unreadable: {exc}")
            return
        if reproduced != manifest:
            errors.append("reproduced extraction manifest does not match supplied manifest")


def _validate_atomic_extracts(
    chunk_id: str, kind: str, values: Any, content_bytes: bytes, errors: list[str]
) -> int:
    if not isinstance(values, list):
        errors.append(f"chunk {chunk_id} {kind} must be a list of atomic extractive assertions")
        return 0
    valid = 0
    singular = "assertion" if kind == "assertions" else "constraint"
    for index, atom in enumerate(values, start=1):
        if not isinstance(atom, dict):
            errors.append(f"chunk {chunk_id} {singular} {index} must be an atomic extractive assertion object")
            continue
        text = atom.get("text")
        start = atom.get("chunk_byte_start")
        end = atom.get("chunk_byte_end")
        if not isinstance(text, str) or not text.strip() or not isinstance(start, int) or not isinstance(end, int):
            errors.append(f"chunk {chunk_id} {singular} {index} must be an atomic extractive assertion with text and byte span")
            continue
        if start < 0 or end <= start or end > len(content_bytes):
            errors.append(f"chunk {chunk_id} {singular} {index} has invalid extractive byte span")
            continue
        if content_bytes[start:end] != text.encode("utf-8"):
            errors.append(f"chunk {chunk_id} {singular} {index} extractive span does not match chunk bytes")
            continue
        valid += 1
    return valid


def _validate_chunk_evidence(
    run: dict[str, Any], base_dir: Path, errors: list[str]
) -> tuple[list[str], list[str]]:
    """Validate extractor manifest + evidence ledger as the coverage authority.

    Returns (manifest_chunk_ids, evidenced_chunk_ids). Empty lists mean the
    authority could not be established; callers must not infer coverage.
    """
    chunking = run.get("chunking")
    if not isinstance(chunking, dict):
        errors.append("chunking contract is required")
        return [], []

    raw_manifest_path = chunking.get("manifest")
    raw_manifest_sha = chunking.get("manifest_sha256")
    raw_evidence_path = chunking.get("evidence_ledger")
    if not isinstance(raw_manifest_path, str) or not raw_manifest_path.strip():
        errors.append("chunking.manifest is required")
        return [], []
    if not isinstance(raw_manifest_sha, str) or not raw_manifest_sha.strip():
        errors.append("chunking.manifest_sha256 is required")
        return [], []
    if not isinstance(raw_evidence_path, str) or not raw_evidence_path.strip():
        errors.append("chunking.evidence_ledger is required")
        return [], []

    manifest_path = _resolve_path(base_dir, raw_manifest_path)
    evidence_path = _resolve_path(base_dir, raw_evidence_path)
    manifest = _load_json_file(manifest_path, "chunking.manifest", errors)
    ledger = _load_json_file(evidence_path, "chunking.evidence_ledger", errors)
    if manifest is None or ledger is None:
        return [], []

    actual_manifest_sha = _sha256_bytes(manifest_path.read_bytes())
    if actual_manifest_sha != raw_manifest_sha:
        errors.append("chunking.manifest_sha256 does not match manifest bytes")

    source = run.get("source", {})
    run_format = source.get("format")
    run_source_sha = source.get("sha256")
    run_source_uri = source.get("uri")
    raw_local_path = source.get("local_path")
    if not isinstance(run_source_sha, str) or not run_source_sha.strip():
        errors.append("source.sha256 is required for chunk coverage")
    if not isinstance(raw_local_path, str) or not raw_local_path.strip():
        errors.append("source.local_path is required for chunk coverage")
        source_path = None
    else:
        source_path = _resolve_path(base_dir, raw_local_path)
        if not source_path.is_file():
            errors.append(f"source.local_path does not exist: {source_path}")
        elif isinstance(run_source_sha, str) and run_source_sha:
            actual_source_sha = _sha256_bytes(source_path.read_bytes())
            if actual_source_sha != run_source_sha:
                errors.append("source sha256 does not match local source bytes")

    manifest_source = manifest.get("source", {})
    if not isinstance(manifest_source, dict):
        errors.append("chunk manifest source must be an object")
        manifest_source = {}
    if manifest_source.get("sha256") != run_source_sha:
        errors.append("chunk manifest source sha256 does not match run source sha256")
    if manifest_source.get("format") != run_format:
        errors.append("chunk manifest source format does not match run source format")
    if manifest_source.get("uri") != run_source_uri:
        errors.append("chunk manifest source uri does not match run source uri")

    if source_path is not None and source_path.is_file():
        _reproduce_extraction_manifest(source_path, manifest, errors)

    if manifest.get("schema_version") != 1:
        errors.append("chunk manifest schema_version must be 1")
    chunks = manifest.get("chunks")
    if not isinstance(chunks, list):
        errors.append("chunk manifest chunks must be a list")
        return [], []
    chunking_meta = manifest.get("chunking", {})
    if not isinstance(chunking_meta, dict) or chunking_meta.get("chunk_count") != len(chunks):
        errors.append("chunk manifest chunk_count does not match emitted chunks")

    manifest_ids: list[str] = []
    manifest_by_id: dict[str, dict[str, Any]] = {}
    cursor = 0
    stream = bytearray()
    for expected_ordinal, raw_chunk in enumerate(chunks, start=1):
        if not isinstance(raw_chunk, dict):
            errors.append(f"chunk manifest entry {expected_ordinal} must be an object")
            continue
        chunk_id = raw_chunk.get("id")
        if not isinstance(chunk_id, str) or not chunk_id:
            errors.append(f"chunk manifest entry {expected_ordinal} missing id")
            continue
        if chunk_id in manifest_by_id:
            errors.append(f"duplicate chunk id in manifest: {chunk_id}")
            continue
        manifest_ids.append(chunk_id)
        manifest_by_id[chunk_id] = raw_chunk
        if raw_chunk.get("ordinal") != expected_ordinal:
            errors.append(f"manifest chunk ordinal mismatch: {chunk_id}")
        content = raw_chunk.get("content")
        if not isinstance(content, str):
            errors.append(f"manifest chunk content must be text: {chunk_id}")
            content = ""
        content_bytes = content.encode("utf-8")
        max_bytes = chunking_meta.get("max_bytes") if isinstance(chunking_meta, dict) else None
        if isinstance(max_bytes, int):
            if len(content_bytes) > max_bytes and raw_chunk.get("oversize_atomic") is not True:
                errors.append(f"non-atomic chunk exceeds max_bytes: {chunk_id}")
            if raw_chunk.get("oversize_atomic") is True and not raw_chunk.get("locator", {}).get("atomic_kind"):
                errors.append(f"oversize_atomic chunk lacks atomic_kind: {chunk_id}")
        expected_hash = _sha256_bytes(content_bytes)
        if raw_chunk.get("content_sha256") != expected_hash:
            errors.append(f"manifest chunk content hash mismatch: {chunk_id}")
        if raw_chunk.get("text_byte_start") != cursor:
            errors.append(f"manifest chunk byte start is not contiguous: {chunk_id}")
        expected_end = cursor + len(content_bytes)
        if raw_chunk.get("text_byte_end") != expected_end:
            errors.append(f"manifest chunk byte end mismatch: {chunk_id}")
        cursor = expected_end
        stream.extend(content_bytes)

    if manifest.get("extracted_text_bytes") != cursor:
        errors.append("chunk manifest extracted_text_bytes does not match chunk stream")
    if manifest.get("extracted_text_sha256") != _sha256_bytes(bytes(stream)):
        errors.append("chunk manifest extracted_text_sha256 does not match chunk stream")

    if ledger.get("schema_version") != 1:
        errors.append("chunk evidence schema_version must be 1")
    if ledger.get("manifest_sha256") != actual_manifest_sha:
        errors.append("chunk evidence manifest_sha256 does not match manifest bytes")
    if ledger.get("source_sha256") != manifest_source.get("sha256"):
        errors.append("chunk evidence source_sha256 does not match manifest source sha256")
    entries = ledger.get("entries")
    if not isinstance(entries, list):
        errors.append("chunk evidence entries must be a list")
        return manifest_ids, []

    seen: set[str] = set()
    evidenced_ids: list[str] = []
    for raw_entry in entries:
        if not isinstance(raw_entry, dict):
            errors.append("chunk evidence entry must be an object")
            continue
        chunk_id = raw_entry.get("chunk_id")
        if not isinstance(chunk_id, str) or not chunk_id:
            errors.append("chunk evidence entry missing chunk_id")
            continue
        if chunk_id in seen:
            errors.append(f"duplicate evidence for chunk: {chunk_id}")
            continue
        seen.add(chunk_id)
        if chunk_id not in manifest_by_id:
            errors.append(f"evidence references unknown chunk: {chunk_id}")
            continue
        chunk = manifest_by_id[chunk_id]
        if raw_entry.get("ordinal") != chunk.get("ordinal"):
            errors.append(f"chunk evidence ordinal mismatch: {chunk_id}")
        if raw_entry.get("chunk_sha256") != chunk.get("content_sha256"):
            errors.append(f"chunk evidence hash mismatch: {chunk_id}")
        outcome = raw_entry.get("outcome")
        if outcome == "evidence":
            content_bytes = str(chunk.get("content", "")).encode("utf-8")
            assertions = raw_entry.get("assertions", [])
            constraints = raw_entry.get("constraints", [])
            valid_atoms = _validate_atomic_extracts(chunk_id, "assertions", assertions, content_bytes, errors)
            valid_atoms += _validate_atomic_extracts(chunk_id, "constraints", constraints, content_bytes, errors)
            if valid_atoms == 0:
                errors.append(
                    f"chunk {chunk_id} must record assertions/constraints or explicit non_match"
                )
        elif outcome == "non_match":
            reason = raw_entry.get("reason")
            if not isinstance(reason, str) or not reason.strip():
                errors.append(f"chunk {chunk_id} non_match requires a reason")
        else:
            errors.append(
                f"chunk {chunk_id} must record assertions/constraints or explicit non_match"
            )
        evidenced_ids.append(chunk_id)

    for chunk_id in manifest_ids:
        if chunk_id not in seen:
            errors.append(f"missing evidence for emitted chunk: {chunk_id}")

    raw_report_path = chunking.get("traversal_report")
    if not isinstance(raw_report_path, str) or not raw_report_path.strip():
        errors.append("chunking.traversal_report is required")
    else:
        report_path = _resolve_path(base_dir, raw_report_path)
        if not report_path.is_file():
            errors.append(f"traversal report does not exist: {report_path}")
        else:
            expected_report = render_traversal_report(manifest, ledger)
            try:
                actual_report = report_path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError) as exc:
                errors.append(f"traversal report is unreadable: {exc}")
            else:
                if actual_report != expected_report:
                    errors.append("traversal report does not match canonical manifest/evidence rendering")

    coverage = run.get("coverage")
    if coverage is not None:
        if not isinstance(coverage, dict):
            errors.append("coverage must be an object when present")
        else:
            required = coverage.get("required")
            completed = coverage.get("completed")
            if required != manifest_ids:
                errors.append("coverage.required must exactly mirror manifest chunk ids")
            if completed != manifest_ids or evidenced_ids != manifest_ids:
                errors.append("coverage.completed must exactly mirror evidenced manifest chunk ids")

    return manifest_ids, evidenced_ids

def _validate_run_root_paths(run: dict[str, Any], base_dir: Path, errors: list[str]) -> None:
    run_root = _resolved(base_dir)
    canonical = canonical_run_paths(run_root)
    ledger_path = _resolved(Path(str(run.get("_ledger_path", run_root / "run.json"))))
    if not _same_path(ledger_path, run_root / "run.json"):
        errors.append("run ledger must be <run-root>/run.json")

    plan = run.get("plan", {})
    raw_plan = plan.get("path") if isinstance(plan, dict) else None
    if isinstance(raw_plan, str) and raw_plan.strip():
        if not _same_path(_resolve_path(run_root, raw_plan), run_root / "plan.md"):
            errors.append("plan.path must be <run-root>/plan.md")

    chunking = run.get("chunking", {})
    if isinstance(chunking, dict):
        raw_manifest = chunking.get("manifest")
        if isinstance(raw_manifest, str) and raw_manifest.strip():
            if not _same_path(_resolve_path(run_root, raw_manifest), canonical["manifest"]):
                errors.append("chunking.manifest must be <run-root>/evidence/chunk-manifest.json")
        raw_ledger = chunking.get("evidence_ledger")
        if isinstance(raw_ledger, str) and raw_ledger.strip():
            if not _same_path(_resolve_path(run_root, raw_ledger), canonical["chunk_evidence"]):
                errors.append("chunking.evidence_ledger must be <run-root>/evidence/chunk-evidence.json")
        raw_report = chunking.get("traversal_report")
        if isinstance(raw_report, str) and raw_report.strip():
            if not _same_path(_resolve_path(run_root, raw_report), canonical["traversal_report"]):
                errors.append("chunking.traversal_report must be <run-root>/deliverables/TRAVERSAL_REPORT.md")

    evidence = run.get("evidence", {})
    expected_evidence = {
        "plan_status": run_root / "plan.md",
        "skill_preflight": run_root / "evidence" / "skill-preflight.md",
        "source_manifest": run_root / "evidence" / "source-manifest.md",
        "chunk_ledger": canonical["chunk_evidence"],
        "failure_ledger": run_root / "evidence" / "failure-ledger.md",
        "verification_log": run_root / "evidence" / "verification-log.txt",
        "format_qa": run_root / "evidence" / "format-qa.md",
        "traversal_report": canonical["traversal_report"],
    }
    if isinstance(evidence, dict):
        for key, expected in expected_evidence.items():
            raw = evidence.get(key)
            if not isinstance(raw, str) or not raw.strip():
                continue
            actual = _resolve_path(run_root, raw)
            if _same_path(actual, expected):
                continue
            if key == "plan_status":
                errors.append("evidence.plan_status must be <run-root>/plan.md")
            elif key == "traversal_report":
                errors.append("evidence.traversal_report must be <run-root>/deliverables/TRAVERSAL_REPORT.md")
            else:
                errors.append(f"evidence.{key} must live under <run-root>/evidence at its canonical path")

    deliverable = run.get("deliverable", {})
    if isinstance(deliverable, dict):
        raw_report = deliverable.get("traversal_report")
        if isinstance(raw_report, str) and raw_report.strip():
            if not _same_path(_resolve_path(run_root, raw_report), canonical["traversal_report"]):
                errors.append("deliverable.traversal_report must be <run-root>/deliverables/TRAVERSAL_REPORT.md")
        for raw_path in deliverable.get("paths", []) or []:
            path = _resolve_path(run_root, raw_path)
            if not _is_within(path, run_root / "deliverables"):
                errors.append("deliverable path must live under <run-root>/deliverables")


def _event_types(run: dict[str, Any]) -> list[str]:
    return [str(e.get("type", "")) for e in run.get("events", [])]


def _node_is_resolved(events: list[dict[str, Any]], node: str) -> bool:
    return any(
        e.get("node") == node and e.get("type") in {"node_passed", "node_superseded"}
        for e in events
    )


def validate_run(run: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    source = run.get("source", {})
    if not source.get("uri"):
        errors.append("source.uri is required")
    if source.get("format") not in {"html", "pdf", "docx", "markdown"}:
        errors.append("source.format must be html, pdf, docx, or markdown")
    if source.get("authority") not in {"primary", "approved-secondary"}:
        errors.append("source.authority must be primary or approved-secondary")
    if source.get("identity_verified") is not True:
        errors.append("source.identity_verified must be true")

    if "fidelity" not in run:
        errors.append("fidelity contract is required")
        fidelity = {}
    else:
        fidelity = run.get("fidelity", {})
    if fidelity.get("preserved") is not True:
        errors.append("source fidelity must be preserved")
    substitutions = fidelity.get("substitutions", [])
    if not isinstance(substitutions, list):
        errors.append("fidelity.substitutions must be a list")

    preflight = run.get("preflight", {})
    for key in REQUIRED_PREFLIGHT:
        if preflight.get(key) is not True:
            errors.append(f"preflight.{key} must be true")

    plan = run.get("plan", {})
    nodes = plan.get("nodes") or []
    if not plan.get("path"):
        errors.append("plan.path is required")
    if not isinstance(nodes, list) or not nodes:
        errors.append("plan.nodes must contain at least one node")

    deliverable = run.get("deliverable", {})
    if not deliverable.get("requested"):
        errors.append("deliverable.requested is required")
    if deliverable.get("provided") is not True:
        errors.append("deliverable.provided must be true")
    traversal_report = deliverable.get("traversal_report")
    if not isinstance(traversal_report, str) or not traversal_report.strip():
        errors.append("deliverable.traversal_report is required for user-visible traversal proof")

    ledger_path = Path(str(run.get("_ledger_path", "run.json")))
    base_dir = ledger_path.parent if str(ledger_path.parent) not in {"", "."} else Path.cwd()
    _validate_run_root_paths(run, base_dir, errors)

    if plan.get("path"):
        plan_path = Path(str(plan["path"]))
        if not plan_path.is_absolute():
            plan_path = base_dir / plan_path
        if not plan_path.is_file():
            errors.append(f"plan.path does not exist: {plan_path}")

    manifest_chunk_ids, evidenced_chunk_ids = _validate_chunk_evidence(run, base_dir, errors)

    if "qa" not in run:
        errors.append("qa contract is required")
        qa = {}
    else:
        qa = run.get("qa", {})
    required_qa = qa.get("required", [])
    passed_qa = qa.get("passed", [])
    if not isinstance(required_qa, list) or not isinstance(passed_qa, list):
        errors.append("qa.required and qa.passed must be lists")
    else:
        missing_qa = [q for q in required_qa if q not in passed_qa]
        for check in missing_qa:
            errors.append(f"qa missing required check: {check}")

    evidence = run.get("evidence", {})
    for key in REQUIRED_EVIDENCE:
        value = evidence.get(key)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"evidence.{key} must be a file path")
            continue
        evidence_path = Path(value)
        if not evidence_path.is_absolute():
            evidence_path = base_dir / evidence_path
        if not evidence_path.is_file():
            errors.append(f"evidence.{key} does not exist: {evidence_path}")

    chunking_report = run.get("chunking", {}).get("traversal_report") if isinstance(run.get("chunking"), dict) else None
    evidence_report = evidence.get("traversal_report")
    deliverable_report = deliverable.get("traversal_report")
    if any(isinstance(x, str) and x.strip() for x in (chunking_report, evidence_report, deliverable_report)):
        if not (chunking_report == evidence_report == deliverable_report):
            errors.append("traversal report path must match across chunking, evidence, and deliverable contracts")

    for raw_path in deliverable.get("paths", []) or []:
        deliverable_path = Path(str(raw_path))
        if not deliverable_path.is_absolute():
            deliverable_path = base_dir / deliverable_path
        if not deliverable_path.is_file():
            errors.append(f"deliverable path does not exist: {deliverable_path}")

    events: list[dict[str, Any]] = run.get("events", [])
    types = _event_types(run)

    verified_events = [event for event in events if event.get("type") == "chunk_verified"]
    verified_event_ids = [str(event.get("chunk_id", "")) for event in verified_events]
    if manifest_chunk_ids:
        for chunk_id in manifest_chunk_ids:
            if chunk_id not in verified_event_ids:
                errors.append(f"missing chunk_verified event for emitted chunk: {chunk_id}")
        for chunk_id in verified_event_ids:
            if chunk_id not in manifest_chunk_ids:
                errors.append(f"chunk_verified references unknown chunk: {chunk_id}")
        if len(verified_event_ids) != len(set(verified_event_ids)):
            errors.append("duplicate chunk_verified event")
        if verified_event_ids and verified_event_ids != manifest_chunk_ids:
            errors.append("chunk_verified events must follow manifest order")
        if evidenced_chunk_ids == manifest_chunk_ids and verified_event_ids != evidenced_chunk_ids:
            errors.append("chunk_verified events must exactly mirror evidenced manifest chunks")

    if "plan_written" not in types:
        errors.append("events must include plan_written")
    if "execution_started" not in types:
        errors.append("events must include execution_started")

    if "execution_started" in types and "plan_written" in types:
        if types.index("execution_started") < types.index("plan_written"):
            errors.append("execution_started cannot precede plan_written")

    for key in LEGACY_PREFLIGHT:
        if key in preflight:
            errors.append(f"legacy preflight key is not allowed: {key}")

    for event in events:
        event_type = event.get("type")
        if event_type in LEGACY_PROCESS_EVENTS:
            errors.append(f"legacy process event is not allowed: {event_type}")

    diagnosis_barriers = {
        "node_started", "node_passed", "node_failed", "node_rechunked",
        "node_recovered", "node_superseded", "architecture_stop",
        "alternative_designed", "verification_started", "done",
    }
    for i, event in enumerate(events):
        if event.get("type") != "node_failed":
            continue
        failed_node = event.get("node")
        diagnosed = False
        for later in events[i + 1 :]:
            later_type = later.get("type")
            if later_type == "failure_diagnosed" and later.get("node") == failed_node:
                diagnosed = True
                break
            if later_type in diagnosis_barriers:
                break
        if not diagnosed:
            errors.append(
                f"node_failed({failed_node}) requires failure_diagnosed before traversal or repair"
            )

    repair_types = {"node_rechunked", "node_recovered", "node_passed", "node_started"}
    for i, event in enumerate(events):
        if event.get("type") != "architecture_stop":
            continue
        replanned = False
        for later in events[i + 1 :]:
            later_type = later.get("type")
            if later_type == "plan_revised":
                replanned = True
                break
            if later_type in repair_types:
                errors.append(
                    "architecture_stop blocks further repair/traversal until exhausted-path redesign and plan_revised"
                )
                break
        if not replanned and any(e.get("type") in repair_types for e in events[i + 1 :]):
            pass

    for i, event in enumerate(events):
        if event.get("type") != "alternative_designed":
            continue
        prior_types = [e.get("type") for e in events[:i]]
        required = ("architecture_stop", "paths_exhausted", "disclosure")
        if not all(name in prior_types for name in required):
            errors.append(
                "alternative_designed requires prior architecture_stop, paths_exhausted, and disclosure"
            )
        else:
            positions = [prior_types.index(name) for name in required]
            if positions != sorted(positions):
                errors.append(
                    "alternative_designed requires architecture_stop -> paths_exhausted -> disclosure ordering"
                )

    for i, event in enumerate(events):
        if event.get("type") != "plan_revised":
            continue
        if not any(e.get("type") == "alternative_designed" for e in events[:i]):
            errors.append("plan_revised requires prior alternative_designed")

    done_positions = [i for i, e in enumerate(events) if e.get("type") == "done"]
    if done_positions:
        done_i = done_positions[-1]
        prior_types = [e.get("type") for e in events[:done_i]]
        if "verification_started" not in prior_types:
            errors.append("done requires prior verification_started")
        if "verification_passed" not in prior_types:
            errors.append("done requires prior verification_passed")
        else:
            last_verification_pass = max(
                i for i, e in enumerate(events[:done_i]) if e.get("type") == "verification_passed"
            )
            material_types = {
                "node_passed", "node_recovered", "node_superseded",
                "node_rechunked", "failure_diagnosed", "architecture_stop",
                "paths_exhausted", "disclosure", "alternative_designed",
                "plan_revised", "chunk_verified"
            }
            material_positions = [
                i for i, e in enumerate(events[:done_i]) if e.get("type") in material_types
            ]
            if material_positions and last_verification_pass < max(material_positions):
                errors.append("verification_passed must follow the last material event")
        for node in nodes:
            if not _node_is_resolved(events[:done_i], str(node)):
                errors.append(f"done requires resolved plan node: {node}")

        unresolved_failures: set[str] = set()
        for e in events[:done_i]:
            if e.get("type") == "node_failed" and e.get("node"):
                unresolved_failures.add(str(e["node"]))
            if e.get("type") in {"node_recovered", "node_passed", "node_superseded"} and e.get("node"):
                unresolved_failures.discard(str(e["node"]))
        for node in sorted(unresolved_failures):
            errors.append(f"done with unresolved failed node: {node}")

    return errors


def build_dod(run: dict[str, Any], errors: list[str]) -> dict[str, Any]:
    events = run.get("events", [])
    verification_errors = [e for e in errors if "verification" in e]
    plan_errors = [e for e in errors if e.startswith("plan.") or "resolved plan node" in e]
    failure_errors = [
        e for e in errors
        if (
            "failure_diagnosed before traversal or repair" in e
            or "architecture_stop" in e
            or "alternative_designed" in e
            or "unresolved failed node" in e
        )
    ]
    fidelity_errors = [e for e in errors if e.startswith("fidelity") or "source fidelity" in e]
    deliverable_errors = [e for e in errors if e.startswith("deliverable")]
    containment_errors = [
        e for e in errors
        if (
            "<run-root>" in e
            and (
                e.startswith("run ledger")
                or e.startswith("plan.path")
                or e.startswith("chunking.")
                or e.startswith("evidence.")
                or e.startswith("deliverable")
            )
        )
    ]

    predicates = {
        "source_identity_verified": run.get("source", {}).get("identity_verified") is True,
        "skill_preflight_complete": all(
            run.get("preflight", {}).get(k) is True for k in REQUIRED_PREFLIGHT
        ),
        "plan_present": bool(run.get("plan", {}).get("path")) and bool(run.get("plan", {}).get("nodes")),
        "plan_resolved": not plan_errors,
        "output_containment_valid": not containment_errors,
        "source_coverage_complete": not any(
            token in e
            for e in errors
            for token in (
                "chunking", "chunk manifest", "manifest chunk", "chunk evidence",
                "missing evidence for emitted chunk", "duplicate evidence for chunk",
                "evidence references unknown chunk", "coverage.required", "coverage.completed",
                "source sha256",
            )
        ),
        "failure_protocol_respected": not failure_errors,
        "source_fidelity_preserved": run.get("fidelity", {}).get("preserved") is True and not fidelity_errors,
        "format_qa_complete": not any(e.startswith("qa ") or e.startswith("qa.") for e in errors),
        "requested_deliverable_produced": run.get("deliverable", {}).get("provided") is True and not deliverable_errors,
        "deliverable_provided": run.get("deliverable", {}).get("provided") is True and not deliverable_errors,
        "evidence_complete": not any(e.startswith("evidence.") for e in errors),
        "no_unresolved_required_failures": not any("unresolved failed node" in e for e in errors),
        "fresh_final_verification": any(
            e.get("type") == "verification_passed" for e in events
        ) and not verification_errors,
        "machine_checks_passed": not errors,
    }
    return {
        "passed": not errors,
        "violations": errors,
        "predicates": predicates,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a document-workflow run ledger")
    parser.add_argument("ledger", type=Path)
    parser.add_argument("--write-dod", type=Path)
    args = parser.parse_args()

    ledger = args.ledger.resolve()
    run_root = ledger.parent
    canonical_dod = canonical_run_paths(run_root)["dod"]
    if args.write_dod is not None and not _same_path(args.write_dod, canonical_dod):
        print("FAIL: dod.json must be written to <run-root>/dod.json")
        return 1

    run = json.loads(ledger.read_text(encoding="utf-8"))
    run["_ledger_path"] = str(ledger)
    errors = validate_run(run)
    dod = build_dod(run, errors)

    canonical_dod.parent.mkdir(parents=True, exist_ok=True)
    canonical_dod.write_text(json.dumps(dod, indent=2) + "\n", encoding="utf-8")

    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        return 1

    print("PASS: Definition of Done predicates satisfied")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
