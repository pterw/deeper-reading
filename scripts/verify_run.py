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
from evidence_atoms import atom_id as evidence_atom_id
from verification_findings import Finding

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
EXTRACTION_TIMEOUT_SECONDS = 60

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


def _load_json_file(path: Path, label: str, findings: list[Finding]) -> dict[str, Any] | None:
    if not path.is_file():
        findings.append(Finding(
            "json.file.missing", "machine_checks_passed",
            f"{label} does not exist: {path}", detail=str(path),
        ))
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        findings.append(Finding(
            "json.file.unreadable", "machine_checks_passed",
            f"{label} is not valid JSON: {exc}", detail=str(path),
        ))
        return None
    if not isinstance(value, dict):
        findings.append(Finding(
            "json.file.type", "machine_checks_passed",
            f"{label} must contain a JSON object",
        ))
        return None
    return value


def _mapping(value: Any, label: str, errors: list[Finding]) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    errors.append(Finding(
        "mapping.type", "machine_checks_passed", f"{label} must be an object",
        detail=label,
    ))
    return {}


def _reproduce_extraction_manifest(
    source_path: Path, manifest: dict[str, Any], findings: list[Finding]
) -> None:
    source_meta = manifest.get("source", {})
    chunking_meta = manifest.get("chunking", {})
    fmt = source_meta.get("format") if isinstance(source_meta, dict) else None
    script_name = EXTRACTOR_SCRIPTS.get(str(fmt))
    if script_name is None:
        findings.append(Finding(
            "reproduction.format.unsupported", "source_coverage_complete",
            f"reproduced extraction unsupported format: {fmt}", detail=str(fmt),
        ))
        return
    max_bytes = chunking_meta.get("max_bytes") if isinstance(chunking_meta, dict) else None
    if not isinstance(max_bytes, int) or not (1 <= max_bytes <= MAX_VERIFIED_CHUNK_BYTES):
        findings.append(Finding(
            "reproduction.max_bytes.invalid", "source_coverage_complete",
            f"chunk manifest max_bytes must be between 1 and {MAX_VERIFIED_CHUNK_BYTES}",
        ))
        return

    script = Path(__file__).resolve().parent / script_name
    if not script.is_file():
        findings.append(Finding(
            "reproduction.script.missing", "source_coverage_complete",
            f"reproduced extraction script is missing: {script}", detail=str(script),
        ))
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
                findings.append(Finding(
                    "reproduction.backend.required", "source_coverage_complete",
                    "chunk manifest PDF backend is required for reproduced extraction",
                ))
                return
            args.extend(["--backend", backend])
        try:
            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                check=False,
                timeout=EXTRACTION_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired:
            findings.append(Finding(
                "reproduction.timeout", "source_coverage_complete",
                f"reproduced extraction timed out after {EXTRACTION_TIMEOUT_SECONDS}s",
            ))
            return
        if result.returncode != 0:
            detail = (result.stderr or result.stdout).strip()
            findings.append(Finding(
                "reproduction.failed", "source_coverage_complete",
                f"reproduced extraction failed: {detail}",
            ))
            return
        try:
            reproduced = json.loads(out.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            findings.append(Finding(
                "reproduction.unreadable", "source_coverage_complete",
                f"reproduced extraction manifest is unreadable: {exc}",
            ))
            return
        if reproduced != manifest:
            findings.append(Finding(
                "reproduction.mismatch", "source_coverage_complete",
                "reproduced extraction manifest does not match supplied manifest",
            ))


def _validate_atomic_extracts(
    chunk_id: str,
    kind: str,
    values: Any,
    content_bytes: bytes,
    findings: list[Finding],
    schema_version: int,
    seen_atom_ids: set[str],
) -> int:
    if not isinstance(values, list):
        findings.append(Finding(
            "atoms.list.type", "source_coverage_complete",
            f"chunk {chunk_id} {kind} must be a list of atomic extractive assertions",
            detail=chunk_id,
        ))
        return 0
    valid = 0
    singular = "assertion" if kind == "assertions" else "constraint"
    for index, atom in enumerate(values, start=1):
        if not isinstance(atom, dict):
            findings.append(Finding(
                "atoms.entry.type", "source_coverage_complete",
                f"chunk {chunk_id} {singular} {index} must be an atomic extractive assertion object",
                detail=chunk_id,
            ))
            continue
        text = atom.get("text")
        start = atom.get("chunk_byte_start")
        end = atom.get("chunk_byte_end")
        if not isinstance(text, str) or not text.strip() or not isinstance(start, int) or not isinstance(end, int):
            findings.append(Finding(
                "atoms.span.missing", "source_coverage_complete",
                f"chunk {chunk_id} {singular} {index} must be an atomic extractive assertion with text and byte span",
                detail=chunk_id,
            ))
            continue
        if start < 0 or end <= start or end > len(content_bytes):
            findings.append(Finding(
                "atoms.span.invalid", "source_coverage_complete",
                f"chunk {chunk_id} {singular} {index} has invalid extractive byte span",
                detail=chunk_id,
            ))
            continue
        if content_bytes[start:end] != text.encode("utf-8"):
            findings.append(Finding(
                "atoms.span.mismatch", "source_coverage_complete",
                f"chunk {chunk_id} {singular} {index} extractive span does not match chunk bytes",
                detail=chunk_id,
            ))
            continue
        if schema_version == 2:
            raw_atom_id = atom.get("atom_id")
            if not isinstance(raw_atom_id, str) or not raw_atom_id:
                findings.append(Finding(
                    "atoms.atom_id.required", "source_coverage_complete",
                    f"chunk {chunk_id} {singular} {index} atom_id is required for schema v2",
                    detail=chunk_id,
                ))
                continue
            if raw_atom_id in seen_atom_ids:
                findings.append(Finding(
                    "atoms.atom_id.duplicate", "source_coverage_complete",
                    f"duplicate atom_id: {raw_atom_id}", detail=raw_atom_id,
                ))
                continue
            expected_atom_id = evidence_atom_id(chunk_id, singular, start, end, text)
            if raw_atom_id != expected_atom_id:
                findings.append(Finding(
                    "atoms.atom_id.mismatch", "source_coverage_complete",
                    f"chunk {chunk_id} {singular} {index} atom_id does not match deterministic identity",
                    detail=chunk_id,
                ))
                continue
            seen_atom_ids.add(raw_atom_id)
        valid += 1
    return valid


def _validate_chunk_evidence(
    run: dict[str, Any], base_dir: Path, findings: list[Finding]
) -> tuple[list[str], list[str]]:
    """Validate extractor manifest + evidence ledger as the coverage authority.

    Returns (manifest_chunk_ids, evidenced_chunk_ids). Empty lists mean the
    authority could not be established; callers must not infer coverage.
    """
    if "chunking" not in run:
        findings.append(Finding(
            "chunking.required", "source_coverage_complete",
            "chunking contract is required",
        ))
        return [], []
    chunking = run.get("chunking")
    if not isinstance(chunking, dict):
        findings.append(Finding(
            "chunking.type", "source_coverage_complete",
            "chunking must be an object",
        ))
        return [], []

    raw_manifest_path = chunking.get("manifest")
    raw_manifest_sha = chunking.get("manifest_sha256")
    raw_evidence_path = chunking.get("evidence_ledger")
    if not isinstance(raw_manifest_path, str) or not raw_manifest_path.strip():
        findings.append(Finding(
            "coverage.manifest_path.required", "source_coverage_complete",
            "chunking.manifest is required",
        ))
        return [], []
    if not isinstance(raw_manifest_sha, str) or not raw_manifest_sha.strip():
        findings.append(Finding(
            "coverage.manifest_sha.missing", "source_coverage_complete",
            "chunking.manifest_sha256 is required",
        ))
        return [], []
    if not isinstance(raw_evidence_path, str) or not raw_evidence_path.strip():
        findings.append(Finding(
            "coverage.evidence_path.required", "source_coverage_complete",
            "chunking.evidence_ledger is required",
        ))
        return [], []

    manifest_path = _resolve_path(base_dir, raw_manifest_path)
    evidence_path = _resolve_path(base_dir, raw_evidence_path)
    manifest = _load_json_file(manifest_path, "chunking.manifest", findings)
    ledger = _load_json_file(evidence_path, "chunking.evidence_ledger", findings)
    if manifest is None or ledger is None:
        return [], []

    actual_manifest_sha = _sha256_bytes(manifest_path.read_bytes())
    if actual_manifest_sha != raw_manifest_sha:
        findings.append(Finding(
            "coverage.manifest_sha.mismatch", "source_coverage_complete",
            "chunking.manifest_sha256 does not match manifest bytes",
        ))

    source = _mapping(run.get("source"), "source", findings)
    run_format = source.get("format")
    run_source_sha = source.get("sha256")
    run_source_uri = source.get("uri")
    raw_local_path = source.get("local_path")
    if not isinstance(run_source_sha, str) or not run_source_sha.strip():
        findings.append(Finding(
            "coverage.source_sha.missing", "source_coverage_complete",
            "source.sha256 is required for chunk coverage",
        ))
    if not isinstance(raw_local_path, str) or not raw_local_path.strip():
        findings.append(Finding(
            "coverage.source_local_path.missing", "source_coverage_complete",
            "source.local_path is required for chunk coverage",
        ))
        source_path = None
    else:
        source_path = _resolve_path(base_dir, raw_local_path)
        if not source_path.is_file():
            findings.append(Finding(
                "coverage.source_local_path.missing", "source_coverage_complete",
                f"source.local_path does not exist: {source_path}",
                detail=str(source_path),
            ))
        elif isinstance(run_source_sha, str) and run_source_sha:
            actual_source_sha = _sha256_bytes(source_path.read_bytes())
            if actual_source_sha != run_source_sha:
                findings.append(Finding(
                    "coverage.source_sha.mismatch", "source_coverage_complete",
                    "source sha256 does not match local source bytes",
                ))

    manifest_source = manifest.get("source", {})
    if not isinstance(manifest_source, dict):
        findings.append(Finding(
            "coverage.manifest_source.type", "source_coverage_complete",
            "chunk manifest source must be an object",
        ))
        manifest_source = {}
    if manifest_source.get("sha256") != run_source_sha:
        findings.append(Finding(
            "coverage.manifest_source.sha.mismatch", "source_coverage_complete",
            "chunk manifest source sha256 does not match run source sha256",
        ))
    if manifest_source.get("format") != run_format:
        findings.append(Finding(
            "coverage.manifest_source.format.mismatch", "source_coverage_complete",
            "chunk manifest source format does not match run source format",
        ))
    if manifest_source.get("uri") != run_source_uri:
        findings.append(Finding(
            "coverage.manifest_source.uri.mismatch", "source_coverage_complete",
            "chunk manifest source uri does not match run source uri",
        ))

    if source_path is not None and source_path.is_file():
        _reproduce_extraction_manifest(source_path, manifest, findings)

    if manifest.get("schema_version") != 1:
        findings.append(Finding(
            "coverage.manifest.schema_version", "source_coverage_complete",
            "chunk manifest schema_version must be 1",
        ))
    chunks = manifest.get("chunks")
    if not isinstance(chunks, list):
        findings.append(Finding(
            "coverage.manifest.chunks.type", "source_coverage_complete",
            "chunk manifest chunks must be a list",
        ))
        return [], []
    chunking_meta = manifest.get("chunking", {})
    if not isinstance(chunking_meta, dict) or chunking_meta.get("chunk_count") != len(chunks):
        findings.append(Finding(
            "coverage.manifest.chunk_count", "source_coverage_complete",
            "chunk manifest chunk_count does not match emitted chunks",
        ))

    manifest_ids: list[str] = []
    manifest_by_id: dict[str, dict[str, Any]] = {}
    cursor = 0
    stream = bytearray()
    for expected_ordinal, raw_chunk in enumerate(chunks, start=1):
        if not isinstance(raw_chunk, dict):
            findings.append(Finding(
                "coverage.chunk.type", "source_coverage_complete",
                f"chunk manifest entry {expected_ordinal} must be an object",
            ))
            continue
        chunk_id = raw_chunk.get("id")
        if not isinstance(chunk_id, str) or not chunk_id:
            findings.append(Finding(
                "coverage.chunk.id.missing", "source_coverage_complete",
                f"chunk manifest entry {expected_ordinal} missing id",
            ))
            continue
        if chunk_id in manifest_by_id:
            findings.append(Finding(
                "coverage.chunk.id.duplicate", "source_coverage_complete",
                f"duplicate chunk id in manifest: {chunk_id}", detail=chunk_id,
            ))
            continue
        manifest_ids.append(chunk_id)
        manifest_by_id[chunk_id] = raw_chunk
        if raw_chunk.get("ordinal") != expected_ordinal:
            findings.append(Finding(
                "coverage.chunk.ordinal.mismatch", "source_coverage_complete",
                f"manifest chunk ordinal mismatch: {chunk_id}", detail=chunk_id,
            ))
        content = raw_chunk.get("content")
        if not isinstance(content, str):
            findings.append(Finding(
                "coverage.chunk.content.type", "source_coverage_complete",
                f"manifest chunk content must be text: {chunk_id}", detail=chunk_id,
            ))
            content = ""
        content_bytes = content.encode("utf-8")
        max_bytes = chunking_meta.get("max_bytes") if isinstance(chunking_meta, dict) else None
        if isinstance(max_bytes, int):
            if len(content_bytes) > max_bytes and raw_chunk.get("oversize_atomic") is not True:
                findings.append(Finding(
                    "coverage.chunk.oversize", "source_coverage_complete",
                    f"non-atomic chunk exceeds max_bytes: {chunk_id}", detail=chunk_id,
                ))
            if raw_chunk.get("oversize_atomic") is True and not raw_chunk.get("locator", {}).get("atomic_kind"):
                findings.append(Finding(
                    "coverage.chunk.atomic_kind.missing", "source_coverage_complete",
                    f"oversize_atomic chunk lacks atomic_kind: {chunk_id}", detail=chunk_id,
                ))
        expected_hash = _sha256_bytes(content_bytes)
        if raw_chunk.get("content_sha256") != expected_hash:
            findings.append(Finding(
                "coverage.chunk.content_sha.mismatch", "source_coverage_complete",
                f"manifest chunk content hash mismatch: {chunk_id}", detail=chunk_id,
            ))
        if raw_chunk.get("text_byte_start") != cursor:
            findings.append(Finding(
                "coverage.chunk.byte_start.not_contiguous", "source_coverage_complete",
                f"manifest chunk byte start is not contiguous: {chunk_id}", detail=chunk_id,
            ))
        expected_end = cursor + len(content_bytes)
        if raw_chunk.get("text_byte_end") != expected_end:
            findings.append(Finding(
                "coverage.chunk.byte_end.mismatch", "source_coverage_complete",
                f"manifest chunk byte end mismatch: {chunk_id}", detail=chunk_id,
            ))
        cursor = expected_end
        stream.extend(content_bytes)

    if manifest.get("extracted_text_bytes") != cursor:
        findings.append(Finding(
            "coverage.manifest.text_bytes.mismatch", "source_coverage_complete",
            "chunk manifest extracted_text_bytes does not match chunk stream",
        ))
    if manifest.get("extracted_text_sha256") != _sha256_bytes(bytes(stream)):
        findings.append(Finding(
            "coverage.manifest.text_sha.mismatch", "source_coverage_complete",
            "chunk manifest extracted_text_sha256 does not match chunk stream",
        ))

    schema_version = ledger.get("schema_version")
    if schema_version not in {1, 2}:
        findings.append(Finding(
            "coverage.ledger.schema_version", "source_coverage_complete",
            "chunk evidence schema_version must be 1 or 2",
        ))
        schema_version = 0
    if ledger.get("manifest_sha256") != actual_manifest_sha:
        findings.append(Finding(
            "coverage.ledger.manifest_sha.mismatch", "source_coverage_complete",
            "chunk evidence manifest_sha256 does not match manifest bytes",
        ))
    if ledger.get("source_sha256") != manifest_source.get("sha256"):
        findings.append(Finding(
            "coverage.ledger.source_sha.mismatch", "source_coverage_complete",
            "chunk evidence source_sha256 does not match manifest source sha256",
        ))
    entries = ledger.get("entries")
    if not isinstance(entries, list):
        findings.append(Finding(
            "coverage.ledger.entries.type", "source_coverage_complete",
            "chunk evidence entries must be a list",
        ))
        return manifest_ids, []

    seen: set[str] = set()
    seen_atom_ids: set[str] = set()
    evidenced_ids: list[str] = []
    for raw_entry in entries:
        if not isinstance(raw_entry, dict):
            findings.append(Finding(
                "coverage.entry.type", "source_coverage_complete",
                "chunk evidence entry must be an object",
            ))
            continue
        chunk_id = raw_entry.get("chunk_id")
        if not isinstance(chunk_id, str) or not chunk_id:
            findings.append(Finding(
                "coverage.entry.chunk_id.missing", "source_coverage_complete",
                "chunk evidence entry missing chunk_id",
            ))
            continue
        if chunk_id in seen:
            findings.append(Finding(
                "coverage.entry.duplicate", "source_coverage_complete",
                f"duplicate evidence for chunk: {chunk_id}", detail=chunk_id,
            ))
            continue
        seen.add(chunk_id)
        if chunk_id not in manifest_by_id:
            findings.append(Finding(
                "coverage.entry.unknown_chunk", "source_coverage_complete",
                f"evidence references unknown chunk: {chunk_id}", detail=chunk_id,
            ))
            continue
        chunk = manifest_by_id[chunk_id]
        if raw_entry.get("ordinal") != chunk.get("ordinal"):
            findings.append(Finding(
                "coverage.entry.ordinal.mismatch", "source_coverage_complete",
                f"chunk evidence ordinal mismatch: {chunk_id}", detail=chunk_id,
            ))
        if raw_entry.get("chunk_sha256") != chunk.get("content_sha256"):
            findings.append(Finding(
                "coverage.entry.hash.mismatch", "source_coverage_complete",
                f"chunk evidence hash mismatch: {chunk_id}", detail=chunk_id,
            ))
        outcome = raw_entry.get("outcome")
        if outcome == "evidence":
            content_bytes = str(chunk.get("content", "")).encode("utf-8")
            assertions = raw_entry.get("assertions", [])
            constraints = raw_entry.get("constraints", [])
            valid_atoms = _validate_atomic_extracts(
                chunk_id, "assertions", assertions, content_bytes, findings,
                schema_version, seen_atom_ids,
            )
            valid_atoms += _validate_atomic_extracts(
                chunk_id, "constraints", constraints, content_bytes, findings,
                schema_version, seen_atom_ids,
            )
            if valid_atoms == 0:
                findings.append(Finding(
                    "coverage.entry.verdict.missing", "source_coverage_complete",
                    f"chunk {chunk_id} must record assertions/constraints or explicit non_match",
                    detail=chunk_id,
                ))
        elif outcome == "non_match":
            reason = raw_entry.get("reason")
            if not isinstance(reason, str) or not reason.strip():
                findings.append(Finding(
                    "coverage.entry.non_match.reason.missing",
                    "source_coverage_complete",
                    f"chunk {chunk_id} non_match requires a reason", detail=chunk_id,
                ))
        else:
            findings.append(Finding(
                "coverage.entry.outcome.invalid", "source_coverage_complete",
                f"chunk {chunk_id} must record assertions/constraints or explicit non_match",
                detail=chunk_id,
            ))
        evidenced_ids.append(chunk_id)

    for chunk_id in manifest_ids:
        if chunk_id not in seen:
            findings.append(Finding(
                "coverage.entry.missing", "source_coverage_complete",
                f"missing evidence for emitted chunk: {chunk_id}", detail=chunk_id,
            ))

    raw_report_path = chunking.get("traversal_report")
    if not isinstance(raw_report_path, str) or not raw_report_path.strip():
        findings.append(Finding(
            "coverage.report_path.required", "source_coverage_complete",
            "chunking.traversal_report is required",
        ))
    else:
        report_path = _resolve_path(base_dir, raw_report_path)
        if not report_path.is_file():
            findings.append(Finding(
                "coverage.report_path.missing", "source_coverage_complete",
                f"traversal report does not exist: {report_path}",
                detail=str(report_path),
            ))
        else:
            expected_report = render_traversal_report(manifest, ledger)
            try:
                actual_report = report_path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError) as exc:
                findings.append(Finding(
                    "coverage.report_path.unreadable", "source_coverage_complete",
                    f"traversal report is unreadable: {exc}",
                ))
            else:
                if actual_report != expected_report:
                    findings.append(Finding(
                        "coverage.report.mismatch", "source_coverage_complete",
                        "traversal report does not match canonical manifest/evidence rendering",
                    ))

    coverage = run.get("coverage")
    if coverage is not None:
        if not isinstance(coverage, dict):
            findings.append(Finding(
                "coverage.mirror.type", "source_coverage_complete",
                "coverage must be an object when present",
            ))
        else:
            required = coverage.get("required")
            completed = coverage.get("completed")
            if required != manifest_ids:
                findings.append(Finding(
                    "coverage.mirror.required.mismatch", "source_coverage_complete",
                    "coverage.required must exactly mirror manifest chunk ids",
                ))
            if completed != manifest_ids or evidenced_ids != manifest_ids:
                findings.append(Finding(
                    "coverage.mirror.completed.mismatch", "source_coverage_complete",
                    "coverage.completed must exactly mirror evidenced manifest chunk ids",
                ))

    return manifest_ids, evidenced_ids

