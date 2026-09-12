#!/usr/bin/env python3
"""Dump canonical chunks from a deeper-reading chunk manifest.

Read-only helper for this run. It lives inside the run root's tools/
directory because it is a workflow artifact, not run evidence.

Usage:
    python dump_chunks.py MANIFEST --summary
    python dump_chunks.py MANIFEST --from 1 --to 12
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def _heading_path(chunk: dict) -> str:
    """Return the chunk's heading path, or '(none)' when it has none."""
    locator = chunk.get("locator") or {}
    path = locator.get("heading_path") or []
    return " > ".join(path) if path else "(none)"


def _kinds(chunk: dict) -> str:
    """Return the distinct block kinds in the chunk, in first-seen order."""
    locator = chunk.get("locator") or {}
    kinds: list[str] = []
    for block in locator.get("blocks") or []:
        kind = block.get("kind")
        if kind and kind not in kinds:
            kinds.append(kind)
    return "+".join(kinds) if kinds else "?"


def main() -> int:
    """Print either a one-line summary per chunk or full chunk contents."""
    parser = argparse.ArgumentParser(description="Dump deeper-reading manifest chunks")
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--from", dest="first", type=int, default=1)
    parser.add_argument("--to", dest="last", type=int, default=0)
    parser.add_argument("--summary", action="store_true")
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    chunks = manifest["chunks"]
    last = args.last or len(chunks)

    for chunk in chunks:
        ordinal = chunk["ordinal"]
        if ordinal < args.first or ordinal > last:
            continue
        if args.summary:
            print(
                f'{ordinal:02d} {chunk["id"]} [{_kinds(chunk)}] '
                f'{len(chunk["content"])}ch {_heading_path(chunk)}'
            )
            continue
        print("=" * 78)
        print(f'CHUNK {ordinal:02d}  id={chunk["id"]}')
        print(f'span={chunk["text_byte_start"]}..{chunk["text_byte_end"]} kinds={_kinds(chunk)}')
        print(f'heading_path={_heading_path(chunk)}')
        print("~" * 78)
        print(chunk["content"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
