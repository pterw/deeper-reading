import json
import hashlib
import os
import subprocess
import sys
from pathlib import Path

import pytest

from installer.core import InstallError, install_skill, uninstall_skill, verify_installation
from installer.manifest import load_manifest
from installer.prerequisites import PrerequisiteStatus

ROOT = Path(__file__).resolve().parents[2]
READY = PrerequisiteStatus('ready', ('mutation-baseline-ready',))


def valid_install(tmp_path: Path) -> Path:
    target = tmp_path / 'skills' / 'deeper-reading'
    install_skill(
        ROOT,
        target,
        load_manifest(ROOT / 'MANIFEST.json'),
        target_name='generic-agents',
        scope='user',
        runtime_profile='standalone',
        document_profile='standalone',
        document_status=READY,
    )
    assert verify_installation(target)['passed'] is True
    return target


def receipt(target: Path) -> dict:
    path = target / '.install-receipt.json'
    return json.loads(path.read_text(encoding='utf-8'))


def write_receipt(target: Path, data: dict) -> None:
    (target / '.install-receipt.json').write_text(json.dumps(data, indent=2, sort_keys=True) + '\n', encoding='utf-8')


def test_unmutated_installation_baseline_passes(tmp_path):
    target = valid_install(tmp_path)
    result = verify_installation(target)
    assert result['passed'] is True
    assert all(result['predicates'].values())
    assert result['violations'] == []


def test_mutation_relocates_canonical_skill_under_nested_root(tmp_path):
    target = valid_install(tmp_path)
    nested = target / target.name
    nested.mkdir()
    (target / 'SKILL.md').replace(nested / 'SKILL.md')
    result = verify_installation(target)
    assert result['passed'] is False
    assert result['predicates']['canonical_root'] is False


def test_mutation_deletes_manifest_owned_reference(tmp_path):
    target = valid_install(tmp_path)
    (target / 'references' / 'html.md').unlink()
    result = verify_installation(target)
    assert result['passed'] is False
    assert result['predicates']['payload_hashes_match'] is False


def test_mutation_marks_document_profile_missing_in_receipt(tmp_path):
    target = valid_install(tmp_path)
    data = receipt(target)
    data['document_status']['state'] = 'missing'
    write_receipt(target, data)
    result = verify_installation(target)
    assert result['passed'] is False
    assert result['predicates']['document_profile_resolved'] is False


def test_mutation_labels_native_oai_profile_on_portable_runtime(tmp_path):
    target = valid_install(tmp_path)
    data = receipt(target)
    data['runtime_profile'] = 'standalone'
    data['document_profile'] = 'oai-native'
    write_receipt(target, data)
    result = verify_installation(target)
    assert result['passed'] is False
    assert result['predicates']['runtime_document_profile_consistent'] is False


def test_mutation_changes_payload_bytes_without_receipt_update(tmp_path):
    target = valid_install(tmp_path)
    with (target / 'SKILL.md').open('a', encoding='utf-8') as fh:
        fh.write('\nmutation\n')
    result = verify_installation(target)
    assert result['passed'] is False
    assert result['predicates']['payload_hashes_match'] is False


def test_mutation_claims_failed_host_discovery(tmp_path):
    target = valid_install(tmp_path)
    data = receipt(target)
    data['host_discovery']['state'] = 'failed'
    write_receipt(target, data)
    result = verify_installation(target)
    assert result['passed'] is False
    assert result['predicates']['host_discovery_verified_or_explicitly_not_available'] is False


def test_mutation_leaves_stage_after_success(tmp_path):
    target = valid_install(tmp_path)
    (target.parent / f'.{target.name}.stage-mutant').mkdir()
    result = verify_installation(target)
    assert result['passed'] is False
    assert result['predicates']['no_staging_leftovers'] is False


def test_mutation_leaves_backup_after_success(tmp_path):
    target = valid_install(tmp_path)
    (target.parent / f'.{target.name}.backup-mutant').mkdir()
    result = verify_installation(target)
    assert result['passed'] is False
    assert result['predicates']['no_backup_leftovers'] is False


def test_mutation_receipt_points_at_different_installed_root(tmp_path):
    target = valid_install(tmp_path)
    data = receipt(target)
    data['installed_root'] = str(tmp_path / 'somewhere-else' / target.name)
    write_receipt(target, data)
    result = verify_installation(target)
    assert result['passed'] is False
    assert result['predicates']['receipt_matches_installed_root'] is False


def test_mutation_deletes_install_receipt(tmp_path):
    target = valid_install(tmp_path)
    (target / '.install-receipt.json').unlink()
    result = verify_installation(target)
    assert result['passed'] is False
    assert result['predicates']['receipt_written'] is False


# Spellings are built from a tmp victim so they never name a real location.
ESCAPE_SPELLINGS = [
    pytest.param(lambda victim: str(victim), id='absolute'),
    pytest.param(lambda victim: '\\\\?\\' + str(victim), id='verbatim-prefix'),
    pytest.param(lambda victim: '../outside.txt', id='parent-relative'),
    pytest.param(lambda victim: 'C:foo', id='drive-relative'),
]
if os.sep != '/':
    ESCAPE_SPELLINGS.append(pytest.param(lambda victim: victim.as_posix(), id='posix-absolute'))
    ESCAPE_SPELLINGS.append(pytest.param(lambda victim: '/' + victim.as_posix().split(':/', 1)[1], id='single-slash'))


