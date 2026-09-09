#!/usr/bin/env python3
"""Portable exhaustive HTML extractor using the Python standard library."""

from __future__ import annotations

import argparse
from html.parser import HTMLParser
from pathlib import Path
import re

from chunk_common import Block, build_manifest, manifest_output_path, pack_blocks, write_manifest

BLOCK_TAGS = {'p', 'li', 'blockquote', 'dt', 'dd', 'figcaption', 'caption'}
SKIP_TAGS = {'script', 'style', 'noscript'}


def _clean(text: str) -> str:
    return re.sub(r'\s+', ' ', text).strip()


class StructuralHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.blocks: list[Block] = []
        self.headings: list[str | None] = [None, None, None]
        self.skip_depth = 0
        self.capture_tag: str | None = None
        self.capture: list[str] = []
        self.capture_heading_path: list[str] = []
        self.table_depth = 0
        self.table: list[str] = []
        self.table_heading_path: list[str] = []
        self.pre_depth = 0
        self.pre: list[str] = []
        self.pre_heading_path: list[str] = []

    def _path(self) -> list[str]:
        return [value for value in self.headings if value is not None]

    def handle_starttag(self, tag: str, attrs) -> None:
        tag = tag.lower()
        if tag in SKIP_TAGS:
            self.skip_depth += 1
            return
        if self.skip_depth:
            return
        if tag == 'table':
            if self.table_depth == 0:
                self.table = []
                self.table_heading_path = self._path()
            self.table_depth += 1
            return
        if self.table_depth:
            return
        if tag == 'pre':
            if self.pre_depth == 0:
                self.pre = []
                self.pre_heading_path = self._path()
            self.pre_depth += 1
            return
        if self.pre_depth:
            return
        if tag in {'h1', 'h2', 'h3'} or tag in BLOCK_TAGS:
            self.capture_tag = tag
            self.capture = []
            self.capture_heading_path = self._path()

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
                self.table.append('\t')
            elif tag == 'tr':
                self.table.append('\n')
            if tag == 'table':
                self.table_depth -= 1
                if self.table_depth == 0:
                    text = ''.join(self.table).strip()
                    if text:
                        self.blocks.append(Block(
                            text,
                            {'kind': 'table', 'heading_path': self.table_heading_path},
                            atomic_kind='table',
                        ))
            return
        if self.pre_depth:
            if tag == 'pre':
                self.pre_depth -= 1
                if self.pre_depth == 0:
                    text = ''.join(self.pre).strip('\n')
                    if text:
                        self.blocks.append(Block(
                            text,
                            {'kind': 'pre', 'heading_path': self.pre_heading_path},
                            atomic_kind='pre',
                        ))
            return
        if self.capture_tag != tag:
            return
        text = _clean(''.join(self.capture))
        if text:
            if tag in {'h1', 'h2', 'h3'}:
                level = int(tag[1])
                self.headings[level - 1] = text
                for idx in range(level, 3):
                    self.headings[idx] = None
                path = self._path()
                self.blocks.append(Block(
                    text + '\n',
                    {'kind': 'heading', 'level': level, 'heading_path': path},
                ))
            else:
                self.blocks.append(Block(
                    text + '\n',
                    {'kind': tag, 'heading_path': self.capture_heading_path},
                ))
        self.capture_tag = None
        self.capture = []

    def handle_data(self, data: str) -> None:
        if self.skip_depth:
            return
        if self.table_depth:
            if data.strip():
                self.table.append(_clean(data))
            return
        if self.pre_depth:
            self.pre.append(data)
            return
        if self.capture_tag is not None:
            self.capture.append(data)


def extract(source: Path, *, max_bytes: int, source_uri: str | None = None) -> dict:
    parser = StructuralHTMLParser()
    parser.feed(source.read_text(encoding='utf-8-sig'))
    parser.close()
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
    raise SystemExit(main())
