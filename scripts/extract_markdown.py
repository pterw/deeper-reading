#!/usr/bin/env python3
"""Portable exhaustive Markdown extractor with structural chunking."""

from __future__ import annotations

import argparse
from pathlib import Path
from script_io import run_cli
import re

from chunk_common import Block, build_manifest, manifest_output_path, pack_blocks, write_manifest

HEADING_RE = re.compile(r'^(#{1,6})\s+(.+?)\s*$')
TABLE_SEP_RE = re.compile(r'^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$')
FENCE_RE = re.compile(r'^\s*(```+|~~~+)')


def _heading_path(stack: list[str | None]) -> list[str]:
    return [value for value in stack if value is not None]


def parse_markdown_blocks(text: str) -> list[Block]:
    lines = text.splitlines(keepends=True)
    blocks: list[Block] = []
    headings: list[str | None] = [None] * 6
    i = 0

    while i < len(lines):
        line = lines[i]
        stripped = line.rstrip('\r\n')
        fence = FENCE_RE.match(stripped)
        if fence:
            marker = fence.group(1)
            fence_lines = [line]
            i += 1
            while i < len(lines):
                fence_lines.append(lines[i])
                candidate = lines[i].lstrip()
                i += 1
                if candidate.startswith(marker[0] * len(marker)):
                    break
            blocks.append(Block(
                ''.join(fence_lines).rstrip('\r\n'),
                {'kind': 'fenced_code', 'heading_path': _heading_path(headings)},
                atomic_kind='fenced_code',
            ))
            continue

        heading = HEADING_RE.match(stripped)
        if heading:
            level = len(heading.group(1))
            title = heading.group(2).strip().strip('#').strip()
            headings[level - 1] = title
            for idx in range(level, len(headings)):
                headings[idx] = None
            blocks.append(Block(
                stripped + '\n',
                {'kind': 'heading', 'level': level, 'heading_path': _heading_path(headings)},
            ))
            i += 1
            continue

        if (
            '|' in stripped
            and i + 1 < len(lines)
            and TABLE_SEP_RE.match(lines[i + 1].rstrip('\r\n'))
        ):
            table_lines = [line, lines[i + 1]]
            i += 2
            while i < len(lines):
                candidate = lines[i].rstrip('\r\n')
                if not candidate.strip() or '|' not in candidate:
                    break
                table_lines.append(lines[i])
                i += 1
            blocks.append(Block(
                ''.join(table_lines).rstrip('\r\n'),
                {'kind': 'table', 'heading_path': _heading_path(headings)},
                atomic_kind='table',
            ))
            continue

        if not stripped.strip():
            i += 1
            continue

        para_lines = [line]
        i += 1
        while i < len(lines):
            candidate = lines[i]
            candidate_stripped = candidate.rstrip('\r\n')
            if not candidate_stripped.strip():
                i += 1
                break
            if FENCE_RE.match(candidate_stripped) or HEADING_RE.match(candidate_stripped):
                break
            if (
                '|' in candidate_stripped
                and i + 1 < len(lines)
                and TABLE_SEP_RE.match(lines[i + 1].rstrip('\r\n'))
            ):
                break
            para_lines.append(candidate)
            i += 1
        blocks.append(Block(
            ''.join(para_lines),
            {'kind': 'text', 'heading_path': _heading_path(headings)},
        ))

    return blocks


def extract(source: Path, *, max_bytes: int, source_uri: str | None = None) -> dict:
    text = source.read_text(encoding='utf-8-sig')
    blocks = parse_markdown_blocks(text)
    packed = pack_blocks(blocks, max_bytes)
    return build_manifest(
        source,
        'markdown',
        packed,
        strategy='markdown-heading-ast-blocks',
        max_bytes=max_bytes,
        source_uri=source_uri,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description='Extract Markdown into exhaustive structural chunks')
    parser.add_argument('source', type=Path)
    output = parser.add_mutually_exclusive_group(required=True)
    output.add_argument('--out', type=Path)
    output.add_argument('--run-root', type=Path)
    parser.add_argument('--max-bytes', type=int, default=12000)
    parser.add_argument('--source-uri')
    args = parser.parse_args()
    out = manifest_output_path(out=args.out, run_root=args.run_root)
    manifest = extract(args.source, max_bytes=args.max_bytes, source_uri=args.source_uri)
    write_manifest(manifest, out)
    print(f'Wrote {len(manifest["chunks"])} chunks to {out}')
    return 0


if __name__ == '__main__':
    raise SystemExit(run_cli(main))
