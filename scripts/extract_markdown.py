#!/usr/bin/env python3
"""Portable exhaustive Markdown extractor with structural chunking."""

from __future__ import annotations

import argparse
import bisect
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


_IMAGE_EXTENSIONS = ('.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.svg')
_DIAGRAM_INFO = frozenset({'mermaid', 'plantuml', 'dot', 'graphviz', 'd2'})
_OPENING_FENCE_RE = re.compile(r'^ {0,3}(`{3,}|~{3,})(.*)$')
_CLOSING_FENCE_RE = re.compile(r'^ {0,3}(`+|~+)[ \t]*$')
# Balanced delimiters nest one level only (CommonMark allows more); each alternative starts
# with a different character, so the patterns stay linear on long runs of brackets.
# A backslash escapes the next character, so an escaped bracket never ends the text.
_BRACKETED = r'(?:\\[\s\S]|[^\[\]\\]|\[(?:\\[\s\S]|[^\[\]\\])*\])*'
_PARENTHESISED = r'(?:[^()]|\([^()]*\))*'
# The link pattern first steps over `\x`, so an escaped bracket never starts a scan that runs
# to the end of the text; `\!` is left alone so it can still start an image.
_ESCAPED = r'\\[^!]'
# Every `<img`, `<div` and `<pre` start is found by the plain scan, which ends a tag at the next
# `>`. The quote-aware form only reads the tag's attributes: a quoted value may hold `>` but not
# `<`, so it never spans the next tag, and a tag it cannot read falls back to the plain body.
_TAG_QUOTED = r"""[^>"']*(?:(?:"[^"<]*"|'[^'<]*')[^>"']*){0,32}>"""
# The svg tail ignores quote tricks: a miss there only treats a self-closing svg as unclosed.
_SVG_TAIL = r"""(?:[^<>"']|"[^"]*"|'[^']*')*>"""
# A backslash escape (`\)`, `\(`) belongs to the destination, so an escaped `)` does not end it.
_DEST_ATOM = r'\\\S|[^()\s\\]|\\(?!\S)'
_DESTINATION = rf'(?:<[^<>]*>|(?:{_DEST_ATOM}|\((?:{_DEST_ATOM})*\))*)'
# The destination sits in a lookahead that is then consumed by a backreference: an atomic group
# (Python 3.10 has none), so a missing `)` fails without retrying every shorter destination.
# The closing `)` is looked up by `_md_matches`, not found by a pattern that rescans to the end.
_MD_IMAGE_RE = re.compile(
    rf'!\[({_BRACKETED})\](?:\(\s*(?=({_DESTINATION}))\2|\[([^\]]*)\])?'
)
_MD_LINK_RE = re.compile(
    rf'{_ESCAPED}|(?<!!)\[(?:\\[\s\S]|[^\[\]!\\]|!(?!\[)|\[(?:\\[\s\S]|[^\[\]\\])*\]'
    rf'|!\[{_BRACKETED}\]\({_PARENTHESISED}\))*\]'
    rf'\(\s*(?=({_DESTINATION}))\1'
)
_HTML_IMG_RE = re.compile(r'<img\b[^>]*>', re.IGNORECASE)
_HTML_IMG_QUOTED_RE = re.compile(rf'<img\b{_TAG_QUOTED}', re.IGNORECASE)
_HTML_SVG_TAG_RE = re.compile(r'<(/?)svg\b', re.IGNORECASE)
_HTML_TAG_TAIL_RE = re.compile(_SVG_TAIL)
_HTML_DIAGRAM_RE = re.compile(r'<(?:pre|div)\b[^>]*>', re.IGNORECASE)
_HTML_DIAGRAM_QUOTED_RE = re.compile(rf'<(?:pre|div)\b{_TAG_QUOTED}', re.IGNORECASE)


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
    """Offsets of <svg tags, minus those nested inside an outer svg that closes later.

    A self-closing <svg/> opens and closes at once; an unclosed <svg hides nothing after it.
    """
    tokens: list[tuple[int, bool, bool]] = []  # (offset, is closer, is self-closing)
    open_tokens: list[int] = []
    closed_at: dict[int, int] = {}
    for match in _HTML_SVG_TAG_RE.finditer(text):
        index = len(tokens)
        closer = bool(match.group(1))
        tail = None if closer else _HTML_TAG_TAIL_RE.match(text, match.end())
        self_closing = tail is not None and text[tail.end() - 2] == '/'
        tokens.append((match.start(), closer, self_closing))
        if closer and open_tokens:
            closed_at[open_tokens.pop()] = match.start()
        elif not closer and not self_closing:
            open_tokens.append(index)
    starts: list[int] = []
    covered_until = -1
    for index, (offset, closer, _) in enumerate(tokens):
        if closer or offset < covered_until:
            continue
        starts.append(offset)
        covered_until = closed_at.get(index, covered_until)
    return starts


