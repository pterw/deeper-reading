#!/usr/bin/env python3
"""Portable exhaustive Markdown extractor with structural chunking."""

from __future__ import annotations

import argparse
import html
from pathlib import Path
from script_io import run_cli
import re

from chunk_common import (
    Block,
    MediaCollector,
    build_manifest,
    manifest_output_path,
    pack_blocks,
    write_manifest,
)

HEADING_RE = re.compile(r'^(#{1,6})\s+(.+?)\s*$')
TABLE_SEP_RE = re.compile(r'^\s*\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)*\|?\s*$')
FENCE_RE = re.compile(r'^\s*(```+|~~~+)')
CLOSING_HASHES_RE = re.compile(r'\s+#+$')


def _is_table_separator(line: str) -> bool:
    line = line.rstrip('\r\n')
    return '|' in line and TABLE_SEP_RE.match(line) is not None


def _closes_fence(line: str, marker: str) -> bool:
    body = line.strip()
    return len(body) >= len(marker) and body == body[0] * len(body) and body[0] == marker[0]


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
                closes = _closes_fence(lines[i], marker)
                i += 1
                if closes:
                    break
            blocks.append(Block(
                ''.join(fence_lines).rstrip('\r\n') + '\n',
                {'kind': 'fenced_code', 'heading_path': _heading_path(headings)},
                atomic_kind='fenced_code',
            ))
            continue

        heading = HEADING_RE.match(stripped)
        if heading:
            level = len(heading.group(1))
            title = CLOSING_HASHES_RE.sub('', heading.group(2).strip())
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
            and _is_table_separator(lines[i + 1])
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
                ''.join(table_lines).rstrip('\r\n') + '\n',
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
                and _is_table_separator(lines[i + 1])
            ):
                break
            para_lines.append(candidate)
            i += 1
        blocks.append(Block(
            ''.join(para_lines),
            {'kind': 'text', 'heading_path': _heading_path(headings)},
        ))

    return blocks


_BACKTICK_RUN_RE = re.compile(r'`+')
_IMAGE_EXTENSIONS = ('.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.svg')
_DIAGRAM_INFO = frozenset({'mermaid', 'plantuml', 'dot', 'graphviz', 'd2'})
# Balanced delimiters nest one level only (CommonMark allows more); each alternative starts
# with a different character, so the patterns stay linear on long runs of brackets.
_BRACKETED = r'(?:[^\[\]]|\[[^\[\]]*\])*'
_PARENTHESISED = r'(?:[^()]|\([^()]*\))*'
_DESTINATION = r'(?:<[^>]*>|(?:[^()\s]|\([^()\s]*\))*)'
# The destination sits in a lookahead that is then consumed by a backreference: an atomic group
# (Python 3.10 has none), so a missing `)` fails without retrying every shorter destination.
_MD_IMAGE_RE = re.compile(
    rf'!\[({_BRACKETED})\](?:\(\s*(?=({_DESTINATION}))\2[^)]*\)|\[([^\]]*)\])?'
)
_MD_LINK_RE = re.compile(
    rf'(?<!!)\[(?:[^\[\]!]|!(?!\[)|\[[^\[\]]*\]|!\[{_BRACKETED}\]\({_PARENTHESISED}\))*\]'
    rf'\(\s*(?=({_DESTINATION}))\1[^)]*\)'
)
_HTML_COMMENT_RE = re.compile(r'<!--.*?-->', re.DOTALL)
_LINK_DEFINITION_RE = re.compile(r'^ {0,3}\[((?:[^\]\\]|\\.)+)\]:\s*\S', re.MULTILINE)
_HTML_IMG_RE = re.compile(r'<img\b[^>]*>', re.IGNORECASE)
_HTML_SVG_TAG_RE = re.compile(r'<(/?)svg\b', re.IGNORECASE)
_HTML_DIAGRAM_RE = re.compile(r'<(?:pre|div)\b[^>]*>', re.IGNORECASE)


def _attr(tag: str, name: str) -> str | None:
    match = re.search(
        rf'(?<![\w-]){name}\s*=\s*(?:"([^"]*)"|\'([^\']*)\'|([^\s>]+))', tag, re.IGNORECASE
    )
    if match is None:
        return None
    return html.unescape(next(group for group in match.groups() if group is not None))


def _link_target(raw: str) -> str:
    return raw[1:-1] if raw.startswith('<') and raw.endswith('>') else raw


