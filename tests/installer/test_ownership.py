import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

# Replays tests/fixtures/installer-ownership-cases.json against the Python installer's
# real command line (tests/node/ownership.test.js replays the same table against Node).
ROOT = Path(__file__).parents[2]
INSTALL = ROOT / 'installer' / 'install.py'
CASES = json.loads((ROOT / 'tests' / 'fixtures' / 'installer-ownership-cases.json').read_text(encoding='utf-8'))['cases']
STEP_KEYS = {
    'mkdir': {'do', 'path'},
    'link': {'do', 'at', 'to'},
    'rmdir': {'do', 'path'},
    'file': {'do', 'path'},
    'receipt': {'do', 'path', 'delete', 'set'},
    'run': {'do', 'cwd', 'home', 'args', 'expect', 'unchanged', 'survives'},
}
EXPECT_KEYS = {'exit', 'state', 'code', 'passed', 'message_has', 'message_lacks'}


def make_link(at, to):
    at.parent.mkdir(parents=True, exist_ok=True)
    if sys.platform == 'win32':
        import _winapi

        _winapi.CreateJunction(str(to), str(at))
    else:
        os.symlink(to, at, target_is_directory=True)


def link_text(path):
    """The target text of a link, or None when path is not a link (junctions included)."""
    try:
        return os.readlink(path)
    except OSError:
        return None


def snapshot(root):
    """Paths and bytes under root; a link is recorded as its target text and not followed."""
    seen = {}
    pending = [root]
    while pending:
        folder = pending.pop()
        for entry in os.scandir(folder):
            text = link_text(entry.path)
            if text is not None:
                seen[entry.path] = ('link', text)
            elif entry.is_dir(follow_symlinks=False):
                seen[entry.path] = ('dir', None)
                pending.append(entry.path)
            else:
                seen[entry.path] = ('file', Path(entry.path).read_bytes())
    return seen


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
    unknown = set(step['expect']) - EXPECT_KEYS
    assert not unknown, f'unknown expect keys: {unknown}'
    before = snapshot(work)
    proc = run_installer(step, work)
    expect = step['expect']
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
    elif step['do'] == 'link':
        make_link(Path(fill(step['at'], work)), Path(fill(step['to'], work)))
    elif step['do'] == 'rmdir':
        Path(fill(step['path'], work)).rmdir()
    elif step['do'] == 'file':
        path = Path(fill(step['path'], work))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('unmanaged\n', encoding='utf-8')
    elif step['do'] == 'receipt':
        edit_receipt(step, work)
    else:
        check_run(step, work)


@pytest.mark.parametrize('case', CASES, ids=[case['id'] for case in CASES])
def test_ownership_case(case, tmp_path):
    work = tmp_path / 'work'
    work.mkdir()
    for step in case['steps']:
        play(step, work)