@pytest.mark.parametrize('spell', ESCAPE_SPELLINGS)
def test_mutation_receipt_escape_spellings_are_rejected_for_containment(tmp_path, spell):
    target = valid_install(tmp_path)
    malicious = spell(tmp_path / 'outside.txt')
    data = receipt(target)
    data['payload_hashes'] = {
        malicious: hashlib.sha256(b'do not touch').hexdigest(),
    }
    write_receipt(target, data)
    result = verify_installation(target)
    assert result['passed'] is False
    assert result['predicates']['payload_hashes_match'] is False
    assert any('managed payload path escapes install root' in v for v in result['violations'])


def test_mutation_receipt_symlink_resolved_escape_is_rejected_for_containment(tmp_path):
    target = valid_install(tmp_path)
    outside = tmp_path / 'outside'
    outside.mkdir()
    victim = outside / 'victim.txt'
    victim.write_text('do not touch', encoding='utf-8')
    link = target / 'escape'
    try:
        link.symlink_to(outside, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip('symlinks unavailable on this platform')

    data = receipt(target)
    data['payload_hashes'] = {
        'escape/victim.txt': hashlib.sha256(b'do not touch').hexdigest(),
    }
    write_receipt(target, data)
    result = verify_installation(target)
    assert result['passed'] is False
    assert result['predicates']['payload_hashes_match'] is False
    assert any('managed payload path escapes install root' in v for v in result['violations'])
    assert victim.read_text(encoding='utf-8') == 'do not touch'


# A directory is not a file, so Python reports it with its existing "receipt missing"
# errors; a file that exists but cannot be read (OSError) must give the invalid-receipt error.
DIRECTORY = 'receipt path is a directory'
UNREADABLE = 'receipt file raises OSError on read'
CORRUPT_RECEIPTS = [
    pytest.param('{', id='truncated-json'),
    pytest.param('[]', id='array'),
    pytest.param('null', id='null'),
    pytest.param('"x"', id='string'),
    pytest.param('{"document_status": 3}', id='document-status-int'),
    pytest.param('{"payload_hashes": ["a"]}', id='payload-hashes-array'),
    pytest.param('{"host_discovery": "verified"}', id='host-discovery-string'),
    pytest.param('{"document_status": null}', id='document-status-null'),
    pytest.param('{"host_discovery": null}', id='host-discovery-null'),
    pytest.param(DIRECTORY, id='receipt-is-a-directory'),
    pytest.param(UNREADABLE, id='receipt-unreadable'),
]


def _corrupt_install(tmp_path: Path, text: str) -> Path:
    target = valid_install(tmp_path)
    receipt_path = target / '.install-receipt.json'
    if text == DIRECTORY:
        receipt_path.unlink()
        receipt_path.mkdir()
    else:
        receipt_path.write_text('{}' if text == UNREADABLE else text, encoding='utf-8')
    return target


@pytest.mark.parametrize('text', CORRUPT_RECEIPTS)
def test_corrupt_receipt_fails_closed_in_install_verify_and_uninstall(tmp_path, monkeypatch, text):
    target = _corrupt_install(tmp_path, text)
    manifest = load_manifest(ROOT / 'MANIFEST.json')
    real_read_text = Path.read_text

    if text == UNREADABLE:
        def read_text(self, *args, **kwargs):
            if self.name == '.install-receipt.json':
                raise PermissionError('receipt is not readable')
            return real_read_text(self, *args, **kwargs)

        monkeypatch.setattr(Path, 'read_text', read_text)
    expected = 'receipt missing' if text == DIRECTORY else 'invalid installation receipt'

    with pytest.raises(InstallError, match=expected):
        install_skill(
            ROOT, target, manifest, target_name='generic-agents', scope='user',
            runtime_profile='standalone', document_profile='standalone', document_status=READY,
        )
    result = verify_installation(target)
    assert result['passed'] is False
    assert any(expected in v for v in result['violations'])
    with pytest.raises(InstallError, match=expected):
        uninstall_skill(target, force=True)

    monkeypatch.undo()
    assert (target / 'SKILL.md').is_file()
    if text == DIRECTORY:
        assert (target / '.install-receipt.json').is_dir()
    else:
        assert (target / '.install-receipt.json').read_text(encoding='utf-8') == ('{}' if text == UNREADABLE else text)


def test_corrupt_receipt_through_the_cli_exits_2_with_empty_stderr(tmp_path):
    project = tmp_path / 'project'
    target = project / '.agents' / 'skills' / 'deeper-reading'
    home = tmp_path / 'home'
    home.mkdir()
    install_skill(
        ROOT, target, load_manifest(ROOT / 'MANIFEST.json'), target_name='generic-agents', scope='project',
        runtime_profile='standalone', document_profile='standalone', document_status=READY,
    )
    (target / '.install-receipt.json').write_text('null', encoding='utf-8')
    env = {**os.environ, 'HOME': str(home), 'USERPROFILE': str(home)}
    for command in ('install', 'verify', 'uninstall'):
        proc = subprocess.run(
            [sys.executable, str(ROOT / 'installer' / 'install.py'), command, '--target', 'generic-agents',
             '--scope', 'project', '--project-dir', str(project), '--json'],
            cwd=tmp_path, env=env, capture_output=True, text=True,
        )
        assert proc.returncode == 2, command
        assert proc.stderr == '', command
        data = json.loads(proc.stdout)
        assert data.get('state') == 'failed' or data.get('passed') is False
        assert 'invalid installation receipt' in proc.stdout
