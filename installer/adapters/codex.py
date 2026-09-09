from __future__ import annotations

from pathlib import Path
import shutil

from .base import SKILL_NAME, VerificationResult, require_project


class CodexAdapter:
    name = 'codex'

    def detect(self) -> bool:
        return shutil.which('codex') is not None

    def resolve_skill_root(self, scope: str, project_dir: Path | None) -> Path:
        if scope == 'user':
            return Path.home() / '.agents' / 'skills' / SKILL_NAME
        project = require_project(scope, project_dir)
        return project / '.agents' / 'skills' / SKILL_NAME

    def discovery_verify(self, skill_name: str) -> VerificationResult:
        return VerificationResult('not-available', ('Codex adapter uses the cross-runtime Agent Skills path; no stable discovery CLI contract is assumed.',))