def _validate_run_root_paths(run: dict[str, Any], base_dir: Path, findings: list[Finding]) -> None:
    run_root = _resolved(base_dir)
    canonical = canonical_run_paths(run_root)
    ledger_path = _resolved(Path(str(run.get("_ledger_path", run_root / "run.json"))))
    if not _same_path(ledger_path, run_root / "run.json"):
        findings.append(Finding(
            "containment.ledger", "output_containment_valid",
            "run ledger must be <run-root>/run.json",
        ))

    plan = run.get("plan", {})
    raw_plan = plan.get("path") if isinstance(plan, dict) else None
    if isinstance(raw_plan, str) and raw_plan.strip():
        if not _same_path(_resolve_path(run_root, raw_plan), run_root / "plan.md"):
            findings.append(Finding(
                "containment.plan", "output_containment_valid",
                "plan.path must be <run-root>/plan.md",
            ))

    chunking = run.get("chunking", {})
    if isinstance(chunking, dict):
        raw_manifest = chunking.get("manifest")
        if isinstance(raw_manifest, str) and raw_manifest.strip():
            if not _same_path(_resolve_path(run_root, raw_manifest), canonical["manifest"]):
                findings.append(Finding(
                    "containment.manifest", "output_containment_valid",
                    "chunking.manifest must be <run-root>/evidence/chunk-manifest.json",
                ))
        raw_ledger = chunking.get("evidence_ledger")
        if isinstance(raw_ledger, str) and raw_ledger.strip():
            if not _same_path(_resolve_path(run_root, raw_ledger), canonical["chunk_evidence"]):
                findings.append(Finding(
                    "containment.evidence_ledger", "output_containment_valid",
                    "chunking.evidence_ledger must be <run-root>/evidence/chunk-evidence.json",
                ))
        raw_report = chunking.get("traversal_report")
        if isinstance(raw_report, str) and raw_report.strip():
            if not _same_path(_resolve_path(run_root, raw_report), canonical["traversal_report"]):
                findings.append(Finding(
                    "containment.traversal_report", "output_containment_valid",
                    "chunking.traversal_report must be <run-root>/deliverables/TRAVERSAL_REPORT.md",
                ))

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
                findings.append(Finding(
                    "containment.plan_status", "output_containment_valid",
                    "evidence.plan_status must be <run-root>/plan.md",
                ))
            elif key == "traversal_report":
                findings.append(Finding(
                    "containment.traversal_report", "output_containment_valid",
                    "evidence.traversal_report must be <run-root>/deliverables/TRAVERSAL_REPORT.md",
                ))
            else:
                findings.append(Finding(
                    "containment.evidence", "output_containment_valid",
                    f"evidence.{key} must live under <run-root>/evidence at its canonical path",
                    detail=key,
                ))

    deliverable = run.get("deliverable", {})
    if isinstance(deliverable, dict):
        raw_report = deliverable.get("traversal_report")
        if isinstance(raw_report, str) and raw_report.strip():
            if not _same_path(_resolve_path(run_root, raw_report), canonical["traversal_report"]):
                findings.append(Finding(
                    "containment.deliverable.report", "output_containment_valid",
                    "deliverable.traversal_report must be <run-root>/deliverables/TRAVERSAL_REPORT.md",
                ))
        for raw_path in deliverable.get("paths", []) or []:
            path = _resolve_path(run_root, raw_path)
            if not _is_within(path, run_root / "deliverables"):
                findings.append(Finding(
                    "containment.deliverable.paths", "output_containment_valid",
                    "deliverable path must live under <run-root>/deliverables",
                    detail=str(path),
                ))


