from __future__ import annotations

from pathlib import Path

from .base import SKILL_NAME, VerificationResult, require_project


class GenericAgentsAdapter:
    name = 'generic-agents'

    def detect(self) -> bool:
        return True

    def resolve_skill_root(self, scope: str, project_dir: Path | None) -> Path:
        if scope == 'user':
            return Path.home() / '.agents' / 'skills' / SKILL_NAME
        project = require_project(scope, project_dir)
        return project / '.agents' / 'skills' / SKILL_NAME

    def discovery_verify(self, skill_name: str) -> VerificationResult:
        return VerificationResult('not-available', ('generic Agent Skills has no universal discovery CLI',))
