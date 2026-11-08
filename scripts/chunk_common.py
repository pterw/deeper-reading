#!/usr/bin/env python3
"""Shared deterministic chunk-manifest utilities for portable extractors."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Iterable
try:
    from script_io import validate_output, write_text_atomic
except ModuleNotFoundError:
    from .script_io import validate_output, write_text_atomic

try:
    from chunk_view import block_kinds, compact_locator
except ModuleNotFoundError:  # package-style imports in tests
    from .chunk_view import block_kinds, compact_locator

SCHEMA_VERSION = 1

RUN_EVIDENCE_DIR = "evidence"
RUN_DELIVERABLES_DIR = "deliverables"
CANONICAL_MANIFEST_NAME = "chunk-manifest.json"
CANONICAL_EVIDENCE_NAME = "chunk-evidence.json"
CANONICAL_TRAVERSAL_REPORT_NAME = "TRAVERSAL_REPORT.md"


def canonical_run_paths(run_root: Path) -> dict[str, Path]:
    root = run_root.resolve()
    return {
        "root": root,
        "manifest": root / RUN_EVIDENCE_DIR / CANONICAL_MANIFEST_NAME,
        "chunk_evidence": root / RUN_EVIDENCE_DIR / CANONICAL_EVIDENCE_NAME,
        "traversal_report": root / RUN_DELIVERABLES_DIR / CANONICAL_TRAVERSAL_REPORT_NAME,
        "dod": root / "dod.json",
    }


def manifest_output_path(*, out: Path | None, run_root: Path | None) -> Path:
    if (out is None) == (run_root is None):
        raise ValueError("exactly one of out or run_root is required")
    if run_root is not None:
        result = canonical_run_paths(run_root)["manifest"]
        validate_output(result, root=run_root)
        return result
    assert out is not None
    return out


@dataclass(frozen=True)
class Block:
    text: str
    locator: dict[str, Any] = field(default_factory=dict)
    atomic_kind: str | None = None


MEDIA_TEXT_CAP = 200


class MediaCollector:
    """Collects media references seen while extracting and attaches them to blocks.

    An extractor calls add() with len(blocks) when it sees a reference, then apply()
    once the blocks are complete. No text is invented, so chunk text and hashes stay put.
    """

    def __init__(self) -> None:
        self._items: list[tuple[int, dict[str, Any]]] = []

    def add(
        self,
        position: int,
        kind: str,
        syntax: str,
        ref: str | None = None,
        alt: str | None = None,
    ) -> None:
        self._items.append((position, {'kind': kind, 'syntax': syntax, 'ref': ref, 'alt': alt}))

    def apply(self, blocks: list[Block]) -> None:
        """Write each entry to the first non-empty block at or after its position."""
        textual = [index for index, block in enumerate(blocks) if block.text]
        if not textual:
            return
        for position, entry in self._items:
            target = next((index for index in textual if index >= position), textual[-1])
            blocks[target].locator.setdefault('media', []).append(dict(entry))


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def utf8_len(text: str) -> int:
    return len(text.encode('utf-8'))


def _split_oversize_text(text: str, max_bytes: int) -> list[str]:
    """Split non-atomic text without dropping or inventing characters."""
    if utf8_len(text) <= max_bytes:
        return [text]
    tokens = re.findall(r'\S+\s*|\s+', text)
    pieces: list[str] = []
    current = ''
    for token in tokens:
        if utf8_len(token) > max_bytes:
            if current:
                pieces.append(current)
                current = ''
            fragment = ''
            for char in token:
                if fragment and utf8_len(fragment + char) > max_bytes:
                    pieces.append(fragment)
                    fragment = char
                else:
                    fragment += char
            if fragment:
                pieces.append(fragment)
            continue
        if current and utf8_len(current + token) > max_bytes:
            pieces.append(current)
            current = token
        else:
            current += token
    if current:
        pieces.append(current)
    return pieces


def pack_blocks(blocks: Iterable[Block], max_bytes: int) -> list[dict[str, Any]]:
    if max_bytes < 1:
        raise ValueError('max_bytes must be >= 1')

    packed: list[dict[str, Any]] = []
    current_text = ''
    current_locators: list[dict[str, Any]] = []
    current_heading: list[str] | None = None

    def flush() -> None:
        nonlocal current_text, current_locators, current_heading
        if not current_text:
            return
        locator: dict[str, Any] = {'blocks': current_locators}
        if current_heading is not None:
            locator['heading_path'] = current_heading
        packed.append({'content': current_text, 'locator': locator, 'oversize_atomic': False})
        current_text = ''
        current_locators = []
        current_heading = None

    for block in blocks:
        if not block.text:
            continue
        heading = block.locator.get('heading_path')
        heading_list = list(heading) if isinstance(heading, list) else None

        if block.atomic_kind:
            flush()
            locator = dict(block.locator)
            locator['atomic_kind'] = block.atomic_kind
            packed.append({
                'content': block.text,
                'locator': locator,
                'oversize_atomic': utf8_len(block.text) > max_bytes,
            })
            continue

        pieces = _split_oversize_text(block.text, max_bytes)
        for piece_index, piece in enumerate(pieces, start=1):
            piece_locator = dict(block.locator)
            if len(pieces) > 1:
                piece_locator['fragment'] = piece_index
                piece_locator['fragments'] = len(pieces)
                if piece_index > 1:
                    piece_locator.pop('media', None)
            if current_text and current_heading != heading_list:
                flush()
            if current_text and utf8_len(current_text + piece) > max_bytes:
                flush()
            if not current_text:
                current_heading = heading_list
            current_text += piece
            current_locators.append(piece_locator)
            if utf8_len(current_text) >= max_bytes:
                flush()

    flush()
    return packed


def _media_ref(ref: Any) -> Any:
    if not isinstance(ref, str):
        return ref
    data_uri = re.match(r'data:[^;,]*', ref)
    return (data_uri.group(0) if data_uri else ref)[:MEDIA_TEXT_CAP]


def _media_alt(alt: Any) -> Any:
    return ' '.join(alt.split())[:MEDIA_TEXT_CAP] if isinstance(alt, str) else alt


def _strip_media(locator: Any, chunk_id: str, found: list[dict[str, Any]]) -> Any:
    """Return locator without media, appending its entries (F2 id not yet set) to found."""
    if not isinstance(locator, dict):
        return locator
    clean = {key: value for key, value in locator.items() if key != 'media'}
    for entry in locator.get('media') or []:
        found.append({'chunk_id': chunk_id, **entry})
    if isinstance(clean.get('blocks'), list):
        clean['blocks'] = [_strip_media(item, chunk_id, found) for item in clean['blocks']]
    return clean


def build_manifest(
    source_path: Path,
    source_format: str,
    packed_chunks: list[dict[str, Any]],
    *,
    strategy: str,
    max_bytes: int,
    source_uri: str | None = None,
    backend: str | None = None,
) -> dict[str, Any]:
    if not ''.join(str(item['content']) for item in packed_chunks).strip():
        message = f'{source_format}: no extractable text'
        if source_format == 'pdf':
            message += ' (no text layer; OCR is needed, use the oai-native profile)'
        raise ValueError(message)
    source_bytes = source_path.read_bytes()
    source_hash = sha256_bytes(source_bytes)
    chunks: list[dict[str, Any]] = []
    cursor = 0
    stream = bytearray()
    media_found: list[dict[str, Any]] = []

    for ordinal, item in enumerate(packed_chunks, start=1):
        content = str(item['content'])
        raw = content.encode('utf-8')
        content_hash = sha256_bytes(raw)
        chunk_id = f'{source_format}-{ordinal:06d}-{content_hash[:12]}'
        locator = _strip_media(item.get('locator', {}), chunk_id, media_found)
        chunk = {
            'id': chunk_id,
            'ordinal': ordinal,
            'locator': locator,
            'text_byte_start': cursor,
            'text_byte_end': cursor + len(raw),
            'content_sha256': content_hash,
            'content': content,
            'oversize_atomic': bool(item.get('oversize_atomic', False)),
        }
        chunks.append(chunk)
        cursor += len(raw)
        stream.extend(raw)

    source = {
        'path': str(source_path.resolve()),
        'uri': source_uri or source_path.resolve().as_uri(),
        'format': source_format,
        'sha256': source_hash,
        'size_bytes': len(source_bytes),
    }
    chunking: dict[str, Any] = {
        'strategy': strategy,
        'max_bytes': max_bytes,
        'chunk_count': len(chunks),
    }
    if backend:
        chunking['backend'] = backend

    manifest: dict[str, Any] = {
        'schema_version': SCHEMA_VERSION,
        'source': source,
        'chunking': chunking,
        'extracted_text_bytes': cursor,
        'extracted_text_sha256': sha256_bytes(bytes(stream)),
        'chunks': chunks,
    }
    if media_found:
        manifest['media'] = [
            {
                'id': f'media-{number:04d}',
                'chunk_id': found['chunk_id'],
                'kind': found['kind'],
                'syntax': found['syntax'],
                'ref': _media_ref(found.get('ref')),
                'alt': _media_alt(found.get('alt')),
            }
            for number, found in enumerate(media_found, start=1)
        ]
    return manifest


def _md_escape(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", "<br>")


def _media_section(manifest: dict[str, Any], ledger: dict[str, Any]) -> tuple[list[str], list[str]]:
    """Summary bullets and table for media references; both empty when the manifest has none."""
    raw_media = manifest.get("media")
    media = [item for item in raw_media if isinstance(item, dict)] if isinstance(raw_media, list) else []
    if not media:
        return [], []
    raw_dispositions = ledger.get("media")
    dispositions = {
        item.get("id"): item
        for item in (raw_dispositions if isinstance(raw_dispositions, list) else [])
        if isinstance(item, dict) and item.get("disposition") in ("read", "not_read")
    }
    rows = []
    counts = {"read": 0, "not_read": 0, "missing": 0}
    for item in media:
        given = dispositions.get(item.get("id"), {})
        state = str(given.get("disposition", "missing"))
        counts[state] += 1
        detail = given.get("tool") if state == "read" else given.get("reason")
        cells = [
            f"`{_md_escape(str(item.get('id', '')))}`",
            f"`{_md_escape(str(item.get('chunk_id', '')))}`",
            *(_md_escape(str(item.get(key) or "")) for key in ("kind", "syntax", "ref", "alt")),
            state,
            _md_escape(str(detail or "")),
        ]
        rows.append("| " + " | ".join(cells) + " |")
    summary = [
        f"- Media references: {len(media)}",
        f"- Media read: {counts['read']}",
        f"- Media not read: {counts['not_read']}",
        f"- Media without disposition: {counts['missing']}",
    ]
    table = [
        "## Media",
        "",
        "Chunk is the first chunk of the nearest following block, and the coverage above is of extracted text only.",
        "",
        "| Media | Chunk | Kind | Syntax | Reference | Alt | Disposition | Tool or reason |",
        "|---|---|---|---|---|---|---|---|",
        *rows,
        "",
    ]
    return summary, table


def render_traversal_report(manifest: dict[str, Any], ledger: dict[str, Any]) -> str:
    """Render a deterministic grouped human view over canonical machine evidence."""
    raw_entries = ledger.get("entries", [])
    entries = raw_entries if isinstance(raw_entries, list) else []
    by_id = {
        entry.get("chunk_id"): entry
        for entry in entries
        if isinstance(entry, dict) and isinstance(entry.get("chunk_id"), str)
    }
    raw_chunks = manifest.get("chunks", [])
    chunks = raw_chunks if isinstance(raw_chunks, list) else []
    source = manifest.get("source", {}) if isinstance(manifest.get("source"), dict) else {}

    evidence_entries = [entry for entry in entries if isinstance(entry, dict)]
    non_match_count = sum(entry.get("outcome") == "non_match" for entry in evidence_entries)
    assertion_count = sum(
        len(entry.get("assertions", []))
        for entry in evidence_entries
        if isinstance(entry.get("assertions", []), list)
    )
    constraint_count = sum(
        len(entry.get("constraints", []))
        for entry in evidence_entries
        if isinstance(entry.get("constraints", []), list)
    )
    source_label = str(source.get("path") or source.get("uri") or "unknown")
    source_format = str(source.get("format") or "unknown")

    media_summary, media_table = _media_section(manifest, ledger)

    lines = [
        "# Traversal Report",
        "",
        "## Run summary",
        "",
        f"- Source: `{_md_escape(source_label)}`",
        f"- Format: `{_md_escape(source_format)}`",
        f"- Source SHA-256: `{source.get('sha256', '')}`",
        f"- Canonical chunks: {len(chunks)}",
        f"- Evidence verdicts: {len(evidence_entries)}",
        f"- Non-match verdicts: {non_match_count}",
        f"- Assertions: {assertion_count}",
        f"- Constraints: {constraint_count}",
        *media_summary,
        "",
        *media_table,
        "## Chunk index",
        "",
        "| # | Chunk | Location | Kinds | Outcome | Atoms |",
        "|---:|---|---|---|---|---:|",
    ]

    for chunk in chunks:
        if not isinstance(chunk, dict):
            continue
        chunk_id = str(chunk.get("id", ""))
        ordinal = chunk.get("ordinal", "")
        locator = chunk.get("locator") if isinstance(chunk.get("locator"), dict) else {}
        location = compact_locator(chunk)
        kinds = "+".join(block_kinds(locator)) or "unknown"
        entry = by_id.get(chunk_id, {})
        outcome = str(entry.get("outcome", "missing")) if isinstance(entry, dict) else "missing"
        atoms = 0
        if isinstance(entry, dict):
            for key in ("assertions", "constraints"):
                values = entry.get(key, [])
                if isinstance(values, list):
                    atoms += len(values)
        lines.append(
            f"| {ordinal} | `{_md_escape(chunk_id)}` | `{_md_escape(location)}` | "
            f"`{_md_escape(kinds)}` | `{_md_escape(outcome)}` | {atoms} |"
        )

    lines.extend(["", "## Chunk details", ""])
    for chunk in chunks:
        if not isinstance(chunk, dict):
            continue
        chunk_id = str(chunk.get("id", ""))
        ordinal = chunk.get("ordinal")
        ordinal_text = f"{ordinal:02d}" if isinstance(ordinal, int) else str(ordinal or "?")
        locator = chunk.get("locator") if isinstance(chunk.get("locator"), dict) else {}
        location = compact_locator(chunk)
        kinds = "+".join(block_kinds(locator)) or "unknown"
        entry = by_id.get(chunk_id, {})
        outcome = str(entry.get("outcome", "missing")) if isinstance(entry, dict) else "missing"
        start = chunk.get("text_byte_start", "?")
        end = chunk.get("text_byte_end", "?")
        raw_locator = json.dumps(locator, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

        lines.extend([
            f"### {ordinal_text} · `{_md_escape(chunk_id)}` — {_md_escape(location)}",
            "",
            f"- Outcome: `{_md_escape(outcome)}`",
            f"- Byte span: `{start}..{end}`",
            f"- Kinds: `{_md_escape(kinds)}`",
            f"- Locator: `{_md_escape(location)}`",
            "",
        ])

        if outcome == "evidence" and isinstance(entry, dict):
            for plural, title in (("assertions", "Assertions"), ("constraints", "Constraints")):
                values = entry.get(plural, [])
                atoms = values if isinstance(values, list) else []
                if not atoms:
                    continue
                lines.extend([f"**{title}**", ""])
                for atom in atoms:
                    if not isinstance(atom, dict):
                        continue
                    atom_text = _md_escape(str(atom.get("text", "")))
                    atom_start = atom.get("chunk_byte_start", "?")
                    atom_end = atom.get("chunk_byte_end", "?")
                    raw_atom_id = atom.get("atom_id")
                    if isinstance(raw_atom_id, str) and raw_atom_id:
                        lines.append(
                            f"- `{_md_escape(raw_atom_id)}` · bytes `{atom_start}..{atom_end}` — {atom_text}"
                        )
                    else:
                        lines.append(f"- bytes `{atom_start}..{atom_end}` — {atom_text}")
                lines.append("")
        elif outcome == "non_match" and isinstance(entry, dict):
            lines.extend(["**Non-match reason**", "", _md_escape(str(entry.get("reason", ""))), ""])
        else:
            lines.extend(["**Missing verdict**", ""])

        lines.extend([
            "<details><summary>Full locator</summary>",
            "",
            f"`{_md_escape(raw_locator)}`",
            "",
            "</details>",
            "",
        ])

    return "\n".join(lines).rstrip() + "\n"


def write_manifest(manifest: dict[str, Any], out: Path) -> None:
    write_text_atomic(out, json.dumps(manifest, indent=2, ensure_ascii=False) + '\n',
                      inputs=[Path(manifest['source']['path'])])
