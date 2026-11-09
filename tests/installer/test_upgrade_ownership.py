import hashlib
import json
import shutil
from pathlib import Path

import pytest

from installer.core import InstallError, install_skill, verify_installation
from installer.manifest import load_manifest, skill_root
from installer.prerequisites import PrerequisiteStatus

ROOT = Path(__file__).resolve().parents[2]
READY = PrerequisiteStatus('ready', ('upgrade-test-ready',))


def install(package_root: Path, target: Path):
    return install_skill(
        package_root,
        target,
        load_manifest(package_root / 'MANIFEST.json'),
        target_name='generic-agents',
        scope='user',
        runtime_profile='standalone',
        document_profile='standalone',
        document_status=READY,
    )


def test_upgrade_refuses_modified_managed_file(tmp_path):
    target = tmp_path / 'skills' / 'deeper-reading'
    install(ROOT, target)
    skill = target / 'SKILL.md'
    skill.write_text(skill.read_text(encoding='utf-8') + '\nuser modification\n', encoding='utf-8')
    modified = skill.read_bytes()

    with pytest.raises(InstallError, match='modified managed files'):
        install(ROOT, target)

    assert skill.read_bytes() == modified


@pytest.mark.parametrize('name', ['legacy-managed.txt', 'README.md'])
def test_upgrade_removes_files_owned_by_old_manifest_but_not_new_manifest(tmp_path, name):
    package = tmp_path / 'package'
    shutil.copytree(ROOT, package, ignore=shutil.ignore_patterns('__pycache__', '.pytest_cache'))
    (package / 'skills' / 'deeper-reading' / name).write_text('old managed payload', encoding='utf-8')
    manifest_path = package / 'MANIFEST.json'
    new_manifest_bytes = manifest_path.read_bytes()
    data = json.loads(new_manifest_bytes)
    data['payload'].append(name)
    manifest_path.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')

    target = tmp_path / 'skills' / 'deeper-reading'
    install(package, target)
    assert (target / name).is_file()

    manifest_path.write_bytes(new_manifest_bytes)
    install(package, target)

    assert not (target / name).exists()
    assert verify_installation(target)['passed'] is True


def test_upgrade_from_0_2_5_removes_the_old_module_files(tmp_path):
    fixtures = ROOT / 'tests' / 'fixtures'
    old = json.loads((fixtures / 'installed-files-0.2.5.json').read_text(encoding='utf-8'))
    new = json.loads((fixtures / 'installed-files-0.2.6.json').read_text(encoding='utf-8'))
    stale = sorted(set(old) - set(new))
    assert len(stale) == 6

    package = tmp_path / 'package'
    shutil.copytree(ROOT, package, ignore=shutil.ignore_patterns('__pycache__', '.pytest_cache'))
    manifest_path = package / 'MANIFEST.json'
    real_manifest_bytes = manifest_path.read_bytes()
    data = json.loads(real_manifest_bytes)
    source = skill_root(data, package)
    for relative in stale:
        path = source / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('old module payload', encoding='utf-8')
    data['payload'].append('skills')
    manifest_path.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')

    target = tmp_path / 'home' / 'skills' / 'deeper-reading'
    install(package, target)
    assert all((target / relative).is_file() for relative in stale)

    manifest_path.write_bytes(real_manifest_bytes)
    install(package, target)

    assert not any((target / relative).exists() for relative in stale)
    assert not (target / 'skills').exists()
    installed = sorted(p.relative_to(target).as_posix() for p in target.rglob('*') if p.is_file())
    assert [name for name in installed if name != '.install-receipt.json'] == new
    assert all((target / name).is_file() for name in new if name.startswith('modules/'))
    assert verify_installation(target)['passed'] is True


def test_install_refuses_existing_unmanaged_skill_root(tmp_path):
    target = tmp_path / 'skills' / 'deeper-reading'
    target.mkdir(parents=True)
    (target / 'SKILL.md').write_text('unmanaged', encoding='utf-8')

    with pytest.raises(InstallError, match='existing target is unmanaged'):
        install(ROOT, target)

    assert (target / 'SKILL.md').read_text(encoding='utf-8') == 'unmanaged'


def test_upgrade_rejects_receipt_paths_outside_install_root(tmp_path):
    target = tmp_path / 'skills' / 'deeper-reading'
    install(ROOT, target)
    victim = tmp_path / 'outside.txt'
    victim.write_text('do not touch', encoding='utf-8')
    malicious = str(victim)

    receipt_path = target / '.install-receipt.json'
    receipt = json.loads(receipt_path.read_text(encoding='utf-8'))
    receipt['payload_hashes'] = {
        malicious: hashlib.sha256(b'do not touch').hexdigest(),
    }
    receipt_path.write_text(json.dumps(receipt), encoding='utf-8')

    with pytest.raises(InstallError, match='managed payload path'):
        install(ROOT, target)

    assert victim.read_text(encoding='utf-8') == 'do not touch'
