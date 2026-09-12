#!/usr/bin/env python3
"""Build canonical schema-v2 chunk evidence from draft extractive verdicts."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from evidence_atoms import EvidenceBindingError, bind_atom


def _load_object(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise EvidenceBindingError(f"{label} is not valid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise EvidenceBindingError(f"{label} must contain a JSON object")
    return value


def _draft_by_ordinal(draft: dict[str, Any], manifest_ordinals: set[int]) -> dict[int, dict[str, Any]]:
    raw_entries = draft.get("entries")
    if not isinstance(raw_entries, list):
        raise EvidenceBindingError("draft entries must be a list")
    indexed: dict[int, dict[str, Any]] = {}
    for index, entry in enumerate(raw_entries, start=1):
        if not isinstance(entry, dict):
            raise EvidenceBindingError(f"draft entry {index} must be an object")
        ordinal = entry.get("ordinal")
        if type(ordinal) is not int:
            raise EvidenceBindingError(f"draft entry {index} ordinal must be an integer")
        if ordinal not in manifest_ordinals:
            raise EvidenceBindingError(f"unknown verdict ordinal: {ordinal}")
        if ordinal in indexed:
            raise EvidenceBindingError(f"duplicate verdict ordinal: {ordinal}")
        indexed[ordinal] = entry
    missing = sorted(manifest_ordinals - set(indexed))
    if missing:
        raise EvidenceBindingError(f"missing verdict for manifest ordinal(s): {missing}")
    return indexed


def build(manifest_path: Path, draft_path: Path, out_path: Path) -> dict[str, Any]:
    manifest_bytes = manifest_path.read_bytes()
    try:
        manifest = json.loads(manifest_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise EvidenceBindingError(f"manifest is not valid JSON: {exc}") from exc
    if not isinstance(manifest, dict):
        raise EvidenceBindingError("manifest must contain a JSON object")
    draft = _load_object(draft_path, "draft evidence")

    chunks = manifest.get("chunks")
    if not isinstance(chunks, list):
        raise EvidenceBindingError("manifest chunks must be a list")
    by_ordinal: dict[int, dict[str, Any]] = {}
    for index, chunk in enumerate(chunks, start=1):
        if not isinstance(chunk, dict):
            raise EvidenceBindingError(f"manifest chunk {index} must be an object")
        ordinal = chunk.get("ordinal")
        if type(ordinal) is not int:
            raise EvidenceBindingError(f"manifest chunk {index} ordinal must be an integer")
        if ordinal in by_ordinal:
            raise EvidenceBindingError(f"duplicate manifest ordinal: {ordinal}")
        by_ordinal[ordinal] = chunk

    drafts = _draft_by_ordinal(draft, set(by_ordinal))
    entries: list[dict[str, Any]] = []
    for ordinal in sorted(by_ordinal):
        chunk = by_ordinal[ordinal]
        chunk_id = chunk.get("id")
        content = chunk.get("content")
        chunk_sha = chunk.get("content_sha256")
        if not isinstance(chunk_id, str) or not chunk_id:
            raise EvidenceBindingError(f"manifest ordinal {ordinal} missing chunk id")
        if not isinstance(content, str):
            raise EvidenceBindingError(f"manifest ordinal {ordinal} content must be text")
        if not isinstance(chunk_sha, str) or not chunk_sha:
            raise EvidenceBindingError(f"manifest ordinal {ordinal} missing content_sha256")

        authored = drafts[ordinal]
        outcome = authored.get("outcome")
        entry: dict[str, Any] = {
            "chunk_id": chunk_id,
            "ordinal": ordinal,
            "chunk_sha256": chunk_sha,
            "outcome": outcome,
        }
        if outcome == "evidence":
            total_atoms = 0
            for plural, singular in (("assertions", "assertion"), ("constraints", "constraint")):
                raw_atoms = authored.get(plural, [])
                if not isinstance(raw_atoms, list):
                    raise EvidenceBindingError(f"chunk {ordinal} {plural} must be a list")
                bound = [bind_atom(chunk_id, singular, content, atom) for atom in raw_atoms]
                entry[plural] = bound
                total_atoms += len(bound)
            if total_atoms == 0:
                raise EvidenceBindingError(
                    f"chunk {ordinal} evidence verdict requires at least one assertion or constraint"
                )
        elif outcome == "non_match":
            reason = authored.get("reason")
            if not isinstance(reason, str) or not reason.strip():
                raise EvidenceBindingError(f"chunk {ordinal} non_match reason is required")
            entry["reason"] = reason
        else:
            raise EvidenceBindingError(
                f"chunk {ordinal} outcome must be evidence or non_match"
            )
        entries.append(entry)

    source = manifest.get("source")
    if not isinstance(source, dict) or not isinstance(source.get("sha256"), str):
        raise EvidenceBindingError("manifest source.sha256 is required")
    return {
        "schema_version": 2,
        "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
        "source_sha256": source["sha256"],
        "entries": entries,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build byte-verified chunk evidence")
    parser.add_argument("manifest", type=Path)
    parser.add_argument("draft", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        ledger = build(args.manifest, args.draft, args.out)
    except (EvidenceBindingError, OSError) as exc:
        print(f"FAIL: {exc}")
        return 1
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(ledger, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    assertions = sum(len(entry.get("assertions", [])) for entry in ledger["entries"])
    constraints = sum(len(entry.get("constraints", [])) for entry in ledger["entries"])
    print(
        f"Wrote {len(ledger['entries'])} verdicts / {assertions} assertions / "
        f"{constraints} constraints to {args.out}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
