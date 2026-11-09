import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from installer.core import InstallError, install_skill, uninstall_skill
from installer.manifest import load_manifest
from installer.prerequisites import PrerequisiteStatus

# Two targets can share one skills folder (a linked ~/.claude/skills). Both can pass the
# command-line ownership check before either has written a receipt; the check must repeat
# inside the target lock, where the second one sees the first one's receipt.
ROOT = Path(__file__).parents[2]
INSTALL = ROOT / 'installer' / 'install.py'
READY = PrerequisiteStatus('ready', ('test-ready',))

# Runs the real command line for codex. `hook` names the install.py function that runs between
# the command-line check and the lock; the wrapper first plants a claude install, as a concurrent
# winner would, and records the winner's files.
DRIVER = '''
import hashlib, json, os, subprocess, sys
from pathlib import Path
root, install_py, mark, shared, hook, command, scope, project = sys.argv[1:9]
extra = ["--project-dir", project] if project else []
sys.path.insert(0, root)
from installer import install

def snap():
    files = {}
    for folder, _, names in os.walk(shared):
        for name in names:
            path = Path(folder) / name
            files[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
    return files

real = getattr(install, hook)

def wrapper(*args, **kwargs):
    won = subprocess.run([sys.executable, install_py, "install", "--target", "claude", "--scope", scope, *extra, "--json"],
                         capture_output=True, text=True)
    Path(mark).write_text(json.dumps({"exit": won.returncode, "files": snap()}), encoding="utf-8")
    return real(*args, **kwargs)

setattr(install, hook, wrapper)
sys.exit(install.main([command, "--target", "codex", "--scope", scope, *extra, "--json"]))
'''


def make_link(at, to):
    at.parent.mkdir(parents=True, exist_ok=True)
    if sys.platform == 'win32':
        import _winapi

        _winapi.CreateJunction(str(to), str(at))
    else:
        os.symlink(to, at, target_is_directory=True)


def files_under(folder):
    return {
        str(path): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in Path(folder).rglob('*')
        if path.is_file()
    }


@pytest.mark.parametrize(
    'command, hook, scope',
    [
        ('install', '_document_status', 'user'),
        ('uninstall', 'uninstall_skill', 'user'),
        ('install', '_document_status', 'project'),
    ],
)
def test_second_target_is_refused_when_the_first_wins_after_the_command_line_check(command, hook, scope, tmp_path):
    home = tmp_path / 'home'
    base = home if scope == 'user' else tmp_path / 'project'
    project = '' if scope == 'user' else str(base)
    shared = base / '.agents' / 'skills'
    shared.mkdir(parents=True)
    make_link(base / '.claude' / 'skills', shared)
    driver, mark = tmp_path / 'driver.py', tmp_path / 'mark.json'
    driver.write_text(DRIVER, encoding='utf-8')
    env = {**os.environ, 'HOME': str(home), 'USERPROFILE': str(home), 'PYTHONUTF8': '1'}

    proc = subprocess.run(
        [sys.executable, str(driver), str(ROOT), str(INSTALL), str(mark), str(shared), hook, command, scope, project],
        cwd=tmp_path, env=env, capture_output=True, text=True, timeout=120,
    )

    winner = json.loads(mark.read_text(encoding='utf-8'))
    assert winner['exit'] == 0 and winner['files'], 'the concurrent winner did not install'
    payload = json.loads(proc.stdout)
    assert proc.returncode == 2, proc.stdout + proc.stderr
    assert payload.get('state') == 'failed', payload
    assert payload.get('code') == 'installer.owner.mismatch', payload
    receipt = json.loads((shared / 'deeper-reading' / '.install-receipt.json').read_text(encoding='utf-8'))
    assert receipt['target'] == 'claude'
    assert files_under(shared) == winner['files']
    assert sorted(entry.name for entry in shared.iterdir()) == ['deeper-reading']


@pytest.mark.parametrize('operation', ['install', 'uninstall'])
def test_owner_check_runs_under_the_lock_and_a_refusal_changes_nothing(operation, tmp_path):
    target = tmp_path / 'skills' / 'deeper-reading'
    manifest = load_manifest(ROOT / 'MANIFEST.json')

    def install(**extra):
        return install_skill(
            ROOT, target, manifest, target_name='generic-agents', scope='user', runtime_profile='standalone',
            document_profile='standalone', document_status=READY, **extra,
        )

    if operation == 'uninstall':
        install()
    before = files_under(tmp_path)
    lock_seen = []

    def refuse():
        lock_seen.append((target.parent / f'.{target.name}.install-lock').is_dir())
        raise InstallError('another target owns this folder', 'installer.owner.mismatch')

    act = install if operation == 'install' else (lambda **kw: uninstall_skill(target, **kw))
    with pytest.raises(InstallError) as caught:
        act(owner_check=refuse)

    assert caught.value.code == 'installer.owner.mismatch'
    assert lock_seen == [True]
    assert files_under(tmp_path) == before
    assert sorted(entry.name for entry in target.parent.iterdir() if entry != target) == []
