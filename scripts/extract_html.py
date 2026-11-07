#!/usr/bin/env python3
"""Portable exhaustive HTML extractor using the Python standard library."""

from __future__ import annotations

import argparse
from html.parser import HTMLParser
from pathlib import Path
from script_io import run_cli
import re

from chunk_common import Block, build_manifest, manifest_output_path, pack_blocks, write_manifest

HEADING_LEVELS = {f'h{level}': level for level in range(1, 7)}
SKIP_TAGS = {'script', 'style', 'noscript', 'template'}
FLOW_BOUNDARY_TAGS = {
    'address', 'article', 'aside', 'blockquote', 'body', 'dd', 'div', 'dt',
    'details', 'figcaption', 'footer', 'header', 'hr', 'html', 'li', 'main',
    'nav', 'ol', 'p', 'section', 'summary', 'ul',
}
SPACE_TAGS = {'br', 'input'}
CELL_SPACE_TAGS = FLOW_BOUNDARY_TAGS | set(HEADING_LEVELS)
HEADING_CLOSING_TAGS = FLOW_BOUNDARY_TAGS | {'table', 'pre'}


def _clean(text: str) -> str:
    return re.sub(r'\s+', ' ', text).strip()


class StructuralHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.blocks: list[Block] = []
        self.headings: list[str | None] = [None] * 6
        self.skip_depth = 0
        self.flow: list[str] = []
        self.flow_has_text = False
        self.flow_heading_path: list[str] = []
        self.heading_tag: str | None = None
        self.heading_text: list[str] = []
        self.table_depth = 0
        self.table: list[str] = []
        self.cell: list[str] = []
        self.in_cell = False
        self.table_heading_path: list[str] = []
        self.pre_depth = 0
        self.pre: list[str] = []
        self.pre_heading_path: list[str] = []

    def _path(self) -> list[str]:
        return [value for value in self.headings if value is not None]

    def _flush_flow(self) -> None:
        text = _clean(''.join(self.flow))
        if text:
            self.blocks.append(Block(
                text + '\n',
                {'kind': 'text', 'heading_path': list(self.flow_heading_path)},
            ))
        self.flow = []
        self.flow_has_text = False
        self.flow_heading_path = []

    def _close_heading(self) -> None:
        text = _clean(''.join(self.heading_text))
        if text and self.heading_tag is not None:
            level = HEADING_LEVELS[self.heading_tag]
            self.headings[level - 1] = text
            for idx in range(level, len(self.headings)):
                self.headings[idx] = None
            self.blocks.append(Block(
                text + '\n',
                {'kind': 'heading', 'level': level, 'heading_path': self._path()},
            ))
        self.heading_tag = None
        self.heading_text = []

    def _heading_has_text(self) -> bool:
        return self.heading_tag is not None and any(part.strip() for part in self.heading_text)

    def _flush_cell(self) -> None:
        text = _clean(''.join(self.cell))
        self.cell = []
        if self.in_cell:
            self.table.append(text + '\t')
            self.in_cell = False
        elif text:
            self.table.append(text + ' ')

    def _end_table(self) -> None:
        self._flush_cell()
        self.table_depth -= 1
        if self.table_depth == 0:
            text = ''.join(self.table).strip()
            if text:
                self.blocks.append(Block(
                    text + '\n',
                    {'kind': 'table', 'heading_path': self.table_heading_path},
                    atomic_kind='table',
                ))

    def _end_pre(self) -> None:
        self.pre_depth -= 1
        if self.pre_depth == 0:
            text = ''.join(self.pre).strip('\n')
            if text:
                self.blocks.append(Block(
                    text + '\n',
                    {'kind': 'pre', 'heading_path': self.pre_heading_path},
                    atomic_kind='pre',
                ))

    def _add_space(self, tag: str) -> None:
        if self.table_depth:
            self.cell.append(' ')
        elif self.pre_depth:
            self.pre.append('\n' if tag == 'br' else ' ')
        elif self.heading_tag is not None:
            self.heading_text.append(' ')
        elif self.flow:
            self.flow.append(' ')

    def handle_starttag(self, tag: str, attrs) -> None:
        tag = tag.lower()
        if tag in SKIP_TAGS:
            self._flush_flow()
            self.skip_depth += 1
            return
        if self.skip_depth:
            return
        if tag in SPACE_TAGS:
            self._add_space(tag)
            return
        if tag in HEADING_LEVELS or tag in HEADING_CLOSING_TAGS:
            if self._heading_has_text():
                self._close_heading()
        if tag == 'table':
            self._flush_flow()
            if self.table_depth == 0:
                self.table = []
                self.cell = []
                self.in_cell = False
                self.table_heading_path = self._path()
            else:
                self._flush_cell()
            self.table_depth += 1
            return
        if self.table_depth:
            if tag in {'td', 'th'}:
                self._flush_cell()
                self.in_cell = True
            elif tag in CELL_SPACE_TAGS:
                self.cell.append(' ')
            return
        if tag == 'pre':
            self._flush_flow()
            if self.pre_depth == 0:
                self.pre = []
                self.pre_heading_path = self._path()
            self.pre_depth += 1
            return
        if self.pre_depth:
            return
        if tag in HEADING_LEVELS:
            self._flush_flow()
            self.heading_tag = tag
            self.heading_text = []
            return
        if tag in FLOW_BOUNDARY_TAGS:
            self._flush_flow()

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in SKIP_TAGS:
            if self.skip_depth:
                self.skip_depth -= 1
            return
        if self.skip_depth:
            return
        if self.table_depth:
            if tag in {'td', 'th'}:
                self._flush_cell()
            elif tag == 'tr':
                self._flush_cell()
                self.table.append('\n')
            if tag == 'table':
                self._end_table()
            elif tag in CELL_SPACE_TAGS:
                self.cell.append(' ')
            return
        if self.pre_depth:
            if tag == 'pre':
                self._end_pre()
            return
        if tag in HEADING_LEVELS:
            self._close_heading()
            return
        if tag in HEADING_CLOSING_TAGS and self._heading_has_text():
            self._close_heading()
        if tag in FLOW_BOUNDARY_TAGS:
            self._flush_flow()

    def handle_data(self, data: str) -> None:
        if self.skip_depth:
            return
        if self.table_depth:
            self.cell.append(data)
            return
        if self.pre_depth:
            self.pre.append(data)
            return
        if self.heading_tag is not None:
            self.heading_text.append(data)
            return
        if data.strip() and not self.flow_has_text:
            self.flow_has_text = True
            self.flow_heading_path = self._path()
        self.flow.append(data)

    def finish(self) -> None:
        self._close_heading()
        while self.table_depth:
            self._end_table()
        while self.pre_depth:
            self._end_pre()
        self._flush_flow()


def extract(source: Path, *, max_bytes: int, source_uri: str | None = None) -> dict:
    parser = StructuralHTMLParser()
    parser.feed(source.read_text(encoding='utf-8-sig'))
    parser.close()
    parser.finish()
    packed = pack_blocks(parser.blocks, max_bytes)
    return build_manifest(
        source,
        'html',
        packed,
        strategy='html-heading-structural-blocks',
        max_bytes=max_bytes,
        source_uri=source_uri,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description='Extract HTML into exhaustive structural chunks')
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
