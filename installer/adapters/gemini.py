from __future__ import annotations

from pathlib import Path
import subprocess

from .base import SKILL_NAME, UnsafeHostPath, VerificationResult, require_project, resolve_host_command, run_host_command
from .discovery import discovery_state


class GeminiAdapter:
    name = 'gemini'

    def detect(self) -> bool:
        return resolve_host_command('gemini') is not None

    def resolve_skill_root(self, scope: str, project_dir: Path | None) -> Path:
        if scope == 'user':
            return Path.home() / '.gemini' / 'skills' / SKILL_NAME
        project = require_project(scope, project_dir)
        return project / '.gemini' / 'skills' / SKILL_NAME

    def discovery_verify(self, skill_name: str) -> VerificationResult:
        if not self.detect():
            return VerificationResult('not-available', ('gemini CLI not found',))
        try:
            proc = run_host_command('gemini', ['skills', 'list'])
        except UnsafeHostPath as exc:
            return VerificationResult('failed', (str(exc),))
        except (OSError, subprocess.TimeoutExpired) as exc:
            return VerificationResult('failed', (f'{type(exc).__name__}: {exc}',))
        evidence = (f'exit={proc.returncode}', (proc.stdout or '').strip(), (proc.stderr or '').strip())
        if proc.returncode != 0:
            return VerificationResult('failed', evidence)
        state = discovery_state('gemini', proc.stdout or '', skill_name)
        if state == 'failed':
            evidence += ('unrecognized gemini skills list output',)
        return VerificationResult(state, evidence)
