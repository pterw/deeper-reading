import json
from pathlib import Path

from installer.core import install_skill, verify_installation
from installer.manifest import load_manifest
from installer.prerequisites import PrerequisiteStatus

ROOT = Path(__file__).resolve().parents[2]
READY = PrerequisiteStatus('ready', ('test-ready',))


def make_install(tmp_path: Path):
    target = tmp_path / 'skills' / 'deeper-reading'
    install_skill(
        ROOT, target, load_manifest(ROOT/'MANIFEST.json'),
        target_name='generic-agents', scope='user', runtime_profile='standalone',
        document_profile='standalone', document_status=READY,
        discovery_state='not-available',
    )
    return target


def test_valid_installation_dod_passes(tmp_path):
    target = make_install(tmp_path)
    result = verify_installation(target)
    assert result['passed'] is True
    assert all(result['predicates'].values())
    assert result['violations'] == []


def test_tampered_payload_fails_hash_predicate(tmp_path):
    target = make_install(tmp_path)
    (target/'SKILL.md').write_text('tampered', encoding='utf-8')
    result = verify_installation(target)
    assert result['passed'] is False
    assert result['predicates']['payload_hashes_match'] is False


def test_unready_document_profile_receipt_fails_dod(tmp_path):
    target = make_install(tmp_path)
    path = target/'.install-receipt.json'
    receipt = json.loads(path.read_text())
    receipt['document_status']['state'] = 'missing'
    path.write_text(json.dumps(receipt), encoding='utf-8')
    result = verify_installation(target)
    assert result['predicates']['document_profile_resolved'] is False


def test_stage_leftover_fails_dod(tmp_path):
    target = make_install(tmp_path)
    leftover = target.parent / '.deeper-reading.stage-orphan'
    leftover.mkdir()
    result = verify_installation(target)
    assert result['predicates']['no_staging_leftovers'] is False
