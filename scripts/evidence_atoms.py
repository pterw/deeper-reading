#!/usr/bin/env python3
"""Bind extractive evidence atoms to exact canonical chunk bytes."""

from __future__ import annotations

import hashlib
import re
from typing import Any


class EvidenceBindingError(ValueError):
    """Raised when a draft evidence atom cannot be bound to source bytes."""


class AmbiguousEvidenceError(EvidenceBindingError):
    """Raised when text occurs more than once and no exact span was supplied."""


def find_byte_occurrences(content: bytes, needle: bytes) -> list[int]:
    """Return every byte offset at which *needle* begins, including overlaps."""
    starts: list[int] = []
    cursor = 0
    while True:
        found = content.find(needle, cursor)
        if found < 0:
            return starts
        starts.append(found)
        cursor = found + 1


def atom_id(chunk_id: str, kind: str, start: int, end: int, text: str) -> str:
    """Return the stable identifier for one byte-verified evidence atom."""
    text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]
    return f"{chunk_id}:{kind}:{start}:{end}:{text_hash}"


def _candidate_lines(content: str, text: str, limit: int = 3) -> list[str]:
    """Return exact source lines sharing distinctive tokens with a missed quote."""
    tokens = [token for token in re.split(r"[^\w]+", text, flags=re.UNICODE) if len(token) > 3]
    tokens = sorted(dict.fromkeys(tokens), key=len, reverse=True)[:3]
    hits: list[str] = []
    for line in content.splitlines():
        if tokens and any(token in line for token in tokens):
            hits.append(line)
        if len(hits) >= limit:
            break
    return hits


def bind_atom(
    chunk_id: str,
    kind: str,
    content: str,
    draft: dict[str, Any],
) -> dict[str, Any]:
    """Bind a draft atom to one exact UTF-8 byte span in a canonical chunk."""
    if not isinstance(draft, dict):
        raise EvidenceBindingError("evidence atom must be an object")
    text = draft.get("text")
    if not isinstance(text, str) or not text:
        raise EvidenceBindingError("evidence atom text must be non-empty")

    has_start = "chunk_byte_start" in draft
    has_end = "chunk_byte_end" in draft
    if has_start != has_end:
        raise EvidenceBindingError("explicit evidence span requires both start and end")

    needle = text.encode("utf-8")
    content_bytes = content.encode("utf-8")

    if has_start:
        start = draft.get("chunk_byte_start")
        end = draft.get("chunk_byte_end")
        if type(start) is not int or type(end) is not int:
            raise EvidenceBindingError("explicit evidence span start and end must be integers")
        if start < 0 or end <= start or end > len(content_bytes):
            raise EvidenceBindingError("explicit evidence span is outside chunk bytes")
        if content_bytes[start:end] != needle:
            raise EvidenceBindingError("explicit evidence span does not match exact evidence text bytes")
    else:
        starts = find_byte_occurrences(content_bytes, needle)
        if not starts:
            candidates = _candidate_lines(content, text)
            detail = ""
            if candidates:
                detail = "; source candidates: " + " | ".join(repr(line) for line in candidates)
            raise EvidenceBindingError(
                f"evidence text does not occur in chunk {chunk_id}{detail}"
            )
        if len(starts) > 1:
            raise AmbiguousEvidenceError(
                f"evidence text occurs multiple times in chunk {chunk_id}; "
                f"byte starts {starts}; provide explicit byte span"
            )
        start = starts[0]
        end = start + len(needle)

    return {
        "atom_id": atom_id(chunk_id, kind, start, end, text),
        "text": text,
        "chunk_byte_start": start,
        "chunk_byte_end": end,
    }
