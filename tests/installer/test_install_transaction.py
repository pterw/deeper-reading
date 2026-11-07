import json
from pathlib import Path

import pytest

from installer import core as installer_core
from installer.manifest import load_manifest
from installer.core import InstallError, install_skill, verify_installation
from installer.prerequisites import PrerequisiteStatus

ROOT = Path(__file__).resolve().parents[2]
READY = PrerequisiteStatus('ready', ('test-ready',))


def install(tmp_path: Path, **kwargs):
    target = tmp_path / 'skills' / 'deeper-reading'
    return target, install_skill(
        ROOT,
        target,
        load_manifest(ROOT / 'MANIFEST.json'),
        target_name='generic-agents',
        scope='user',
        runtime_profile='standalone',
        document_profile='standalone',
        document_status=READY,
        **kwargs,
    )


def test_fresh_install_has_canonical_root_and_receipt(tmp_path):
    target, result = install(tmp_path)
    assert (target / 'SKILL.md').is_file()
    assert not (target / 'deeper-reading' / 'SKILL.md').exists()
    receipt = json.loads((target / '.install-receipt.json').read_text(encoding='utf-8'))
    assert receipt['skill'] == 'deeper-reading'
    assert result['state'] == 'installed'


def test_dry_run_mutates_nothing(tmp_path):
    target, result = install(tmp_path, dry_run=True)
    assert result['state'] == 'dry-run'
    assert not target.exists()
    assert not target.parent.exists()


def test_failure_after_replace_rolls_back_previous_install(tmp_path):
    target, _ = install(tmp_path)
    marker = target / 'user-note.txt'
    marker.write_text('keep me', encoding='utf-8')
    original_skill = (target / 'SKILL.md').read_bytes()

    def fail(point):
        if point == 'after-replace':
            raise RuntimeError('injected failure')

    with pytest.raises(InstallError):
        install(tmp_path, failure_injector=fail)

    assert (target / 'SKILL.md').read_bytes() == original_skill
    assert marker.read_text(encoding='utf-8') == 'keep me'


@pytest.mark.parametrize('mode', ['injector', 'real-removal'])
def test_backup_cleanup_failure_after_commit_keeps_the_new_install_and_warns(tmp_path, monkeypatch, mode):
    target, first = install(tmp_path)
    assert 'warnings' not in first
    fail = None
    if mode == 'injector':
        def fail(point):
            if point == 'cleanup-backup':
                raise OSError('injected cleanup failure')
    else:
        real_rmtree = installer_core.shutil.rmtree

        def rmtree_failing_for_backup(path, *args, **kwargs):
            if '.backup-' in Path(path).name:
                raise PermissionError('backup is undeletable')
            return real_rmtree(path, *args, **kwargs)

        monkeypatch.setattr(installer_core.shutil, 'rmtree', rmtree_failing_for_backup)

    _, result = install(tmp_path, failure_injector=fail)

    assert result['state'] == 'installed'
    assert len(result['warnings']) == 1
    assert 'backup cleanup failed' in result['warnings'][0]
    assert (target / 'SKILL.md').is_file()
    verdict = verify_installation(target)
    failed = [name for name, ok in verdict['predicates'].items() if not ok]
    assert failed == ['no_backup_leftovers']


def test_receipt_failure_still_rolls_back_to_the_previous_install(tmp_path):
    target, _ = install(tmp_path)
    original = (target / 'SKILL.md').read_bytes()

    def fail(point):
        if point == 'after-receipt':
            raise RuntimeError('injected failure')

    with pytest.raises(InstallError):
        install(tmp_path, failure_injector=fail)

    assert (target / 'SKILL.md').read_bytes() == original
    assert verify_installation(target)['passed'] is True


def test_upgrade_preserves_unowned_files(tmp_path):
    target, _ = install(tmp_path)
    marker = target / 'user-note.txt'
    marker.write_text('keep me', encoding='utf-8')
    install(tmp_path)
    assert marker.read_text(encoding='utf-8') == 'keep me'


def test_success_leaves_no_stage_or_backup_siblings(tmp_path):
    target, _ = install(tmp_path)
    leftovers = [p.name for p in target.parent.iterdir() if p.name.startswith('.deeper-reading.')]
    assert leftovers == []


def test_host_discovery_failure_rolls_back(tmp_path):
    target, _ = install(tmp_path)
    marker = target / 'user-note.txt'
    marker.write_text('keep me', encoding='utf-8')

    class Discovery:
        state = 'failed'
        evidence = ('injected discovery failure',)

    with pytest.raises(InstallError):
        install(tmp_path, discovery_verifier=lambda name: Discovery())

    assert marker.read_text(encoding='utf-8') == 'keep me'
    assert (target / 'SKILL.md').is_file()
