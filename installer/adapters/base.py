from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

SKILL_NAME = 'deeper-reading'


@dataclass(frozen=True)
class VerificationResult:
    state: str
    evidence: tuple[str, ...] = ()


class RuntimeAdapter(Protocol):
    name: str

    def detect(self) -> bool: ...
    def resolve_skill_root(self, scope: str, project_dir: Path | None) -> Path: ...
    def discovery_verify(self, skill_name: str) -> VerificationResult: ...


def require_project(scope: str, project_dir: Path | None) -> Path:
    if scope == 'user':
        raise ValueError('user scope does not require a project directory')
    if scope != 'project':
        raise ValueError(f'unsupported scope: {scope}')
    if project_dir is None:
        raise ValueError('project scope requires --project-dir')
    return Path(project_dir).resolve()