def _event_types(run: dict[str, Any]) -> list[str]:
    return [str(e.get("type", "")) for e in run.get("events", [])]


def _node_is_resolved(events: list[dict[str, Any]], node: str) -> bool:
    return any(
        e.get("node") == node and e.get("type") in {"node_passed", "node_superseded"}
        for e in events
    )


def validate_findings(run: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []

    source = _mapping(run.get("source"), "source", findings)
    if not source.get("uri"):
        findings.append(Finding(
            "source.uri.required", "source_identity_verified",
            "source.uri is required",
        ))
    if source.get("format") not in {"html", "pdf", "docx", "markdown"}:
        findings.append(Finding(
            "source.format.invalid", "source_identity_verified",
            "source.format must be html, pdf, docx, or markdown",
        ))
    if source.get("authority") not in {"primary", "approved-secondary"}:
        findings.append(Finding(
            "source.authority.invalid", "source_identity_verified",
            "source.authority must be primary or approved-secondary",
        ))
    if source.get("identity_verified") is not True:
        findings.append(Finding(
            "source.identity.unverified", "source_identity_verified",
            "source.identity_verified must be true",
        ))

    if "fidelity" not in run:
        findings.append(Finding(
            "fidelity.required", "source_fidelity_preserved",
            "fidelity contract is required",
        ))
        fidelity = {}
    else:
        fidelity = _mapping(run.get("fidelity"), "fidelity", findings)
    if fidelity.get("preserved") is not True:
        findings.append(Finding(
            "fidelity.preserved.required", "source_fidelity_preserved",
            "source fidelity must be preserved",
        ))
    substitutions = fidelity.get("substitutions", [])
    if not isinstance(substitutions, list):
        findings.append(Finding(
            "fidelity.substitutions.type", "source_fidelity_preserved",
            "fidelity.substitutions must be a list",
        ))

    preflight = _mapping(run.get("preflight"), "preflight", findings)
    for key in REQUIRED_PREFLIGHT:
        if preflight.get(key) is not True:
            findings.append(Finding(
                f"preflight.{key}.false", "skill_preflight_complete",
                f"preflight.{key} must be true", detail=key,
            ))

    plan = _mapping(run.get("plan"), "plan", findings)
    nodes = plan.get("nodes") or []
    if not plan.get("path"):
        findings.append(Finding(
            "plan.path.required", "plan_present", "plan.path is required",
        ))
    if not isinstance(nodes, list) or not nodes:
        findings.append(Finding(
            "plan.nodes.required", "plan_present",
            "plan.nodes must contain at least one node",
        ))

    deliverable = _mapping(run.get("deliverable"), "deliverable", findings)
    if not deliverable.get("requested"):
        findings.append(Finding(
            "deliverable.requested.required", "requested_deliverable_produced",
            "deliverable.requested is required",
        ))
    if deliverable.get("provided") is not True:
        findings.append(Finding(
            "deliverable.provided.required", "requested_deliverable_produced",
            "deliverable.provided must be true",
        ))
    traversal_report = deliverable.get("traversal_report")
    if not isinstance(traversal_report, str) or not traversal_report.strip():
        findings.append(Finding(
            "deliverable.traversal_report.required",
            "requested_deliverable_produced",
            "deliverable.traversal_report is required for user-visible traversal proof",
        ))

    ledger_path = Path(str(run.get("_ledger_path", "run.json")))
    base_dir = ledger_path.parent if str(ledger_path.parent) not in {"", "."} else Path.cwd()
    _validate_run_root_paths(run, base_dir, findings)

    if plan.get("path"):
        plan_path = Path(str(plan["path"]))
        if not plan_path.is_absolute():
            plan_path = base_dir / plan_path
        if not plan_path.is_file():
            findings.append(Finding(
                "plan.path.missing", "plan_resolved",
                f"plan.path does not exist: {plan_path}", detail=str(plan_path),
            ))

    if "chunking" not in run:
        findings.append(Finding(
            "chunking.required", "source_coverage_complete",
            "chunking contract is required",
        ))
        manifest_chunk_ids, evidenced_chunk_ids = [], []
    elif not isinstance(run.get("chunking"), dict):
        findings.append(Finding(
            "chunking.type", "source_coverage_complete",
            "chunking must be an object",
        ))
        manifest_chunk_ids, evidenced_chunk_ids = [], []
    else:
        manifest_chunk_ids, evidenced_chunk_ids = _validate_chunk_evidence(run, base_dir, findings)

    if "qa" not in run:
        findings.append(Finding(
            "qa.required", "format_qa_complete", "qa contract is required",
        ))
        qa = {}
    else:
        qa = _mapping(run.get("qa"), "qa", findings)
    required_qa = qa.get("required", [])
    passed_qa = qa.get("passed", [])
    if not isinstance(required_qa, list) or not isinstance(passed_qa, list):
        findings.append(Finding(
            "qa.type", "format_qa_complete",
            "qa.required and qa.passed must be lists",
        ))
    else:
        missing_qa = [q for q in required_qa if q not in passed_qa]
        for check in missing_qa:
            findings.append(Finding(
                "qa.missing", "format_qa_complete",
                f"qa missing required check: {check}", detail=check,
            ))

    evidence = _mapping(run.get("evidence"), "evidence", findings)
    for key in REQUIRED_EVIDENCE:
        value = evidence.get(key)
        if not isinstance(value, str) or not value.strip():
            findings.append(Finding(
                f"evidence.{key}.invalid", "evidence_complete",
                f"evidence.{key} must be a file path", detail=key,
            ))
            continue
        evidence_path = Path(value)
        if not evidence_path.is_absolute():
            evidence_path = base_dir / evidence_path
        if not evidence_path.is_file():
            findings.append(Finding(
                f"evidence.{key}.missing", "evidence_complete",
                f"evidence.{key} does not exist: {evidence_path}", detail=key,
            ))

    chunking_report = run.get("chunking", {}).get("traversal_report") if isinstance(run.get("chunking"), dict) else None
    evidence_report = evidence.get("traversal_report")
    deliverable_report = deliverable.get("traversal_report")
    if any(isinstance(x, str) and x.strip() for x in (chunking_report, evidence_report, deliverable_report)):
        if not (chunking_report == evidence_report == deliverable_report):
            findings.append(Finding(
                "traversal.report.mismatch", "output_containment_valid",
                "traversal report path must match across chunking, evidence, and deliverable contracts",
            ))

    for raw_path in deliverable.get("paths", []) or []:
        deliverable_path = Path(str(raw_path))
        if not deliverable_path.is_absolute():
            deliverable_path = base_dir / deliverable_path
        if not deliverable_path.is_file():
            findings.append(Finding(
                "deliverable.path.missing", "requested_deliverable_produced",
                f"deliverable path does not exist: {deliverable_path}",
                detail=str(deliverable_path),
            ))

    raw_events = run.get("events", [])
    if not isinstance(raw_events, list):
        findings.append(Finding(
            "events.type", "machine_checks_passed", "events must be a list",
        ))
        events: list[dict[str, Any]] = []
    else:
        events = []
        for index, event in enumerate(raw_events, start=1):
            if not isinstance(event, dict):
                findings.append(Finding(
                    "events.entry.type", "machine_checks_passed",
                    f"events[{index}] must be an object", detail=str(index),
                ))
                continue
            events.append(event)
    types = [str(event.get("type", "")) for event in events]

    verified_events = [event for event in events if event.get("type") == "chunk_verified"]
    verified_event_ids = [str(event.get("chunk_id", "")) for event in verified_events]
    if manifest_chunk_ids:
        for chunk_id in manifest_chunk_ids:
            if chunk_id not in verified_event_ids:
                findings.append(Finding(
                    "events.chunk_verified.missing", "source_coverage_complete",
                    f"missing chunk_verified event for emitted chunk: {chunk_id}",
                    detail=chunk_id,
                ))
        for chunk_id in verified_event_ids:
            if chunk_id not in manifest_chunk_ids:
                findings.append(Finding(
                    "events.chunk_verified.unknown", "source_coverage_complete",
                    f"chunk_verified references unknown chunk: {chunk_id}",
                    detail=chunk_id,
                ))
        if len(verified_event_ids) != len(set(verified_event_ids)):
            findings.append(Finding(
                "events.chunk_verified.duplicate", "source_coverage_complete",
                "duplicate chunk_verified event",
            ))
        if verified_event_ids and verified_event_ids != manifest_chunk_ids:
            findings.append(Finding(
                "events.chunk_verified.order", "source_coverage_complete",
                "chunk_verified events must follow manifest order",
            ))
        if evidenced_chunk_ids == manifest_chunk_ids and verified_event_ids != evidenced_chunk_ids:
            findings.append(Finding(
                "events.chunk_verified.mirror", "source_coverage_complete",
                "chunk_verified events must exactly mirror evidenced manifest chunks",
            ))

    if "plan_written" not in types:
        findings.append(Finding(
            "events.plan_written.missing", "plan_resolved",
            "events must include plan_written",
        ))
    if "execution_started" not in types:
        findings.append(Finding(
            "events.execution_started.missing", "plan_resolved",
            "events must include execution_started",
        ))

    if "execution_started" in types and "plan_written" in types:
        if types.index("execution_started") < types.index("plan_written"):
            findings.append(Finding(
                "events.execution.order", "plan_resolved",
                "execution_started cannot precede plan_written",
            ))

    for key in LEGACY_PREFLIGHT:
        if key in preflight:
            findings.append(Finding(
                "preflight.legacy", "skill_preflight_complete",
                f"legacy preflight key is not allowed: {key}", detail=key,
            ))

    for event in events:
        event_type = event.get("type")
        if event_type in LEGACY_PROCESS_EVENTS:
            findings.append(Finding(
                "events.legacy", "machine_checks_passed",
                f"legacy process event is not allowed: {event_type}", detail=event_type,
            ))

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
            findings.append(Finding(
                "failure.protocol.diagnosis", "failure_protocol_respected",
                f"node_failed({failed_node}) requires failure_diagnosed before traversal or repair",
                detail=str(failed_node),
            ))

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
                findings.append(Finding(
                    "failure.protocol.architecture_stop.repair",
                    "failure_protocol_respected",
                    "architecture_stop blocks further repair/traversal until exhausted-path redesign and plan_revised",
                ))
                break
        if not replanned and any(e.get("type") in repair_types for e in events[i + 1 :]):
            pass

    for i, event in enumerate(events):
        if event.get("type") != "alternative_designed":
            continue
        prior_types = [e.get("type") for e in events[:i]]
        required = ("architecture_stop", "paths_exhausted", "disclosure")
        if not all(name in prior_types for name in required):
            findings.append(Finding(
                "failure.protocol.alternative.prerequisites",
                "failure_protocol_respected",
                "alternative_designed requires prior architecture_stop, paths_exhausted, and disclosure",
            ))
        else:
            positions = [prior_types.index(name) for name in required]
            if positions != sorted(positions):
                findings.append(Finding(
                    "failure.protocol.alternative.order", "failure_protocol_respected",
                    "alternative_designed requires architecture_stop -> paths_exhausted -> disclosure ordering",
                ))

    for i, event in enumerate(events):
        if event.get("type") != "plan_revised":
            continue
        if not any(e.get("type") == "alternative_designed" for e in events[:i]):
            findings.append(Finding(
                "failure.protocol.plan_revised", "failure_protocol_respected",
                "plan_revised requires prior alternative_designed",
            ))

    done_positions = [i for i, e in enumerate(events) if e.get("type") == "done"]
    if done_positions:
        done_i = done_positions[-1]
        prior_types = [e.get("type") for e in events[:done_i]]
        if "verification_started" not in prior_types:
            findings.append(Finding(
                "done.verification_started.missing", "fresh_final_verification",
                "done requires prior verification_started",
            ))
        if "verification_passed" not in prior_types:
            findings.append(Finding(
                "done.verification_passed.missing", "fresh_final_verification",
                "done requires prior verification_passed",
            ))
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
                findings.append(Finding(
                    "done.verification.stale", "fresh_final_verification",
                    "verification_passed must follow the last material event",
                ))
        for node in nodes:
            if not _node_is_resolved(events[:done_i], str(node)):
                findings.append(Finding(
                    "done.node.unresolved", "plan_resolved",
                    f"done requires resolved plan node: {node}", detail=str(node),
                ))

        unresolved_failures: set[str] = set()
        for e in events[:done_i]:
            if e.get("type") == "node_failed" and e.get("node"):
                unresolved_failures.add(str(e["node"]))
            if e.get("type") in {"node_recovered", "node_passed", "node_superseded"} and e.get("node"):
                unresolved_failures.discard(str(e["node"]))
        for node in sorted(unresolved_failures):
            findings.append(Finding(
                "done.failure.unresolved", "no_unresolved_required_failures",
                f"done with unresolved failed node: {node}", detail=node,
            ))

    return findings


def validate_run(run: dict[str, Any]) -> list[str]:
    """Public compatibility wrapper: display messages only."""
    return [f.message for f in validate_findings(run)]


def _as_findings(run: dict[str, Any], items: list[Any]) -> list[Finding]:
    """Normalize a findings list or a legacy display-message list.

    The findings path is authoritative. The legacy str path re-derives the
    findings deterministically and asserts the messages match, so callers
    holding display text still get full predicate truth without any
    message-to-code guessing.
    """
    if items and isinstance(items[0], Finding):
        return list(items)
    findings = validate_findings(run)
    assert [f.message for f in findings] == list(items), (
        "legacy messages no longer match validate_findings output")
    return findings


def build_dod(run: dict[str, Any], errors: list[Any]) -> dict[str, Any]:
    from verification_findings import codes_of, group_by_predicate

    findings = _as_findings(run, errors)
    by_predicate = group_by_predicate(findings)
    codes = codes_of(findings)

    raw_events = run.get("events", [])
    events = [event for event in raw_events if isinstance(event, dict)] if isinstance(raw_events, list) else []
    source = run.get("source") if isinstance(run.get("source"), dict) else {}
    preflight = run.get("preflight") if isinstance(run.get("preflight"), dict) else {}
    plan = run.get("plan") if isinstance(run.get("plan"), dict) else {}
    fidelity = run.get("fidelity") if isinstance(run.get("fidelity"), dict) else {}
    deliverable = run.get("deliverable") if isinstance(run.get("deliverable"), dict) else {}

    def failed(predicate: str) -> bool:
        return bool(by_predicate.get(predicate))

    predicates = {
        "source_identity_verified": source.get("identity_verified") is True and not failed("source_identity_verified"),
        "skill_preflight_complete": all(
            preflight.get(k) is True for k in REQUIRED_PREFLIGHT
        ) and not failed("skill_preflight_complete"),
        "plan_present": bool(plan.get("path")) and bool(plan.get("nodes")) and not failed("plan_present"),
        "plan_resolved": not failed("plan_resolved"),
        "output_containment_valid": not failed("output_containment_valid"),
        "source_coverage_complete": not failed("source_coverage_complete"),
        "failure_protocol_respected": not failed("failure_protocol_respected"),
        "source_fidelity_preserved": fidelity.get("preserved") is True and not failed("source_fidelity_preserved"),
        "format_qa_complete": not failed("format_qa_complete"),
        "requested_deliverable_produced": deliverable.get("provided") is True and not failed("requested_deliverable_produced"),
        "deliverable_provided": deliverable.get("provided") is True and not failed("requested_deliverable_produced"),
        "evidence_complete": not failed("evidence_complete"),
        "no_unresolved_required_failures": not failed("no_unresolved_required_failures"),
        "fresh_final_verification": any(
            e.get("type") == "verification_passed" for e in events
        ) and not failed("fresh_final_verification"),
        "machine_checks_passed": not findings,
    }
    return {
        "passed": not findings,
        "violations": [f.message for f in findings],
        "codes": codes,
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

    try:
        loaded = json.loads(ledger.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        loaded = None
        errors = [f"run ledger is not valid JSON: {exc}"]
    else:
        errors = []

    if not isinstance(loaded, dict):
        run: dict[str, Any] = {"_ledger_path": str(ledger)}
        if loaded is not None:
            findings = [Finding(
                "json.ledger.type", "machine_checks_passed",
                "run ledger must contain a JSON object",
            )]
        else:
            findings = [Finding(
                "json.ledger.unreadable", "machine_checks_passed",
                errors[0],
            )]
    else:
        run = loaded
        run["_ledger_path"] = str(ledger)
        findings = validate_findings(run)
    dod = build_dod(run, findings)

    canonical_dod.parent.mkdir(parents=True, exist_ok=True)
    canonical_dod.write_text(json.dumps(dod, indent=2) + "\n", encoding="utf-8")

    if findings:
        for f in findings:
            print(f"FAIL: {f.message}")
        return 1

    print("PASS: Definition of Done predicates satisfied")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
