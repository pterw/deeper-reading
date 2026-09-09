#!/usr/bin/env python3
"""Render a deterministic human-readable traversal ledger."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from chunk_common import canonical_run_paths, render_traversal_report


def main() -> int:
    parser = argparse.ArgumentParser(description="Render TRAVERSAL_REPORT.md from canonical chunk evidence")
    parser.add_argument("manifest", type=Path, nargs="?")
    parser.add_argument("evidence", type=Path, nargs="?")
    parser.add_argument("--out", type=Path)
    parser.add_argument("--run-root", type=Path)
    args = parser.parse_args()

    if args.run_root is not None:
        if any(value is not None for value in (args.manifest, args.evidence, args.out)):
            parser.error("--run-root cannot be combined with manifest/evidence/--out")
        paths = canonical_run_paths(args.run_root)
        manifest_path = paths["manifest"]
        evidence_path = paths["chunk_evidence"]
        out = paths["traversal_report"]
    else:
        if args.manifest is None or args.evidence is None or args.out is None:
            parser.error("manifest, evidence, and --out are required without --run-root")
        manifest_path = args.manifest
        evidence_path = args.evidence
        out = args.out

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_traversal_report(manifest, evidence), encoding="utf-8")
    print(f"Wrote traversal report to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
