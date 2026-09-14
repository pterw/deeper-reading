import json
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]

def run_script(name, *args):
    return subprocess.run([sys.executable, '-B', str(ROOT / 'scripts' / name), *map(str,args)],
                          capture_output=True, text=True, timeout=15)

@pytest.mark.parametrize('value', [None, [], 'invalid', 5])
def test_non_object_ledger_fails_with_machine_readable_dod(tmp_path, value):
    ledger = tmp_path / 'run.json'
    ledger.write_text(json.dumps(value), encoding='utf-8')
    result = run_script('verify_run.py', ledger)
    assert result.returncode == 1
    assert 'Traceback' not in result.stderr
    dod = json.loads((tmp_path / 'dod.json').read_text())
    assert dod['codes'] == ['json.ledger.type']
    assert not dod['passed']

def test_extractor_cannot_overwrite_source(tmp_path):
    source = tmp_path / 'source.md'
    source.write_text('# Important source\nDo not destroy.\n', encoding='utf-8')
    before = source.read_bytes()
    result = run_script('extract_markdown.py', source, '--out', source)
    assert result.returncode != 0
    assert source.read_bytes() == before
    assert 'FAIL:' in result.stderr

def test_run_root_output_rejects_symlink_escape(tmp_path):
    root = tmp_path / 'run'
    outside = tmp_path / 'outside'
    root.mkdir(); outside.mkdir()
    try:
        (root / 'evidence').symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip('directory symlinks unavailable')
    source = tmp_path / 'source.md'
    source.write_text('source', encoding='utf-8')
    result = run_script('extract_markdown.py', source, '--run-root', root)
    assert result.returncode != 0
    assert not list(outside.iterdir())

def test_verifier_cannot_overwrite_ledger_named_dod(tmp_path):
    ledger = tmp_path / 'dod.json'
    ledger.write_text('{}', encoding='utf-8')
    result = run_script('verify_run.py', ledger)
    assert result.returncode == 1
    assert ledger.read_text() == '{}'

def test_verifier_rejects_dod_symlink(tmp_path):
    ledger = tmp_path / 'run.json'
    ledger.write_text('{}', encoding='utf-8')
    outside = tmp_path / 'outside.txt'
    outside.write_text('keep', encoding='utf-8')
    try:
        (tmp_path / 'dod.json').symlink_to(outside)
    except OSError:
        pytest.skip('file symlinks unavailable')
    result = run_script('verify_run.py', ledger)
    assert result.returncode == 1
    assert outside.read_text() == 'keep'

@pytest.mark.parametrize('source', [{'format':[]}, {'format':'pdf','authority':{}}, None])
def test_malformed_source_is_a_finding(source):
    from scripts.verify_run import validate_findings
    findings = validate_findings({'source':source})
    assert findings
    assert all(f.code and f.predicate for f in findings)

def test_package_findings_accepted_without_revalidation(tmp_path):
    from scripts.verification_findings import Finding
    from scripts.verify_run import build_dod
    result = build_dod({}, [Finding('source.uri.required','source_identity_verified','missing')])
    assert result['codes'] == ['source.uri.required']

def test_backend_provenance_rejects_unknown_and_forged_capability():
    from scripts.verify_run import validate_findings
    for extraction in [{'backend':'unknown','format':'pdf','capabilities':['text']},
                       {'backend':'pypdf','format':'pdf','capabilities':['ocr']},
                       {'backend':'   ','format':'pdf','capabilities':[]}]:
        findings = validate_findings({'source':{'format':'pdf'}, 'extraction':extraction})
        assert any(f.code.startswith('extraction.') for f in findings)


def test_existing_evidence_symlink_escape_cannot_pass_verification(tmp_path):
    from tests.run_fixture import valid_run
    from scripts.verify_run import validate_findings
    root = tmp_path / 'run'
    root.mkdir()
    run = valid_run(root)
    outside = tmp_path / 'outside-evidence'
    (root / 'evidence').rename(outside)
    try:
        (root / 'evidence').symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip('directory symlinks unavailable')
    findings = validate_findings(run)
    assert any(f.predicate == 'output_containment_valid' for f in findings)
