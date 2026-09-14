import json
import hashlib
from pathlib import Path

import pytest

from installer.core import install_skill, verify_installation
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
    assert verify_installation(target)['passed'] is True


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


@pytest.mark.parametrize(
    'malicious',
    [
        '/tmp/outside.txt',
        '../outside.txt',
        'C:/outside.txt',
        'C:foo',
        r'C:\outside.txt',
        r'\\server\share\outside.txt',
    ],
)
def test_mutation_receipt_escape_spellings_are_rejected_for_containment(tmp_path, malicious):
    target = valid_install(tmp_path)
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
