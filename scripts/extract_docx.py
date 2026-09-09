#!/usr/bin/env python3
"""Portable exhaustive DOCX text extractor using ZIP + OOXML stdlib parsing."""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import zipfile
import xml.etree.ElementTree as ET

from chunk_common import Block, build_manifest, manifest_output_path, pack_blocks, write_manifest

W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
NS = {'w': W}
TEXT_TAGS = {f'{{{W}}}t', f'{{{W}}}delText', f'{{{W}}}instrText'}
TAB_TAG = f'{{{W}}}tab'
BREAK_TAGS = {f'{{{W}}}br', f'{{{W}}}cr'}
P_TAG = f'{{{W}}}p'
TBL_TAG = f'{{{W}}}tbl'
TR_TAG = f'{{{W}}}tr'
TC_TAG = f'{{{W}}}tc'


def _story_part(name: str) -> bool:
    return bool(
        name == 'word/document.xml'
        or re.fullmatch(r'word/header\d+\.xml', name)
        or re.fullmatch(r'word/footer\d+\.xml', name)
        or name in {
            'word/footnotes.xml',
            'word/endnotes.xml',
            'word/comments.xml',
        }
    )


def _part_sort_key(name: str) -> tuple[int, str]:
    if name == 'word/document.xml':
        return (0, name)
    if name.startswith('word/header'):
        return (1, name)
    if name.startswith('word/footer'):
        return (2, name)
    if name == 'word/footnotes.xml':
        return (3, name)
    if name == 'word/endnotes.xml':
        return (4, name)
    if name == 'word/comments.xml':
        return (5, name)
    return (9, name)


def _text_from_element(element: ET.Element) -> str:
    pieces: list[str] = []
    for node in element.iter():
        if node.tag in TEXT_TAGS and node.text:
            pieces.append(node.text)
        elif node.tag == TAB_TAG:
            pieces.append('\t')
        elif node.tag in BREAK_TAGS:
            pieces.append('\n')
    return ''.join(pieces)


def _heading_level(paragraph: ET.Element) -> int | None:
    style = paragraph.find('./w:pPr/w:pStyle', NS)
    if style is None:
        return None
    value = style.get(f'{{{W}}}val') or ''
    match = re.search(r'Heading\s*([123])$', value, re.IGNORECASE)
    if not match:
        return None
    return int(match.group(1))


def _table_text(table: ET.Element) -> str:
    rows: list[str] = []
    for row in table.findall('./w:tr', NS):
        cells: list[str] = []
        for cell in row.findall('./w:tc', NS):
            paragraphs = [
                _text_from_element(p).strip()
                for p in cell.iter(P_TAG)
            ]
            cells.append(' '.join(x for x in paragraphs if x))
        rows.append('\t'.join(cells))
    return '\n'.join(row for row in rows if row.strip())


def _walk_blocks(root: ET.Element, part: str) -> list[Block]:
    blocks: list[Block] = []
    headings: list[str | None] = [None, None, None]
    block_index = 0

    def path() -> list[str]:
        return [value for value in headings if value is not None]

    def walk(parent: ET.Element) -> None:
        nonlocal block_index
        for child in list(parent):
            if child.tag == TBL_TAG:
                text = _table_text(child).strip()
                if text:
                    block_index += 1
                    blocks.append(Block(
                        text,
                        {
                            'part': part,
                            'block_index': block_index,
                            'kind': 'table',
                            'heading_path': path(),
                        },
                        atomic_kind='table',
                    ))
                continue
            if child.tag == P_TAG:
                text = _text_from_element(child).strip()
                if text:
                    level = _heading_level(child)
                    if level is not None:
                        headings[level - 1] = text
                        for idx in range(level, 3):
                            headings[idx] = None
                    block_index += 1
                    locator = {
                        'part': part,
                        'block_index': block_index,
                        'kind': 'heading' if level else 'paragraph',
                        'heading_path': path(),
                    }
                    if level:
                        locator['level'] = level
                    blocks.append(Block(text + '\n', locator))
                continue
            walk(child)

    walk(root)
    return blocks


def extract(source: Path, *, max_bytes: int, source_uri: str | None = None) -> dict:
    blocks: list[Block] = []
    with zipfile.ZipFile(source) as zf:
        parts = sorted((name for name in zf.namelist() if _story_part(name)), key=_part_sort_key)
        if 'word/document.xml' not in parts:
            raise ValueError('DOCX is missing word/document.xml')
        for part in parts:
            root = ET.fromstring(zf.read(part))
            blocks.extend(_walk_blocks(root, part))
    packed = pack_blocks(blocks, max_bytes)
    return build_manifest(
        source,
        'docx',
        packed,
        strategy='docx-ooxml-story-blocks',
        max_bytes=max_bytes,
        source_uri=source_uri,
        backend='stdlib-zip-xml',
    )


def main() -> int:
    parser = argparse.ArgumentParser(description='Extract DOCX text into exhaustive structural chunks')
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
    raise SystemExit(main())
