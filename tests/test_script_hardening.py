import json
import subprocess
import sys

import pytest

from layout import SKILL_ROOT

def run_script(name, *args):
    return subprocess.run([sys.executable, '-B', str(SKILL_ROOT / 'scripts' / name), *map(str,args)],
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

def _run_with_prior_passing_dod(root):
    from tests.run_fixture import valid_run
    run = valid_run(root)
    ledger = root / 'run.json'
    ledger.write_text(json.dumps(run), encoding='utf-8')
    (root / 'dod.json').write_text(json.dumps({'passed': True}), encoding='utf-8')
    return run, ledger


@pytest.mark.parametrize('locator', ['oops', None, []])
def test_non_object_locator_reports_missing_atomic_kind_and_rewrites_dod(tmp_path, locator):
    run, ledger = _run_with_prior_passing_dod(tmp_path)
    manifest_path = tmp_path / 'evidence' / 'chunk-manifest.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    manifest['chunks'][0].update(oversize_atomic=True, locator=locator)
    manifest_path.write_text(json.dumps(manifest), encoding='utf-8')
    result = run_script('verify_run.py', ledger)
    assert result.returncode == 1
    assert 'Traceback' not in result.stderr
    dod = json.loads((tmp_path / 'dod.json').read_text())
    assert dod['passed'] is False
    assert 'coverage.chunk.atomic_kind.missing' in dod['codes']


def _raise_key_error(run):
    raise KeyError('boom')


def _return_unknown_predicate(run):
    from scripts.verification_findings import Finding
    return [Finding('x', 'not_a_predicate', 'm')]


@pytest.mark.parametrize('broken', [_raise_key_error, _return_unknown_predicate],
                         ids=['any-exception', 'unknown-predicate'])
def test_validation_failure_becomes_ledger_validation_error(tmp_path, monkeypatch, broken):
    import scripts.verify_run as verify_run
    monkeypatch.setattr(verify_run, '_validate_findings', broken)
    assert 'ledger.validation.error' in [f.code for f in verify_run.validate_findings({})]


def test_validation_crash_through_main_rewrites_stale_passing_dod(tmp_path, monkeypatch):
    import scripts.verify_run as verify_run
    _run, ledger = _run_with_prior_passing_dod(tmp_path)
    monkeypatch.setattr(verify_run, '_validate_findings', _raise_key_error)
    monkeypatch.setattr(sys, 'argv', ['verify_run.py', str(ledger)])
    assert verify_run.main() == 1
    dod = json.loads((tmp_path / 'dod.json').read_text())
    assert dod['passed'] is False
    assert 'ledger.validation.error' in dod['codes']


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
    assert (tmp_path / 'dod.json').is_symlink()
    assert (tmp_path / 'dod.json').resolve() == outside.resolve()

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


def _empty_docx(path):
    import zipfile
    body = ('<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            '<w:body><w:p><w:r><w:drawing/></w:r></w:p></w:body></w:document>')
    with zipfile.ZipFile(path, 'w') as z:
        z.writestr('[Content_Types].xml', '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>')
        z.writestr('word/document.xml', body)


@pytest.mark.parametrize('script,name,content', [
    ('extract_html.py', 'a.html', '<script>x</script><style>p{}</style>'),
    ('extract_markdown.py', 'a.md', ''),
    ('extract_markdown.py', 'b.md', ' \n\t\n'),
    ('extract_docx.py', 'a.docx', None),
], ids=['html-scripts-only', 'md-empty', 'md-whitespace', 'docx-drawing-only'])
def test_extractor_fails_closed_when_no_text(tmp_path, script, name, content):
    source = tmp_path / name
    if content is None:
        _empty_docx(source)
    else:
        source.write_text(content, encoding='utf-8')
    out = tmp_path / 'manifest.json'
    result = run_script(script, source, '--out', out)
    assert result.returncode == 1
    assert 'no extractable text' in result.stderr
    assert script.removeprefix('extract_').removesuffix('.py') in result.stderr
    assert not out.exists()


def test_pdf_without_text_layer_points_at_ocr(tmp_path):
    sys.path.insert(0, str(SKILL_ROOT / 'scripts'))
    from chunk_common import build_manifest
    source = tmp_path / 'a.pdf'
    source.write_bytes(b'%PDF-1.4')
    kwargs = dict(strategy='page', max_bytes=1000)
    with pytest.raises(ValueError, match='no extractable text') as err:
        build_manifest(source, 'pdf', [{'content': ''}, {'content': ' \n'}], **kwargs)
    assert 'OCR' in str(err.value) and 'oai-native' in str(err.value)
    assert build_manifest(source, 'pdf', [{'content': ''}, {'content': 'text'}], **kwargs)['chunks']