def _html_tags(text: str, plain: re.Pattern, quoted: re.Pattern):
    """Yield (offset, tag) for each tag start the plain scan finds, read quote-aware if it can."""
    for match in plain.finditer(text):
        yield match.start(), (quoted.match(text, match.start()) or match).group(0)


def _md_scan(text: str, regex: re.Pattern, group: int, closers: list[int], starts: list[int] | None):
    """Yield (match, destination) scanning left to right; see `_md_matches`.

    With `starts`, a match whose `)` lies beyond another reference start is not skipped past
    that `)`: the scan resumes right after its `](`.
    """
    pos = 0
    while (match := regex.search(text, pos)) is not None:
        target = match.group(group)
        pos = match.end()
        if target is not None:
            index = bisect.bisect_left(closers, pos)
            start = bisect.bisect_left(starts, match.start(group)) if starts is not None else 0
            if index == len(closers):
                target, pos = None, match.start() + 1
            elif starts is not None and start < len(starts) and starts[start] < closers[index]:
                pos = match.start(group)
            else:
                pos = closers[index] + 1
        yield match, target


def _md_matches(text: str, regex: re.Pattern, group: int):
    """Yield (match, destination) for each Markdown image or link match.

    The destination is None when the match has none or no `)` follows it. The closing `)` is the
    next one after the destination, looked up in the list of every `)`, so a missing one costs a
    lookup, not a scan to the end. A match with a closing `)` is skipped past it. A second scan
    resumes right after the `](` when another reference starts (`![` or `](`) before that `)`, so
    a reference inside a malformed outer one is found too; it adds matches, never drops one.
    """
    closers = [match.start() for match in re.finditer(r'\)', text)]
    starts = [match.start() for match in re.finditer(r'!\[|\]\(', text)]
    seen: set[int] = set()
    for resume in (None, starts):
        for match, target in _md_scan(text, regex, group, closers, resume):
            if match.start() not in seen:
                seen.add(match.start())
                yield match, target


def _text_media(text: str) -> list[tuple[int, str, str, str | None, str | None]]:
    """Media references in Markdown text, as (offset, kind, syntax, ref, alt)."""
    found: list[tuple[int, str, str, str | None, str | None]] = []
    for match, target in _md_matches(text, _MD_IMAGE_RE, 2):
        alt, label = match.group(1), match.group(3)
        ref = _link_target(target) if target is not None else (label or alt)
        found.append((match.start(), 'image', 'md_image', ref or None, alt))
    for match, target in _md_matches(text, _MD_LINK_RE, 1):
        if target is not None and _is_image_target(_link_target(target)):
            found.append((match.start(), 'image', 'md_link', _link_target(target), None))
    tags = text[: text.rfind('>') + 1]
    for start, tag in _html_tags(tags, _HTML_IMG_RE, _HTML_IMG_QUOTED_RE):
        ref = _attr(tag, 'src') or _attr(tag, 'data-src')
        found.append((start, 'image', 'html_img', ref, _attr(tag, 'alt')))
    found.extend((start, 'svg', 'html_svg', None, None) for start in _svg_starts(text))
    for start, tag in _html_tags(tags, _HTML_DIAGRAM_RE, _HTML_DIAGRAM_QUOTED_RE):
        if 'mermaid' in (_attr(tag, 'class') or '').split():
            found.append((start, 'diagram', 'html_diagram', None, None))
    return sorted(found, key=lambda item: item[0])


def _is_closed_fence(text: str) -> bool:
    """True for a fence with a valid opener and a closer of the same character, as long."""
    lines = text.splitlines()
    opener = _OPENING_FENCE_RE.match(lines[0])
    closer = _CLOSING_FENCE_RE.match(lines[-1]) if len(lines) > 1 else None
    if opener is None or closer is None:
        return False
    fence, info = opener.groups()
    if fence[0] == '`' and '`' in info:
        return False
    return closer.group(1)[0] == fence[0] and len(closer.group(1)) >= len(fence)


def _fence_diagram(text: str) -> bool:
    info = FENCE_RE.sub('', text.split('\n', 1)[0], count=1).strip().split()
    return bool(info) and info[0].lower() in _DIAGRAM_INFO


def collect_media(blocks: list[Block]) -> None:
    """Record media references on the blocks that hold them, in document order."""
    collector = MediaCollector()
    for index, block in enumerate(blocks):
        if block.locator.get('kind') == 'fenced_code':
            if _fence_diagram(block.text):
                collector.add(index, 'diagram', 'fence_diagram')
            if _is_closed_fence(block.text):
                continue
        for _, kind, syntax, ref, alt in _text_media(block.text):
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
