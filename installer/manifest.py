from __future__ import annotations

from dataclasses import dataclass
import json
import re
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


def _skill_root_error(data: dict[str, Any], root: Path) -> str | None:
    """Return the first problem with ``skill.root``, or None when it is usable."""
    skill = data.get('skill') if isinstance(data, dict) else None
    if not isinstance(data, dict) or not isinstance(skill if skill is not None else {}, dict):
        return 'MANIFEST.json must be an object and skill must be an object'
    raw = (skill or {}).get('root', '.')
    if not isinstance(raw, str):
        return 'skill.root must be a string'
    if not raw or '\\' in raw or raw.startswith('/') or re.match(r'[A-Za-z]:', raw):
        return 'skill.root must be a relative path'
    if '..' in raw.split('/'):
        return 'skill.root must not contain ..'
    try:
        folder = (root / raw).resolve()
        folder.relative_to(root)
    except (OSError, ValueError):
        return 'skill.root is outside the package root'
    except RuntimeError:
        # Python before 3.13 raises RuntimeError for a symlink loop.
        return 'Missing canonical SKILL.md at package root'
    if not (folder / 'SKILL.md').is_file():
        return 'Missing canonical SKILL.md at package root'
    return None


def skill_root(manifest_data: dict[str, Any], package_root: Path) -> Path:
    """Resolve the folder holding SKILL.md and the payload; raise ValueError if the field is bad."""
    root = Path(package_root).resolve()
    error = _skill_root_error(manifest_data, root)
    if error:
        raise ValueError(error)
    return (root / (manifest_data.get('skill') or {}).get('root', '.')).resolve()


def validate_manifest(manifest: Manifest, package_root: Path) -> list[str]:
    root = Path(package_root).resolve()
    data = manifest.data
    errors: list[str] = []

    skill = data.get('skill') or {}
    entry = skill.get('entrypoint')
    name = skill.get('name')
    if entry != 'SKILL.md':
        errors.append('Canonical entrypoint must be SKILL.md')

    root_error = _skill_root_error(data, root)
    if root_error:
        errors.append(root_error)
        skill_dir = None
    else:
        skill_dir = skill_root(data, root)
        fm_name = _frontmatter_name(skill_dir / 'SKILL.md')
        if fm_name != name:
            errors.append(f'Manifest skill name {name!r} does not match SKILL.md name {fm_name!r}')

    payload = data.get('payload')
    if not isinstance(payload, list) or not payload:
        errors.append('Payload must be a non-empty list')
        payload = []

    base = skill_dir or root
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
        try:
            resolved = (base / rel).resolve()
        except RuntimeError:
            # Python before 3.13 raises RuntimeError for a symlink loop.
            if skill_dir:
                errors.append(f'Payload entry does not exist: {raw}')
            continue
        try:
            resolved.relative_to(base)
        except ValueError:
            errors.append(f'Payload path outside package root: {raw}')
            continue
        if skill_dir and not resolved.exists():
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
