#!/usr/bin/env python3
"""Deterministic human views over canonical chunk-manifest entries."""

from __future__ import annotations

import json
from typing import Any


def heading_path(locator: dict[str, Any]) -> str:
    values = locator.get("heading_path") or []
    if not isinstance(values, list):
        return "(none)"
    return " > ".join(str(value) for value in values) if values else "(none)"


def block_kinds(locator: dict[str, Any]) -> list[str]:
    kinds: list[str] = []
    blocks = locator.get("blocks") or []
    if isinstance(blocks, list):
        for block in blocks:
            if isinstance(block, dict):
                kind = block.get("kind")
                if isinstance(kind, str) and kind and kind not in kinds:
                    kinds.append(kind)
    for key in ("kind", "atomic_kind"):
        kind = locator.get(key)
        if isinstance(kind, str) and kind and kind not in kinds:
            kinds.append(kind)
    return kinds


def _page_label(pages: Any) -> str | None:
    if not isinstance(pages, list) or not pages:
        return None
    values = [value for value in pages if isinstance(value, int)]
    if not values:
        return None
    if len(values) == 1:
        return f"page {values[0]}"
    if values == list(range(values[0], values[-1] + 1)):
        return f"pages {values[0]}-{values[-1]}"
    return "pages " + ",".join(str(value) for value in values)


def compact_locator(chunk: dict[str, Any]) -> str:
    locator = chunk.get("locator")
    if not isinstance(locator, dict):
        return "{}"
    pieces: list[str] = []
    heading = heading_path(locator)
    if heading != "(none)":
        pieces.append(heading)
    page = _page_label(locator.get("pages"))
    if page:
        pieces.append(page)
    part = locator.get("part")
    if isinstance(part, str) and part:
        pieces.append(part)
    if pieces:
        return " · ".join(pieces)
    return json.dumps(locator, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def summary_line(chunk: dict[str, Any]) -> str:
    ordinal = chunk.get("ordinal")
    chunk_id = str(chunk.get("id", ""))
    locator = chunk.get("locator") if isinstance(chunk.get("locator"), dict) else {}
    kinds = block_kinds(locator)
    kind_text = "+".join(kinds) if kinds else "unknown"
    content = chunk.get("content")
    size = len(content.encode("utf-8")) if isinstance(content, str) else 0
    ordinal_text = f"{ordinal:02d}" if isinstance(ordinal, int) else "??"
    return f"{ordinal_text}  {chunk_id}  [{kind_text}]  {size}B  {compact_locator(chunk)}"


def detail_block(chunk: dict[str, Any]) -> str:
    ordinal = chunk.get("ordinal")
    chunk_id = str(chunk.get("id", ""))
    content = chunk.get("content") if isinstance(chunk.get("content"), str) else ""
    locator = chunk.get("locator") if isinstance(chunk.get("locator"), dict) else {}
    kinds = "+".join(block_kinds(locator)) or "unknown"
    start = chunk.get("text_byte_start", "?")
    end = chunk.get("text_byte_end", "?")
    ordinal_text = f"{ordinal:02d}" if isinstance(ordinal, int) else "??"
    return "\n".join([
        f"CHUNK {ordinal_text}  {chunk_id}",
        f"Location: {compact_locator(chunk)}",
        f"Kinds: [{kinds}]",
        f"Bytes: {start}..{end}",
        "---",
        content,
    ])
