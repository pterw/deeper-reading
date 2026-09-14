from __future__ import annotations

from pathlib import Path
import shutil
import subprocess

from .base import SKILL_NAME, VerificationResult, require_project
from .discovery import discovery_state


class CopilotAdapter:
    name = 'copilot'

    def detect(self) -> bool:
        return shutil.which('copilot') is not None

    def resolve_skill_root(self, scope: str, project_dir: Path | None) -> Path:
        if scope == 'user':
            return Path.home() / '.copilot' / 'skills' / SKILL_NAME
        project = require_project(scope, project_dir)
        return project / '.github' / 'skills' / SKILL_NAME

    def discovery_verify(self, skill_name: str) -> VerificationResult:
        if not self.detect():
            return VerificationResult('not-available', ('copilot CLI not found',))
        try:
            proc = subprocess.run(['copilot', 'skill', 'list', '--json'], capture_output=True, text=True, check=False, timeout=30)
        except (OSError, subprocess.TimeoutExpired) as exc:
            return VerificationResult('failed', (f'{type(exc).__name__}: {exc}',))
        evidence = (f'exit={proc.returncode}', (proc.stdout or '').strip(), (proc.stderr or '').strip())
        if proc.returncode != 0:
            return VerificationResult('failed', evidence)
        state = discovery_state('copilot', proc.stdout or '', skill_name)
        if state == 'failed':
            evidence += ('unrecognized copilot skill list --json output',)
        return VerificationResult(state, evidence)
