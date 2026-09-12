import hashlib
import json
import shutil
from pathlib import Path

import pytest

from installer.core import InstallError, install_skill
from installer.manifest import load_manifest
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


def test_upgrade_removes_files_owned_by_old_manifest_but_not_new_manifest(tmp_path):
    package = tmp_path / 'package'
    shutil.copytree(ROOT, package, ignore=shutil.ignore_patterns('__pycache__', '.pytest_cache'))
    legacy = package / 'legacy-managed.txt'
    legacy.write_text('old managed payload', encoding='utf-8')
    manifest_path = package / 'MANIFEST.json'
    data = json.loads(manifest_path.read_text(encoding='utf-8'))
    data['payload'].append('legacy-managed.txt')
    manifest_path.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')

    target = tmp_path / 'skills' / 'deeper-reading'
    install(package, target)
    assert (target / 'legacy-managed.txt').is_file()

    data['payload'].remove('legacy-managed.txt')
    manifest_path.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
    install(package, target)

    assert not (target / 'legacy-managed.txt').exists()


def test_install_refuses_existing_unmanaged_skill_root(tmp_path):
    target = tmp_path / 'skills' / 'deeper-reading'
    target.mkdir(parents=True)
    (target / 'SKILL.md').write_text('unmanaged', encoding='utf-8')

    with pytest.raises(InstallError, match='existing target is unmanaged'):
        install(ROOT, target)

    assert (target / 'SKILL.md').read_text(encoding='utf-8') == 'unmanaged'


@pytest.mark.parametrize(
    'malicious',
    [
        '/tmp/outside.txt',
        '../outside.txt',
        'C:/outside.txt',
        r'C:\outside.txt',
        r'\\server\share\outside.txt',
    ],
)
def test_upgrade_rejects_receipt_paths_outside_install_root(tmp_path, malicious):
    target = tmp_path / 'skills' / 'deeper-reading'
    install(ROOT, target)
    victim = tmp_path / 'outside.txt'
    victim.write_text('do not touch', encoding='utf-8')

    receipt_path = target / '.install-receipt.json'
    receipt = json.loads(receipt_path.read_text(encoding='utf-8'))
    receipt['payload_hashes'] = {
        malicious: hashlib.sha256(b'do not touch').hexdigest(),
    }
    receipt_path.write_text(json.dumps(receipt), encoding='utf-8')

    with pytest.raises(InstallError, match='managed payload path'):
        install(ROOT, target)

    assert victim.read_text(encoding='utf-8') == 'do not touch'
