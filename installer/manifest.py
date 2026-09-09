from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Manifest:
    data: dict[str, Any]
    source: Path

    def __getitem__(self, key: str) -> Any:
        return self.data[key]


def load_manifest(path: Path) -> Manifest:
    path = Path(path)
    return Manifest(json.loads(path.read_text(encoding='utf-8')), path)


def _frontmatter_name(skill_path: Path) -> str | None:
    text = skill_path.read_text(encoding='utf-8')
    if not text.startswith('---\n'):
        return None
    end = text.find('\n---\n', 4)
    if end == -1:
        return None
    for line in text[4:end].splitlines():
        if line.startswith('name:'):
            return line.split(':', 1)[1].strip().strip('"\'')
    return None


def validate_manifest(manifest: Manifest, package_root: Path) -> list[str]:
    root = Path(package_root).resolve()
    data = manifest.data
    errors: list[str] = []

    skill = data.get('skill') or {}
    entry = skill.get('entrypoint')
    name = skill.get('name')
    if entry != 'SKILL.md':
        errors.append('Canonical entrypoint must be SKILL.md')

    skill_path = root / 'SKILL.md'
    if not skill_path.is_file():
        errors.append('Missing canonical SKILL.md at package root')
    else:
        fm_name = _frontmatter_name(skill_path)
        if fm_name != name:
            errors.append(f'Manifest skill name {name!r} does not match SKILL.md name {fm_name!r}')

    payload = data.get('payload')
    if not isinstance(payload, list) or not payload:
        errors.append('Payload must be a non-empty list')
        payload = []

    seen: set[str] = set()
    for raw in payload:
        if not isinstance(raw, str) or not raw:
            errors.append('Payload entries must be non-empty strings')
            continue
        if raw in seen:
            errors.append(f'Duplicate payload entry: {raw}')
            continue
        seen.add(raw)
        rel = Path(raw)
        if rel.is_absolute() or '..' in rel.parts:
            errors.append(f'Payload path traversal/outside package root: {raw}')
            continue
        resolved = (root / rel).resolve()
        try:
            resolved.relative_to(root)
        except ValueError:
            errors.append(f'Payload path outside package root: {raw}')
            continue
        if not resolved.exists():
            errors.append(f'Payload entry does not exist: {raw}')

    prerequisites = data.get('prerequisites', {})
    if not isinstance(prerequisites, dict):
        errors.append('Prerequisites must be an object')
    elif 'superpowers' in prerequisites:
        errors.append('Standalone manifest must not require an external process framework')

    profiles = data.get('document_profiles')
    if not isinstance(profiles, dict) or set(profiles) != {'standalone', 'oai-native'}:
        errors.append('Document profiles must be exactly standalone and oai-native')

    if 'skills' not in payload:
        errors.append('Standalone runtime payload must include package-owned skills')

    return errors
