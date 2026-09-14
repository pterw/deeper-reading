import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

import pytest
from installer.core import InstallError, install_skill, verify_installation, verify_installed
from installer.manifest import load_manifest
from installer.prerequisites import PrerequisiteStatus

ROOT = Path(__file__).resolve().parents[2]

def package_at(root, text):
    root.mkdir()
    (root / 'SKILL.md').write_text('---\nname: deeper-reading\n---\n', encoding='utf-8')
    (root / 'VERSION').write_text(text, encoding='utf-8')
    (root / 'skills').mkdir()
    manifest = {'skill': {'name':'deeper-reading', 'entrypoint':'SKILL.md'},
                'payload':['SKILL.md', 'VERSION', 'skills'],
                'document_profiles': {'standalone':{}, 'oai-native':{}}}
    (root / 'MANIFEST.json').write_text(json.dumps(manifest), encoding='utf-8')
    return root

def install(package, target, **options):
    return install_skill(package, target, load_manifest(package / 'MANIFEST.json'),
        target_name='generic-agents', scope='user', runtime_profile='standalone',
        document_profile='standalone', document_status=PrerequisiteStatus('ready'), **options)

def command(language, package, target, barrier, pause):
    if language == 'node' and not shutil.which('node'):
        pytest.skip('Node is required for cross-runtime locking tests')
    executable = [sys.executable, '-B'] if language == 'python' else ['node']
    suffix = 'py' if language == 'python' else 'mjs'
    return executable + [str(Path(__file__).with_name(f'lock_worker.{suffix}')),
                         str(package), str(target), str(barrier), pause]

@pytest.mark.parametrize('owner_language,peer_language', [
    ('python','python'), ('node','node'), ('python','node'), ('node','python')])
@pytest.mark.parametrize('pause', ['after-stage','after-backup','after-replace',
                                  'after-verify','after-receipt','discovery'])
def test_peer_cannot_mutate_until_failed_owner_finishes(tmp_path, owner_language, peer_language, pause):
    old = package_at(tmp_path / 'old', 'old')
    new = package_at(tmp_path / 'new', 'new')
    target = tmp_path / 'target'
    install(old, target)
    owner = subprocess.Popen(command(owner_language, new, target, tmp_path, pause),
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        deadline = time.monotonic() + 20
        while not (tmp_path / 'ready').exists():
            assert owner.poll() is None, owner.communicate()
            assert time.monotonic() < deadline, 'owner did not reach barrier'
            time.sleep(.01)
        for operation in ['install', 'uninstall']:
            peer = subprocess.run(command(peer_language, new, target, tmp_path, operation),
                                  capture_output=True, text=True, timeout=15)
            assert peer.returncode == 2, peer.stdout + peer.stderr
            assert 'locked' in peer.stdout.lower(), peer.stdout + peer.stderr
    finally:
        (tmp_path / 'release').touch()
        try:
            stdout, stderr = owner.communicate(timeout=15)
        finally:
            if owner.poll() is None:
                owner.kill()
                owner.communicate()
    assert 'deliberate owner failure' in stdout, stdout + stderr
    assert (target / 'VERSION').read_text() == 'old'
    assert verify_installation(target)['passed']
    install(new, target)
    assert (target / 'VERSION').read_text() == 'new'
    assert verify_installation(target)['passed']
    assert not list(tmp_path.glob('.target.*'))


@pytest.mark.parametrize('language', ['python', 'node'])
def test_abandoned_lock_is_not_stolen(tmp_path, language):
    package = package_at(tmp_path / 'package', 'new')
    target = tmp_path / 'target'
    lock = tmp_path / '.target.install-lock'
    lock.mkdir()
    for operation in ['install', 'uninstall']:
        peer = subprocess.run(command(language, package, target, tmp_path, operation),
                              capture_output=True, text=True, timeout=15)
        assert peer.returncode == 2
        assert 'locked' in peer.stdout
        assert lock.is_dir()
        assert not target.exists()


@pytest.mark.parametrize('raw', ['C:foo', 'c:foo', '../outside', None, ''])
def test_internal_verifier_keeps_containment_exception_contract(tmp_path, raw):
    with pytest.raises(InstallError, match='managed payload path'):
        verify_installed(tmp_path, {raw: '0' * 64})


def test_containment_failure_rolls_back_and_releases_lock(tmp_path, monkeypatch):
    old = package_at(tmp_path / 'old', 'old')
    new = package_at(tmp_path / 'new', 'new')
    target = tmp_path / 'target'
    install(old, target)
    import installer.core as core
    original = core.verify_installed
    def fail_at_target(root, hashes):
        return original(root, {'C:foo':'0' * 64} if root == target else hashes)
    with monkeypatch.context() as context:
        context.setattr(core, 'verify_installed', fail_at_target)
        with pytest.raises(InstallError, match='managed payload path'):
            install(new, target)
    assert (target / 'VERSION').read_text() == 'old'
    assert verify_installation(target)['passed']
    install(new, target)


@pytest.mark.parametrize('language', ['python', 'node'])
@pytest.mark.parametrize('target_exists', [False, True])
def test_alias_uses_physical_target_lock(tmp_path, language, target_exists):
    package = package_at(tmp_path / 'package', 'new')
    target = tmp_path / 'target'
    if target_exists:
        install(package, target)
    alias = tmp_path / 'alias'
    try:
        alias.symlink_to(target, target_is_directory=True)
    except OSError:
        pytest.skip('directory symlinks unavailable')
    lock = tmp_path / '.target.install-lock'
    lock.mkdir()
    peer = subprocess.run(command(language, package, alias, tmp_path, 'install'),
                          capture_output=True, text=True, timeout=15)
    assert peer.returncode == 2, peer.stdout + peer.stderr
    assert 'locked' in peer.stdout, peer.stdout + peer.stderr
    assert lock.is_dir()
    assert not (tmp_path / '.alias.install-lock').exists()
