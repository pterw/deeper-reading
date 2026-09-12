#!/usr/bin/env python3
"""Build the canonical chunk-evidence ledger for this run.

Reads the extractor manifest, locates every authored assertion inside its own
chunk bytes, and writes evidence/chunk-evidence.json. It refuses to write when
any assertion does not reproduce its chunk bytes, printing the nearest matching
line so the mismatch can be corrected from the source rather than guessed.

Usage:
    python build_evidence.py MANIFEST OUT
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

from assertions_a import ASSERTIONS_A
from assertions_b import ASSERTIONS_B
from assertions_c import ASSERTIONS_C

ASSERTIONS: dict[int, list[str]] = {**ASSERTIONS_A, **ASSERTIONS_B, **ASSERTIONS_C}


def _sha256(data: bytes) -> str:
    """Return the lowercase hex SHA-256 of a byte string."""
    return hashlib.sha256(data).hexdigest()


def _candidate_lines(content: str, assertion: str, limit: int = 3) -> list[str]:
    """Return chunk lines that share a distinctive token with the assertion.

    This is the repair aid: when an assertion does not reproduce its chunk
    bytes, these lines show the exact characters the source actually uses.
    """
    tokens = [t for t in re.split(r"[^A-Za-z0-9_]+", assertion) if len(t) > 3]
    candidates = sorted(tokens, key=len, reverse=True)[:3]
    hits: list[str] = []
    for line in content.split("\n"):
        if any(token in line for token in candidates):
            hits.append(line)
        if len(hits) >= limit:
            break
    return hits


def build(manifest_path: Path, out_path: Path) -> int:
    """Locate all assertions and write the ledger. Returns a process code."""
    manifest_bytes = manifest_path.read_bytes()
    manifest = json.loads(manifest_bytes.decode("utf-8"))
    chunks = manifest["chunks"]

    if sorted(ASSERTIONS) != [c["ordinal"] for c in chunks]:
        missing = sorted(set(range(1, len(chunks) + 1)) - set(ASSERTIONS))
        print(f"FAIL: assertion coverage does not match the manifest. missing={missing}")
        return 1

    entries = []
    problems = 0
    for chunk in chunks:
        content_bytes = chunk["content"].encode("utf-8")
        assertions = []
        for text in ASSERTIONS[chunk["ordinal"]]:
            needle = text.encode("utf-8")
            offset = content_bytes.find(needle)
            if offset < 0:
                problems += 1
                print(f"MISS chunk {chunk['ordinal']:02d}: {text[:70]!r}")
                for line in _candidate_lines(chunk["content"], text):
                    print(f"     source has: {line[:170]!r}")
                continue
            assertions.append(
                {
                    "text": text,
                    "chunk_byte_start": offset,
                    "chunk_byte_end": offset + len(needle),
                }
            )
        entries.append(
            {
                "chunk_id": chunk["id"],
                "ordinal": chunk["ordinal"],
                "chunk_sha256": chunk["content_sha256"],
                "outcome": "evidence",
                "assertions": assertions,
                "constraints": [],
            }
        )

    if problems:
        print(f"FAIL: {problems} assertion(s) do not reproduce their chunk bytes.")
        return 1

    ledger = {
        "schema_version": 1,
        "manifest_sha256": _sha256(manifest_bytes),
        "source_sha256": manifest["source"]["sha256"],
        "entries": entries,
    }
    out_path.write_text(json.dumps(ledger, indent=2) + "\n", encoding="utf-8")
    total = sum(len(e["assertions"]) for e in entries)
    print(f"Wrote {len(entries)} verdicts / {total} assertions to {out_path}")
    return 0


def main() -> int:
    """Parse arguments and build the ledger."""
    parser = argparse.ArgumentParser(description="Build the chunk-evidence ledger")
    parser.add_argument("manifest", type=Path)
    parser.add_argument("out", type=Path)
    args = parser.parse_args()
    return build(args.manifest, args.out)


if __name__ == "__main__":
    raise SystemExit(main())
