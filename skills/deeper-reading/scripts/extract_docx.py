#!/usr/bin/env python3
"""Portable exhaustive DOCX text extractor using ZIP + OOXML stdlib parsing."""

from __future__ import annotations

import argparse
from pathlib import Path
from script_io import run_cli
import re
import zipfile
import xml.etree.ElementTree as ET

from chunk_common import Block, MediaCollector, build_manifest, manifest_output_path, pack_blocks, write_manifest

W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
NS = {'w': W}
TEXT_TAGS = {f'{{{W}}}t', f'{{{W}}}delText'}
MARKERS = {
    f'{{{W}}}del': 'deleted',
    f'{{{W}}}moveFrom': 'deleted',
    f'{{{W}}}ins': 'inserted',
    f'{{{W}}}moveTo': 'inserted',
}
FALLBACK_TAG = '{http://schemas.openxmlformats.org/markup-compatibility/2006}Fallback'
TAB_TAG = f'{{{W}}}tab'
BREAK_TAGS = {f'{{{W}}}br', f'{{{W}}}cr'}
P_TAG = f'{{{W}}}p'
TBL_TAG = f'{{{W}}}tbl'
TR_TAG = f'{{{W}}}tr'
TC_TAG = f'{{{W}}}tc'
R = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
A = 'http://schemas.openxmlformats.org/drawingml/2006/main'
C = 'http://schemas.openxmlformats.org/drawingml/2006/chart'
DGM = 'http://schemas.openxmlformats.org/drawingml/2006/diagram'
WP = 'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing'
V = 'urn:schemas-microsoft-com:vml'
O = 'urn:schemas-microsoft-com:office:office'
PKG_REL = '{http://schemas.openxmlformats.org/package/2006/relationships}Relationship'
DRAWING_TAG = f'{{{W}}}drawing'
CX = 'http://schemas.microsoft.com/office/drawing/2014/chartex'
IMAGEDATA_TAG = f'{{{V}}}imagedata'
OBJECT_TAG = f'{{{W}}}object'


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


def _collect_text(element: ET.Element, pieces: list[str]) -> None:
    for node in element:
        if node.tag == FALLBACK_TAG:
            continue
        if node.tag in TEXT_TAGS:
            pieces.append(node.text or '')
        elif node.tag == TAB_TAG:
            pieces.append('\t')
        elif node.tag in BREAK_TAGS:
            pieces.append('\n')
        elif node.tag in MARKERS:
            raw = _text_from_element(node)
            inner = raw.strip()
            if inner:
                pieces.append(f'[{MARKERS[node.tag]}: {inner}]')
            elif raw:
                pieces.append(' ')
        elif node.tag == P_TAG:
            pieces.append('\n')
            _collect_text(node, pieces)
            pieces.append('\n')
        else:
            _collect_text(node, pieces)


def _text_from_element(element: ET.Element) -> str:
    pieces: list[str] = []
    _collect_text(element, pieces)
    return ''.join(pieces)


def _paragraphs(element: ET.Element):
    for node in element:
        if node.tag == P_TAG:
            yield node
        elif node.tag != FALLBACK_TAG:
            yield from _paragraphs(node)


def _heading_level(paragraph: ET.Element) -> int | None:
    style = paragraph.find('./w:pPr/w:pStyle', NS)
    if style is None:
        return None
    value = style.get(f'{{{W}}}val') or ''
    match = re.search(r'Heading\s*([1-6])$', value, re.IGNORECASE)
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
                for p in _paragraphs(cell)
            ]
            cells.append(' '.join(x for x in paragraphs if x))
        rows.append('\t'.join(cells))
    return '\n'.join(row for row in rows if row.strip())


def _part_relationships(zf: zipfile.ZipFile, part: str) -> dict[str, str]:
    name = part.replace('word/', 'word/_rels/', 1) + '.rels'
    if name not in zf.namelist():
        return {}
    root = ET.fromstring(zf.read(name))
    return {rel.get('Id'): rel.get('Target') for rel in root.iter(PKG_REL)}


def _iter_live(element: ET.Element):
    """Descendants in document order; an mc:Fallback subtree is never read."""
    for node in element:
        if node.tag == FALLBACK_TAG:
            continue
        yield node
        yield from _iter_live(node)


def _drawing_alt(drawing: ET.Element) -> str | None:
    for node in _iter_live(drawing):
        if node.tag == f'{{{WP}}}docPr':
            return node.get('descr') or node.get('title') or None
    return None


def _drawing_item(node: ET.Element, rels: dict[str, str]) -> tuple[str, str | None] | None:
    """(kind, target) when node is a DrawingML picture, chart or diagram reference."""
    if node.tag == f'{{{A}}}blip':
        return 'image', rels.get(node.get(f'{{{R}}}embed') or node.get(f'{{{R}}}link'))
    if node.tag in (f'{{{C}}}chart', f'{{{CX}}}chart'):
        return 'diagram', rels.get(node.get(f'{{{R}}}id'))
    if node.tag == f'{{{DGM}}}relIds':
        return 'diagram', rels.get(node.get(f'{{{R}}}dm'))
    return None


def _record_media(
    element: ET.Element, rels: dict[str, str], media: MediaCollector, position: int,
    drawing: ET.Element | None = None,
) -> None:
    """Record pictures, charts, diagrams, VML images and OLE objects under element, once
    each and in document order. drawing is the outermost enclosing w:drawing (its
    wp:docPr gives the alt text). A w:object is one reference: nothing inside it is
    recorded again."""
    for node in element:
        if node.tag == FALLBACK_TAG:
            continue
        if node.tag == OBJECT_TAG:
            ole = next((n for n in _iter_live(node) if n.tag == f'{{{O}}}OLEObject'), None)
            rid = ole.get(f'{{{R}}}id') if ole is not None else None
            media.add(position, 'embedded', 'ole_object', rels.get(rid))
            continue
        if node.tag == IMAGEDATA_TAG:
            media.add(position, 'image', 'vml_image', rels.get(node.get(f'{{{R}}}id')))
            continue
        item = _drawing_item(node, rels) if drawing is not None else None
        if item:
            media.add(position, item[0], 'drawing', item[1], _drawing_alt(drawing))
        enclosing = drawing if drawing is not None else (node if node.tag == DRAWING_TAG else None)
        _record_media(node, rels, media, position, enclosing)


def _walk_blocks(
    root: ET.Element, part: str, rels: dict[str, str], media: MediaCollector, base: int
) -> list[Block]:
    blocks: list[Block] = []
    headings: list[str | None] = [None] * 6
    block_index = 0

    def path() -> list[str]:
        return [value for value in headings if value is not None]

    def walk(parent: ET.Element) -> None:
        nonlocal block_index
        for child in list(parent):
            if child.tag == FALLBACK_TAG:
                continue
            if child.tag in (TBL_TAG, P_TAG):
                _record_media(child, rels, media, base + len(blocks))
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
                        for idx in range(level, len(headings)):
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
    media = MediaCollector()
    with zipfile.ZipFile(source) as zf:
        parts = sorted((name for name in zf.namelist() if _story_part(name)), key=_part_sort_key)
        if 'word/document.xml' not in parts:
            raise ValueError('DOCX is missing word/document.xml')
        for part in parts:
            root = ET.fromstring(zf.read(part))
            blocks.extend(_walk_blocks(root, part, _part_relationships(zf, part), media, len(blocks)))
    media.apply(blocks)
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
    raise SystemExit(run_cli(main))