def _is_image_target(target: str) -> bool:
    return re.split(r'[?#]', target, maxsplit=1)[0].lower().endswith(_IMAGE_EXTENSIONS)


def _svg_starts(text: str) -> list[int]:
    """Offsets of outermost <svg tags; nested svg and stray closers are skipped."""
    starts: list[int] = []
    depth = 0
    for match in _HTML_SVG_TAG_RE.finditer(text):
        if match.group(1):
            depth = max(depth - 1, 0)
        else:
            if depth == 0:
                starts.append(match.start())
            depth += 1
    return starts


def _mask_code_spans(text: str) -> str:
    """Blank code spans: a complete backtick run closes on the next run of equal length."""
    runs = [match.span() for match in _BACKTICK_RUN_RE.finditer(text)]
    next_same: list[int | None] = [None] * len(runs)
    latest: dict[int, int] = {}
    for index in range(len(runs) - 1, -1, -1):
        length = runs[index][1] - runs[index][0]
        next_same[index] = latest.get(length)
        latest[length] = index
    pieces: list[str] = []
    position = index = 0
    while index < len(runs):
        closer = next_same[index]
        if closer is None:
            index += 1
            continue
        start, end = runs[index][0], runs[closer][1]
        pieces.append(text[position:start])
        pieces.append(' ' * (end - start))
        position = end
        index = closer + 1
    pieces.append(text[position:])
    return ''.join(pieces)


def _label_key(label: str) -> str:
    return ' '.join(label.split()).casefold()


def _definition_labels(blocks: list[Block]) -> set[str]:
    """Normalised labels of the link definitions `[label]: url` in the non-fenced text."""
    return {
        _label_key(match.group(1))
        for block in blocks
        if block.locator.get('kind') != 'fenced_code'
        for match in _LINK_DEFINITION_RE.finditer(block.text)
    }


def _text_media(
    text: str, definitions: frozenset[str] | set[str] = frozenset()
) -> list[tuple[int, str, str, str | None, str | None]]:
    """Media references in non-code Markdown text, as (offset, kind, syntax, ref, alt)."""
    text = _mask_code_spans(text)
    text = _HTML_COMMENT_RE.sub(lambda match: ' ' * len(match.group(0)), text)
    found: list[tuple[int, str, str, str | None, str | None]] = []
    for match in _MD_IMAGE_RE.finditer(text):
        alt, target, label = match.groups()
        if target is None and label is None and _label_key(alt) not in definitions:
            continue
        ref = _link_target(target) if target is not None else (label or alt)
        found.append((match.start(), 'image', 'md_image', ref or None, alt))
    for match in _MD_LINK_RE.finditer(text):
        target = _link_target(match.group(1))
        if _is_image_target(target):
            found.append((match.start(), 'image', 'md_link', target, None))
    for match in _HTML_IMG_RE.finditer(text):
        tag = match.group(0)
        ref = _attr(tag, 'src') or _attr(tag, 'data-src')
        found.append((match.start(), 'image', 'html_img', ref, _attr(tag, 'alt')))
    found.extend((start, 'svg', 'html_svg', None, None) for start in _svg_starts(text))
    for match in _HTML_DIAGRAM_RE.finditer(text):
        if 'mermaid' in (_attr(match.group(0), 'class') or '').split():
            found.append((match.start(), 'diagram', 'html_diagram', None, None))
    return sorted(found, key=lambda item: item[0])


def _fence_diagram(text: str) -> bool:
    info = FENCE_RE.sub('', text.split('\n', 1)[0], count=1).strip().split()
    return bool(info) and info[0].lower() in _DIAGRAM_INFO


def collect_media(blocks: list[Block]) -> None:
    """Record media references on the blocks that hold them, in document order."""
    collector = MediaCollector()
    definitions = _definition_labels(blocks)
    for index, block in enumerate(blocks):
        if block.locator.get('kind') == 'fenced_code':
            if _fence_diagram(block.text):
                collector.add(index, 'diagram', 'fence_diagram')
            continue
        for _, kind, syntax, ref, alt in _text_media(block.text, definitions):
            collector.add(index, kind, syntax, ref, alt)
    collector.apply(blocks)


def extract(source: Path, *, max_bytes: int, source_uri: str | None = None) -> dict:
    text = source.read_text(encoding='utf-8-sig')
    blocks = parse_markdown_blocks(text)
    collect_media(blocks)
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
