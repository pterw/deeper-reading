import hashlib
import json
import os
from pathlib import Path
import sys

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


@pytest.mark.parametrize('malicious', ['Z:/dr-no-such/x', '//dr-no-such-host/share/x'])
def test_uninstall_rejects_drive_and_unc_receipt_paths_on_every_os(tmp_path, malicious):
    target = make_install(tmp_path)
    receipt_path = target / '.install-receipt.json'
    receipt = json.loads(receipt_path.read_text(encoding='utf-8'))
    receipt['payload_hashes'] = {malicious: hashlib.sha256(b'x').hexdigest()}
    receipt_path.write_text(json.dumps(receipt), encoding='utf-8')

    with pytest.raises(InstallError, match='managed payload path'):
        uninstall_skill(target, force=True)


def test_uninstall_rejects_receipt_paths_outside_install_root(tmp_path):
    target = make_install(tmp_path)
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
        uninstall_skill(target, force=True)

    assert victim.read_text(encoding='utf-8') == 'do not touch'


def test_uninstall_rejects_symlink_resolved_escape(tmp_path):
    target = make_install(tmp_path)
    victim = tmp_path / 'outside.txt'
    victim.write_text('do not touch', encoding='utf-8')
    link = target / 'escape'
    try:
        link.symlink_to(tmp_path, target_is_directory=True)
    except OSError:
        pytest.skip('symlinks unavailable on this platform')

    receipt_path = target / '.install-receipt.json'
    receipt = json.loads(receipt_path.read_text(encoding='utf-8'))
    receipt['payload_hashes'] = {
        'escape/outside.txt': hashlib.sha256(b'do not touch').hexdigest(),
    }
    receipt_path.write_text(json.dumps(receipt), encoding='utf-8')

    with pytest.raises(InstallError, match='managed payload path'):
        uninstall_skill(target, force=True)

    assert victim.read_text(encoding='utf-8') == 'do not touch'


def _link(at: Path, to: Path):
    if sys.platform == 'win32':
        import _winapi

        _winapi.CreateJunction(str(to), str(at))
    else:
        os.symlink(to, at, target_is_directory=True)


def test_uninstall_rejects_escape_through_a_long_link_chain(tmp_path):
    # Two chains of 25 links: a path through both is past the 40 links Linux follows for one lookup.
    # Python resolves links itself, so it must still see where the path ends; Ubuntu CI is the real check.
    target = make_install(tmp_path)
    victim = tmp_path / 'outside.txt'
    victim.write_text('do not touch', encoding='utf-8')
    for prefix in ('a', 'b'):
        (target/f'real{prefix}').mkdir()
        _link(target/f'{prefix}25', target/f'real{prefix}')
        for i in range(24, -1, -1):
            _link(target/f'{prefix}{i}', target/f'{prefix}{i + 1}')
    _link(target/'reala'/'b0', target/'b0')
    _link(target/'realb'/'escape', tmp_path)

    receipt_path = target / '.install-receipt.json'
    receipt = json.loads(receipt_path.read_text(encoding='utf-8'))
    receipt['payload_hashes'] = {
        'a0/b0/escape/outside.txt': hashlib.sha256(b'do not touch').hexdigest(),
    }
    receipt_path.write_text(json.dumps(receipt), encoding='utf-8')

    with pytest.raises(InstallError, match='managed payload path'):
        uninstall_skill(target, force=True)

    assert victim.read_text(encoding='utf-8') == 'do not touch'
