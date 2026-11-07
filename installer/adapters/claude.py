from __future__ import annotations

from pathlib import Path

from .base import SKILL_NAME, VerificationResult, require_project, resolve_host_command


class ClaudeAdapter:
    name = 'claude'

    def detect(self) -> bool:
        return resolve_host_command('claude') is not None

    def resolve_skill_root(self, scope: str, project_dir: Path | None) -> Path:
        if scope == 'user':
            return Path.home() / '.claude' / 'skills' / SKILL_NAME
        project = require_project(scope, project_dir)
        return project / '.claude' / 'skills' / SKILL_NAME

    def discovery_verify(self, skill_name: str) -> VerificationResult:
        return VerificationResult('not-available', ('Claude Code direct skill discovery has no stable noninteractive list contract assumed by this installer.',))
