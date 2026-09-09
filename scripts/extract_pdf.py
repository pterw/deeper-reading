#!/usr/bin/env python3
"""Portable exhaustive PDF text extractor with runtime backend detection."""

from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import subprocess

from chunk_common import Block, build_manifest, manifest_output_path, pack_blocks, write_manifest

BACKENDS = ('pypdf', 'pymupdf', 'pdfplumber', 'pdftotext')


def _extract_pypdf(source: Path, password: str | None) -> list[str]:
    from pypdf import PdfReader
    reader = PdfReader(str(source))
    if reader.is_encrypted:
        if password is None or not reader.decrypt(password):
            raise RuntimeError('PDF is encrypted; provide --password')
    return [(page.extract_text() or '') for page in reader.pages]


def _extract_pymupdf(source: Path, password: str | None) -> list[str]:
    import fitz
    doc = fitz.open(str(source))
    if doc.needs_pass:
        if password is None or not doc.authenticate(password):
            raise RuntimeError('PDF is encrypted; provide --password')
    try:
        return [page.get_text('text') or '' for page in doc]
    finally:
        doc.close()


def _extract_pdfplumber(source: Path, password: str | None) -> list[str]:
    import pdfplumber
    with pdfplumber.open(str(source), password=password) as pdf:
        return [(page.extract_text() or '') for page in pdf.pages]


def _extract_pdftotext(source: Path, password: str | None) -> list[str]:
    exe = shutil.which('pdftotext')
    if not exe:
        raise RuntimeError('pdftotext executable is not available')
    args = [exe]
    if password:
        args.extend(['-upw', password])
    args.extend([str(source), '-'])
    result = subprocess.run(args, capture_output=True, check=False)
    if result.returncode != 0:
        stderr = result.stderr.decode('utf-8', errors='replace')
        raise RuntimeError(f'pdftotext failed: {stderr.strip()}')
    text = result.stdout.decode('utf-8', errors='replace')
    pages = text.split('\f')
    if pages and pages[-1] == '':
        pages.pop()
    return pages


def _backend_available(name: str) -> bool:
    try:
        if name == 'pypdf':
            import pypdf  # noqa: F401
            return True
        if name == 'pymupdf':
            import fitz  # noqa: F401
            return True
        if name == 'pdfplumber':
            import pdfplumber  # noqa: F401
            return True
        if name == 'pdftotext':
            return shutil.which('pdftotext') is not None
    except Exception:
        return False
    return False


def choose_backend(requested: str) -> str:
    if requested != 'auto':
        if requested not in BACKENDS:
            raise ValueError(f'unknown PDF backend: {requested}')
        if not _backend_available(requested):
            raise RuntimeError(f'requested PDF backend is unavailable: {requested}')
        return requested
    for name in BACKENDS:
        if _backend_available(name):
            return name
    raise RuntimeError(
        'No portable PDF text backend is available. Install pypdf, PyMuPDF, '
        'pdfplumber, or provide the pdftotext executable.'
    )


def _page_blocks(pages: list[str]) -> list[Block]:
    blocks: list[Block] = []
    for page_number, raw in enumerate(pages, start=1):
        text = raw.replace('\r\n', '\n').replace('\r', '\n')
        if text and not text.endswith('\n'):
            text += '\n'
        blocks.append(Block(
            text,
            {
                'kind': 'page',
                'pages': [page_number],
                'text_extracted': bool(text.strip()),
            },
        ))
    return blocks


def _pack_pages(blocks: list[Block], max_bytes: int) -> list[dict]:
    nonempty = [block for block in blocks if block.text]
    packed = pack_blocks(nonempty, max_bytes)
    present_pages: set[int] = set()
    for item in packed:
        locators = item.get('locator', {}).get('blocks', [])
        pages = sorted({p for loc in locators for p in loc.get('pages', [])})
        item['locator']['pages'] = pages
        present_pages.update(pages)
    for block in blocks:
        page = block.locator['pages'][0]
        if page not in present_pages:
            packed.append({
                'content': '',
                'locator': dict(block.locator),
                'oversize_atomic': False,
            })
    packed.sort(key=lambda item: min(item.get('locator', {}).get('pages', [10**9])))
    return packed


def extract(
    source: Path,
    *,
    max_bytes: int,
    source_uri: str | None = None,
    backend: str = 'auto',
    password: str | None = None,
) -> dict:
    selected = choose_backend(backend)
    if selected == 'pypdf':
        pages = _extract_pypdf(source, password)
    elif selected == 'pymupdf':
        pages = _extract_pymupdf(source, password)
    elif selected == 'pdfplumber':
        pages = _extract_pdfplumber(source, password)
    else:
        pages = _extract_pdftotext(source, password)
    packed = _pack_pages(_page_blocks(pages), max_bytes)
    return build_manifest(
        source,
        'pdf',
        packed,
        strategy='pdf-page-text',
        max_bytes=max_bytes,
        source_uri=source_uri,
        backend=selected,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description='Extract PDF text into exhaustive page-located chunks')
    parser.add_argument('source', type=Path)
    output = parser.add_mutually_exclusive_group(required=True)
    output.add_argument('--out', type=Path)
    output.add_argument('--run-root', type=Path)
    parser.add_argument('--max-bytes', type=int, default=12000)
    parser.add_argument('--source-uri')
    parser.add_argument('--backend', choices=('auto',) + BACKENDS, default='auto')
    parser.add_argument('--password')
    args = parser.parse_args()
    out = manifest_output_path(out=args.out, run_root=args.run_root)
    manifest = extract(
        args.source,
        max_bytes=args.max_bytes,
        source_uri=args.source_uri,
        backend=args.backend,
        password=args.password,
    )
    write_manifest(manifest, out)
    print(f'Wrote {len(manifest["chunks"])} chunks using {manifest["chunking"]["backend"]} to {out}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
