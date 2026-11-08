import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

# Replays tests/fixtures/installer-recovery-cases.json against the Python installer's
# real command line (tests/node/recovery.test.js replays the same table against Node).
ROOT = Path(__file__).parents[2]
INSTALL = ROOT / 'installer' / 'install.py'
CASES = json.loads((ROOT / 'tests' / 'fixtures' / 'installer-recovery-cases.json').read_text(encoding='utf-8'))['cases']
STEP_KEYS = {
    'mkdir': {'do', 'path'},
    'file': {'do', 'path'},
    'receipt': {'do', 'path', 'delete', 'set'},
    'run': {'do', 'cwd', 'home', 'args', 'expect', 'unchanged', 'survives'},
}
EXPECT_KEYS = {'exit', 'state', 'code', 'passed', 'message_has', 'message_lacks'}


def snapshot(root):
    """Paths and bytes under root."""
    return {
        str(path): None if path.is_dir() else path.read_bytes()
        for path in Path(root).rglob('*')
    }


def fill(text, work):
    return text.replace('{work}', str(work)).replace('{home}', str(work / 'home')).replace('{project}', str(work / 'project'))


def run_installer(step, work):
    home = Path(fill(step.get('home', '{home}'), work))
    home.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, 'HOME': str(home), 'USERPROFILE': str(home), 'PYTHONUTF8': '1'}
    args = [fill(arg, work) for arg in step['args']] + ['--json']
    return subprocess.run(
        [sys.executable, str(INSTALL), *args], cwd=fill(step['cwd'], work), env=env,
        capture_output=True, text=True, timeout=120,
    )


def check_run(step, work):
    expect = step['expect']
    unknown = set(expect) - EXPECT_KEYS
    assert not unknown, f'unknown expect keys: {unknown}'
    before = snapshot(work)
    proc = run_installer(step, work)
    assert proc.returncode == expect['exit'], proc.stdout + proc.stderr
    payload = json.loads(proc.stdout)
    if expect['state'] is None:
        assert 'state' not in payload, payload
    else:
        assert payload.get('state') == expect['state'], payload
    assert payload.get('code') == expect.get('code'), payload
    if 'passed' in expect:
        assert payload.get('passed') is expect['passed'], payload
    for text in expect.get('message_has', []):
        assert text in payload['error'], payload
    for text in expect.get('message_lacks', []):
        assert text not in payload['error'], payload
    if step['unchanged']:
        assert snapshot(work) == before
    for path in step.get('survives', []):
        assert Path(fill(path, work)).exists(), path


def edit_receipt(step, work):
    path = Path(fill(step['path'], work)) / '.install-receipt.json'
    receipt = json.loads(path.read_text(encoding='utf-8'))
    for key in step.get('delete', []):
        del receipt[key]
    receipt.update(step.get('set', {}))
    path.write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')


def play(step, work):
    unknown = set(step) - STEP_KEYS.get(step['do'], set())
    assert step['do'] in STEP_KEYS and not unknown, f'unknown step or keys: {step}'
    if step['do'] == 'mkdir':
        Path(fill(step['path'], work)).mkdir(parents=True, exist_ok=True)
    elif step['do'] == 'file':
        path = Path(fill(step['path'], work))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('unmanaged\n', encoding='utf-8')
    elif step['do'] == 'receipt':
        edit_receipt(step, work)
    else:
        check_run(step, work)


@pytest.mark.parametrize('case', CASES, ids=[case['id'] for case in CASES])
def test_recovery_case(case, tmp_path):
    work = tmp_path / 'work'
    (work / 'home').mkdir(parents=True)
    (work / 'project').mkdir()
    for step in case['steps']:
        play(step, work)
