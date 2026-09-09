from pathlib import Path

import pytest

from installer.core import InstallError, install_skill, uninstall_skill
from installer.manifest import load_manifest
from installer.prerequisites import PrerequisiteStatus

ROOT = Path(__file__).resolve().parents[2]
READY = PrerequisiteStatus('ready', ('test-ready',))


def make_install(tmp_path: Path):
    target = tmp_path/'skills'/'deeper-reading'
    install_skill(ROOT, target, load_manifest(ROOT/'MANIFEST.json'), target_name='generic-agents', scope='user', runtime_profile='standalone', document_profile='standalone', document_status=READY)
    return target


def test_uninstall_preserves_unowned_file(tmp_path):
    target = make_install(tmp_path)
    note = target/'my-note.txt'
    note.write_text('mine', encoding='utf-8')
    result = uninstall_skill(target)
    assert result['state'] == 'uninstalled'
    assert note.read_text(encoding='utf-8') == 'mine'
    assert not (target/'SKILL.md').exists()
    assert not (target/'.install-receipt.json').exists()


def test_uninstall_refuses_modified_owned_file_without_force(tmp_path):
    target = make_install(tmp_path)
    (target/'SKILL.md').write_text('changed', encoding='utf-8')
    with pytest.raises(InstallError):
        uninstall_skill(target)
    assert (target/'SKILL.md').exists()


def test_force_uninstall_removes_modified_owned_file_but_not_unowned(tmp_path):
    target = make_install(tmp_path)
    (target/'SKILL.md').write_text('changed', encoding='utf-8')
    note = target/'my-note.txt'
    note.write_text('mine', encoding='utf-8')
    uninstall_skill(target, force=True)
    assert not (target/'SKILL.md').exists()
    assert note.exists()
