from __future__ import annotations

from pathlib import Path
import shutil
import subprocess

from .base import SKILL_NAME, VerificationResult, require_project


class GeminiAdapter:
    name = 'gemini'

    def detect(self) -> bool:
        return shutil.which('gemini') is not None

    def resolve_skill_root(self, scope: str, project_dir: Path | None) -> Path:
        if scope == 'user':
            return Path.home() / '.gemini' / 'skills' / SKILL_NAME
        project = require_project(scope, project_dir)
        return project / '.gemini' / 'skills' / SKILL_NAME

    def discovery_verify(self, skill_name: str) -> VerificationResult:
        if not self.detect():
            return VerificationResult('not-available', ('gemini CLI not found',))
        proc = subprocess.run(['gemini', 'skills', 'list'], capture_output=True, text=True, check=False, timeout=30)
        evidence = (f'exit={proc.returncode}', proc.stdout.strip(), proc.stderr.strip())
        if proc.returncode != 0:
            return VerificationResult('failed', evidence)
        return VerificationResult('verified' if skill_name in proc.stdout else 'missing', evidence)
