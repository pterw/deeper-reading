#!/usr/bin/env python3
"""Read-only bounded inspection of canonical deeper-reading chunk manifests."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from script_io import run_cli

from chunk_view import detail_block, summary_line


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Inspect canonical deeper-reading chunks")
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--from", dest="first", type=int, default=1)
    parser.add_argument("--to", dest="last", type=int, default=0)
    parser.add_argument("--summary", action="store_true")
    args = parser.parse_args(argv)

    try:
        value = json.loads(args.manifest.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        print(f"FAIL: manifest is not valid JSON: {exc}")
        return 1
    chunks = value.get("chunks") if isinstance(value, dict) else None
    if not isinstance(chunks, list):
        print("FAIL: manifest must contain a chunks list")
        return 1
    if args.first < 1 or args.last < 0 or (args.last and args.last < args.first):
        print("FAIL: chunk range must satisfy 1 <= --from <= --to")
        return 1
    last = args.last or len(chunks)
    for chunk in chunks:
        if not isinstance(chunk, dict) or type(chunk.get("ordinal")) is not int:
            print("FAIL: every manifest chunk must be an object with integer ordinal")
            return 1
        ordinal = chunk["ordinal"]
        if ordinal < args.first or ordinal > last:
            continue
        print(summary_line(chunk) if args.summary else detail_block(chunk))
    return 0


if __name__ == "__main__":
    raise SystemExit(run_cli(main))
