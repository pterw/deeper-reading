import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from installer.core import install_skill, verify_installation
from installer.manifest import load_manifest
from installer.prerequisites import PrerequisiteStatus

READY = PrerequisiteStatus('ready', ('test-ready',))
NOT_AN_OBJECT = {'array': '[]', 'null': 'null', 'string': '"text"', 'skill-not-an-object': '{"skill": 5}'}


def _package(root: Path, *, skill_root: str | None, version: str = '9.9.9', extra: str = '') -> Path:
    """Build a synthetic package; ``skill_root`` None means a root-level layout."""
    folder = root if skill_root is None else root / skill_root
    (folder / 'scripts').mkdir(parents=True)
    (folder / 'skills').mkdir()
    (folder / 'SKILL.md').write_text('---\nname: demo\n---\nbody\n', encoding='utf-8')
    (folder / 'VERSION').write_text(version + '\n', encoding='utf-8')
    (folder / 'scripts' / 'tool.py').write_text('# tool\n', encoding='utf-8')
    (folder / 'skills' / 'owned.txt').write_text('owned\n', encoding='utf-8')
    if extra:
        (folder / 'scripts' / extra).write_text('# extra\n', encoding='utf-8')
    manifest = {
        'schema_version': 1,
        'skill': {'name': 'demo', 'entrypoint': 'SKILL.md'},
        'payload': ['SKILL.md', 'VERSION', 'scripts', 'skills'],
        'prerequisites': {},
        'document_profiles': {'standalone': {}, 'oai-native': {}},
    }
    if skill_root is not None:
        manifest['skill']['root'] = skill_root
    (root / 'MANIFEST.json').write_text(json.dumps(manifest), encoding='utf-8')
    return root


def _install(package: Path, target: Path) -> dict:
    return install_skill(
        package,
        target,
        load_manifest(package / 'MANIFEST.json'),
        target_name='generic-agents',
        scope='user',
        runtime_profile='standalone',
        document_profile='standalone',
        document_status=READY,
    )


def _files(target: Path) -> set[str]:
    return {
        p.relative_to(target).as_posix()
        for p in target.rglob('*')
        if p.is_file() and p.name != '.install-receipt.json'
    }


def _receipt(target: Path) -> dict:
    return json.loads((target / '.install-receipt.json').read_text(encoding='utf-8'))


def test_rooted_package_installs_hashes_and_verifies(tmp_path):
    package = _package(tmp_path / 'pkg', skill_root='pkg-skill/demo', version='1.2.3')
    target = tmp_path / 'target'
    _install(package, target)
    receipt = _receipt(target)
    assert receipt['version'] == '1.2.3'
    assert set(receipt['payload_hashes']) == _files(target)
    assert 'scripts/tool.py' in receipt['payload_hashes']
    assert verify_installation(target)['passed'] is True


def test_upgrade_from_root_level_to_rooted_leaves_no_stale_files(tmp_path):
    flat = _package(tmp_path / 'flat', skill_root=None, extra='old.py')
    rooted = _package(tmp_path / 'rooted', skill_root='pkg-skill/demo')
    target = tmp_path / 'target'
    _install(flat, target)
    assert 'scripts/old.py' in _files(target)
    _install(rooted, target)
    assert 'scripts/old.py' not in _files(target)
    assert set(_receipt(target)['payload_hashes']) == _files(target)
    assert verify_installation(target)['passed'] is True


def _cli(package: Path, home: Path, command: str):
    env = {**os.environ, 'HOME': str(home), 'USERPROFILE': str(home)}
    args = [sys.executable, str(package / 'installer' / 'install.py'), command, '--target', 'generic-agents', '--json']
    return subprocess.run(args, cwd=home, env=env, capture_output=True, text=True, timeout=120)


@pytest.mark.parametrize('command', ['doctor', 'install', 'verify'])
@pytest.mark.parametrize(
    'damage',
    [
        'root-not-a-string',
        'root-outside-package',
        'corrupt-json',
        'missing-file',
        'array',
        'null',
        'string',
        'skill-not-an-object',
    ],
)
def test_bad_manifest_fails_cleanly_through_the_cli(tmp_path, command, damage):
    repo = Path(__file__).resolve().parents[2]
    package = tmp_path / 'package'
    shutil.copytree(repo / 'installer', package / 'installer', ignore=shutil.ignore_patterns('node', '__pycache__'))
    for name in ('MANIFEST.json', 'SKILL.md', 'VERSION', 'LICENSE'):
        shutil.copy2(repo / name, package / name)
    for name in ('references', 'scripts', 'skills'):
        shutil.copytree(repo / name, package / name, ignore=shutil.ignore_patterns('__pycache__'))
    home = tmp_path / 'home'
    home.mkdir()
    assert _cli(package, home, 'install').returncode == 0
    manifest = package / 'MANIFEST.json'
    data = json.loads(manifest.read_text(encoding='utf-8'))
    if damage == 'corrupt-json':
        manifest.write_text('{not json', encoding='utf-8')
    elif damage == 'missing-file':
        manifest.unlink()
    elif damage in NOT_AN_OBJECT:
        manifest.write_text(NOT_AN_OBJECT[damage], encoding='utf-8')
    else:
        data['skill']['root'] = 5 if damage == 'root-not-a-string' else '../elsewhere'
        manifest.write_text(json.dumps(data), encoding='utf-8')

    proc = _cli(package, home, command)

    assert proc.returncode == 2
    assert 'Traceback' not in proc.stderr
    assert json.loads(proc.stdout)['state'] == 'failed'
