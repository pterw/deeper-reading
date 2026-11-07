from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Protocol

SKILL_NAME = 'deeper-reading'
LAUNCHABLE_EXTENSIONS = ('.com', '.exe', '.bat', '.cmd')
TRAILING_DOTS = re.compile(r'(?<=[^./\\:])\.+(?=[/\\]|$)')
CURRENT_DIRECTORY = re.compile(r'(?:\.(?:/+\.?)*)?')
CURRENT_DIRECTORY_WIN32 = re.compile(r'(?:\.(?:[/\\]+\.?)*)?')
UNSAFE_SHIM_CHARACTERS = frozenset('"%&|<>^!(),;=\r\n')


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


class UnsafeHostPath(Exception):
    pass


def unsafe_shim_path(path: str) -> str | None:
    return next((char for char in path if char in UNSAFE_SHIM_CHARACTERS), None)


def host_path_refusal(path: str) -> str | None:
    if sys.platform == 'win32' and path.lower().endswith(('.cmd', '.bat')):
        return unsafe_shim_path(path)
    return None


def _normalise(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] == '"':
        value = value[1:-1]
    return value


def _candidate_names(name: str) -> list[str]:
    if sys.platform != 'win32':
        return [name]
    pathext = os.environ.get('PATHEXT') or '.COM;.EXE;.BAT;.CMD'
    extensions = [_normalise(ext).lower() for ext in pathext.split(';')]
    return [name + ext for ext in extensions if ext in LAUNCHABLE_EXTENSIONS]


def resolve_host_command(name: str) -> str | None:
    # Rule R29, identical in installer/node/adapters.js (shared table:
    # tests/fixtures/host-resolution-cases.json): only PATH entries are searched, never the
    # current directory; entries and PATHEXT members are trimmed and unquoted; empty and
    # current-directory entries (".", "./", ".\.") are skipped; Win32 drops the trailing dots
    # of every path segment.
    candidates = _candidate_names(name)
    for entry in os.environ.get('PATH', '').split(os.pathsep):
        directory = _normalise(entry)
        if sys.platform == 'win32':
            directory = TRAILING_DOTS.sub('', directory)
        if (CURRENT_DIRECTORY_WIN32 if sys.platform == 'win32' else CURRENT_DIRECTORY).fullmatch(directory):
            continue
        for candidate in candidates:
            path = os.path.join(os.path.abspath(directory), candidate)
            if os.path.isfile(path) and (sys.platform == 'win32' or os.access(path, os.X_OK)):
                return path
    return None


def run_host_command(name: str, args: list[str]) -> subprocess.CompletedProcess:
    path = resolve_host_command(name)
    if path is None:
        raise FileNotFoundError(f'{name} not found on PATH')
    char = host_path_refusal(path)
    if char is not None:
        raise UnsafeHostPath(f'unsafe host command path: {path} (character {char})')
    return subprocess.run([path, *args], capture_output=True, text=True, check=False, timeout=30)
