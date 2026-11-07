import json
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

import pytest
from installer.adapters import detect_target
from installer.adapters.base import host_path_refusal, resolve_host_command, unsafe_shim_path
from installer.adapters.claude import ClaudeAdapter
from installer.adapters.codex import CodexAdapter
from installer.adapters.copilot import CopilotAdapter
from installer.adapters.gemini import GeminiAdapter

RESOLVE = 'installer.adapters.base.resolve_host_command'
WIN = sys.platform == 'win32'
VECTORS = {'copilot': ['skill', 'list', '--json'], 'gemini': ['skills', 'list']}
ADAPTERS = {'claude': ClaudeAdapter, 'codex': CodexAdapter, 'copilot': CopilotAdapter, 'gemini': GeminiAdapter}
CASES = json.loads((Path(__file__).parents[1] / 'fixtures/discovery-output.json').read_text(encoding='utf-8'))
# One table for both runtimes (tests/node/discovery.test.js reads the same file).
RESOLUTION = json.loads((Path(__file__).parents[1] / 'fixtures/host-resolution-cases.json').read_text(encoding='utf-8'))


def write_shim(directory, name, body_win, body_sh):
    directory.mkdir(parents=True, exist_ok=True)
    if WIN:
        shim = directory / f'{name}.cmd'
        shim.write_bytes(('@echo off\r\n' + body_win + '\r\n').encode('ascii'))
    else:
        shim = directory / name
        shim.write_bytes(('#!/bin/sh\n' + body_sh + '\n').encode('ascii'))
        shim.chmod(0o755)
    return shim


def use_clean_env(monkeypatch, tmp_path, path_dirs):
    monkeypatch.setenv('HOME', str(tmp_path / 'home'))
    monkeypatch.setenv('USERPROFILE', str(tmp_path / 'home'))
    monkeypatch.setenv('PATH', os.pathsep.join(str(d) for d in path_dirs))
    monkeypatch.setenv('PATHEXT', '.COM;.EXE;.BAT;.CMD')


@pytest.mark.parametrize('case', CASES)
def test_discovery_requires_exact_enabled_record(case):
    adapter = CopilotAdapter() if case['host'] == 'copilot' else GeminiAdapter()
    result = subprocess.CompletedProcess([], 0, case['output'], '')
    with patch.object(adapter, 'detect', return_value=True), patch(RESOLVE, return_value=f"hostdir/{case['host']}.exe"), patch('subprocess.run', return_value=result) as run:
        assert adapter.discovery_verify('deeper-reading').state == case['state']
        assert run.call_args.args[0][1:] == VECTORS[case['host']]

@pytest.mark.parametrize('adapter_type', [CopilotAdapter, GeminiAdapter])
@pytest.mark.parametrize('error', [FileNotFoundError('missing executable'), subprocess.TimeoutExpired('host', 30)])
def test_discovery_process_failure_is_diagnostic(adapter_type, error):
    adapter = adapter_type()
    with patch.object(adapter, 'detect', return_value=True), patch(RESOLVE, return_value=f'hostdir/{adapter.name}.exe'), patch('subprocess.run', side_effect=error):
        result = adapter.discovery_verify('deeper-reading')
    assert result.state == 'failed'
    assert result.evidence


@pytest.mark.parametrize('host', ['copilot', 'gemini'])
def test_discovery_launches_real_host_shim(host, tmp_path, monkeypatch):
    shim_dir = tmp_path / 'npm bin'
    shim_dir.mkdir()
    verified = next(c['output'] for c in CASES if c['host'] == host and c['state'] == 'verified')
    (shim_dir / 'out.txt').write_bytes(verified.encode('ascii'))
    write_shim(shim_dir, host,
               'echo %* > "%~dp0argv.txt"\r\ntype "%~dp0out.txt"',
               'echo "$@" > "$(dirname "$0")/argv.txt"\ncat "$(dirname "$0")/out.txt"')
    use_clean_env(monkeypatch, tmp_path, [shim_dir])
    result = ADAPTERS[host]().discovery_verify('deeper-reading')
    assert result.state == 'verified', result.evidence
    assert (shim_dir / 'argv.txt').read_text(encoding='ascii').split() == VECTORS[host]


@pytest.mark.parametrize('name', sorted(ADAPTERS))
def test_resolution_ignores_current_directory(name, tmp_path, monkeypatch):
    cwd = tmp_path / 'cwd'
    empty = tmp_path / 'empty'
    empty.mkdir()
    write_shim(cwd, name, 'exit /b 0', 'exit 0')
    use_clean_env(monkeypatch, tmp_path, [empty])
    monkeypatch.chdir(cwd)
    assert ADAPTERS[name]().detect() is False
    assert detect_target() == 'generic-agents'


@pytest.mark.parametrize('case', RESOLUTION['cases'], ids=lambda case: case['id'])
def test_host_resolution_table(case, tmp_path, monkeypatch):
    root = tmp_path / 'root'
    (root / 'cwd').mkdir(parents=True)
    for directory in case['dirs']:
        (root / directory).mkdir(parents=True)
    for file in case['files']:
        (root / file).parent.mkdir(parents=True, exist_ok=True)
        (root / file).write_bytes(b'')
    monkeypatch.setenv('HOME', str(tmp_path / 'home'))
    monkeypatch.setenv('USERPROFILE', str(tmp_path / 'home'))
    monkeypatch.setenv('PATH', os.pathsep.join(entry.replace('{root}', root.as_posix()) for entry in case['path']))
    monkeypatch.setenv('PATHEXT', case['pathext'])
    monkeypatch.chdir(root / 'cwd')
    with monkeypatch.context() as patched:
        patched.setattr(sys, 'platform', 'win32')
        resolved = resolve_host_command(case['name'])
        refusal = host_path_refusal(resolved) if resolved else None
    relative = os.path.relpath(resolved, root).replace('\\', '/') if resolved else None
    assert relative == case['resolved']
    assert (refusal is not None) == case['refusal']


@pytest.mark.parametrize('char', RESOLUTION['refusal_characters'])
def test_unsafe_shim_path_refused(char):
    assert unsafe_shim_path('C:\\npm' + char + 'bin\\copilot.cmd') == char


def test_safe_shim_path_accepted():
    assert unsafe_shim_path('C:\\Program Files\\npm-bin_1.0\\copilot.cmd') is None


@pytest.mark.parametrize('char', ['%', '&'])
def test_unsafe_shim_directory_starts_no_process(char, tmp_path, monkeypatch):
    shim_dir = tmp_path / f'npm{char}bin'
    if not WIN:
        assert unsafe_shim_path(str(shim_dir / 'copilot.cmd')) == char
        return
    write_shim(shim_dir, 'copilot', 'echo ran > "%~dp0marker.txt"', '')
    use_clean_env(monkeypatch, tmp_path, [shim_dir])
    result = CopilotAdapter().discovery_verify('deeper-reading')
    assert result.state == 'failed'
    assert result.evidence[0].startswith('unsafe host command path: ')
    assert str(shim_dir) in result.evidence[0]
    assert result.evidence[0].endswith(f'(character {char})')
    assert not (shim_dir / 'marker.txt').exists()
