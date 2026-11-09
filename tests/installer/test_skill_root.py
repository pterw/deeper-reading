import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest
from layout import SKILL_ROOT

from installer.core import install_skill, verify_installation
from installer.manifest import load_manifest
from installer.prerequisites import PrerequisiteStatus

READY = PrerequisiteStatus('ready', ('test-ready',))
NOT_AN_OBJECT = {'array': '[]', 'null': 'null', 'string': '"text"', 'skill-not-an-object': '{"skill": 5}'}


def _package(root: Path, *, skill_root: str | None, version: str = '9.9.9', extra: str = '') -> Path:
    """Build a synthetic package; ``skill_root`` None means a root-level layout."""
    folder = root if skill_root is None else root / skill_root
    (folder / 'scripts').mkdir(parents=True)
    (folder / 'modules').mkdir()
    (folder / 'SKILL.md').write_text('---\nname: demo\n---\nbody\n', encoding='utf-8')
    (folder / 'VERSION').write_text(version + '\n', encoding='utf-8')
    (folder / 'scripts' / 'tool.py').write_text('# tool\n', encoding='utf-8')
    (folder / 'modules' / 'owned.txt').write_text('owned\n', encoding='utf-8')
    if extra:
        (folder / 'scripts' / extra).write_text('# extra\n', encoding='utf-8')
    manifest = {
        'schema_version': 1,
        'skill': {'name': 'demo', 'entrypoint': 'SKILL.md'},
        'payload': ['SKILL.md', 'VERSION', 'scripts', 'modules'],
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


def _self_link(path: Path) -> None:
    """Make ``path`` a link loop: a symlink to itself, or on Windows two junctions pointing at each other."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if sys.platform != 'win32':
        path.symlink_to(path.name, target_is_directory=True)
        return
    import _winapi

    other = path.with_name(path.name + '-other')
    other.mkdir()
    _winapi.CreateJunction(str(other), str(path))
    other.rmdir()
    _winapi.CreateJunction(str(path), str(other))


@pytest.mark.parametrize('root', ['skills/demo/SKILL.md', 'skills/demo/SKILL.md/sub', 'loop', 'loop/sub'])
def test_unusable_skill_root_gives_one_error_not_a_raise(tmp_path, root):
    from installer.manifest import validate_manifest

    package = _package(tmp_path / 'pkg', skill_root='skills/demo')
    manifest = load_manifest(package / 'MANIFEST.json')
    manifest.data['skill']['root'] = root
    if root.startswith('loop'):
        _self_link(package / 'loop')

    assert validate_manifest(manifest, package) == ['Missing canonical SKILL.md at package root']


@pytest.mark.parametrize(
    ('root', 'expected'),
    [
        ('pkg-skill/demo', ['Payload entry does not exist: loop', 'Payload entry does not exist: gone']),
        ('skills/demo/SKILL.md', ['Missing canonical SKILL.md at package root']),
    ],
)
def test_payload_loop_is_reported_and_checking_goes_on_unless_the_root_is_unusable(tmp_path, root, expected):
    from installer.manifest import validate_manifest

    package = _package(tmp_path / 'pkg', skill_root='pkg-skill/demo')
    manifest = load_manifest(package / 'MANIFEST.json')
    manifest.data['payload'] += ['loop', 'gone']
    _self_link(package / 'pkg-skill' / 'demo' / 'loop')  # where a usable root looks
    _self_link(package / 'loop')  # where an unusable root falls back to the package root
    manifest.data['skill']['root'] = root

    assert validate_manifest(manifest, package) == expected


def test_a_runtime_error_that_is_not_a_symlink_loop_keeps_its_traceback(monkeypatch):
    from installer import install

    def broken(args):
        raise RuntimeError('something else broke')

    monkeypatch.setattr(install, 'command_doctor', broken)

    with pytest.raises(RuntimeError, match='something else broke'):
        install.main(['doctor', '--target', 'generic-agents', '--json'])


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
    for name in ('MANIFEST.json', 'LICENSE'):
        shutil.copy2(repo / name, package / name)
    package_skill = package / 'skills' / 'deeper-reading'
    shutil.copytree(SKILL_ROOT, package_skill, ignore=shutil.ignore_patterns('__pycache__'))
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


def _listing(root: Path) -> list[str]:
    """Every entry under ``root``, links listed but never entered (``rglob`` raises on a junction loop on Windows)."""
    found = []
    for folder, names, files in os.walk(root, followlinks=False):
        for name in (*names, *files):
            found.append((Path(folder) / name).relative_to(root).as_posix())
        # os.walk lists a link to a folder under names; pruning it keeps the walk from entering it.
        names[:] = [n for n in names if not _is_link(Path(folder) / n)]
    return sorted(found)


def _is_link(path: Path) -> bool:
    """A symlink or, on Windows, a junction (``islink`` misses junctions before Python 3.12)."""
    info = path.lstat()
    return path.is_symlink() or bool(getattr(info, 'st_file_attributes', 0) & 0x400)


@pytest.mark.parametrize('command', ['install', 'uninstall'])
def test_target_that_is_a_symlink_loop_fails_cleanly_through_the_cli(tmp_path, command):
    repo = Path(__file__).resolve().parents[2]
    home = tmp_path / 'home'
    home.mkdir()
    _self_link(home / '.agents' / 'skills' / 'deeper-reading')
    before = _listing(home)

    proc = _cli(repo, home, command)

    assert _listing(home) == before
    assert proc.returncode == 2
    assert 'Traceback' not in proc.stderr
    assert json.loads(proc.stdout)['state'] == 'failed'
