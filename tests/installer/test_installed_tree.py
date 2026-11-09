import json
import os
from pathlib import Path
import subprocess
import sys

# Pins the tree the real package installs to the file list that 0.2.6 installs
# (tests/fixtures/installed-files-0.2.6.json), so a change to the source layout cannot
# silently change what lands in a user's skill folder. The package root comes from this
# file's own path, so the pin holds before and after the source files move.
ROOT = Path(__file__).parents[2]
INSTALL = ROOT / 'installer' / 'install.py'
PIN = json.loads((ROOT / 'tests' / 'fixtures' / 'installed-files-0.2.6.json').read_text(encoding='utf-8'))
RECEIPT = '.install-receipt.json'


def test_installed_tree_matches_the_0_2_6_file_list(tmp_path):
    home = tmp_path / 'home'
    project = tmp_path / 'project'
    home.mkdir()
    project.mkdir()
    env = {**os.environ, 'HOME': str(home), 'USERPROFILE': str(home), 'PYTHONUTF8': '1'}
    proc = subprocess.run(
        [sys.executable, str(INSTALL), 'install', '--target', 'generic-agents', '--scope', 'project',
         '--project-dir', str(project), '--json'],
        cwd=tmp_path, env=env, capture_output=True, text=True, timeout=120,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr

    target = project / '.agents' / 'skills' / 'deeper-reading'
    installed = sorted(p.relative_to(target).as_posix() for p in target.rglob('*') if p.is_file())
    assert [name for name in installed if name != RECEIPT] == PIN
    receipt = json.loads((target / RECEIPT).read_text(encoding='utf-8'))
    assert sorted(receipt['payload_hashes']) == PIN
