import hashlib
from pathlib import Path
import subprocess
import sys

import pytest

from layout import ROOT, SKILL_ROOT
sys.path.insert(0, str(SKILL_ROOT / 'scripts'))
import extract_pdf

FIXTURE = ROOT / 'tests/fixtures/pdf-first-run'

@pytest.mark.parametrize('backend', ['pypdf','pdftotext'])
def test_committed_pdf_including_empty_page_and_provenance(backend):
    if not extract_pdf._backend_available(backend):
        pytest.skip(f'optional PDF backend {backend} unavailable; other PDF backend tests remain active')
    source = FIXTURE / 'source/sample.pdf'
    manifest = extract_pdf.extract(source, max_bytes=12000, backend=backend)
    assert len(manifest['chunks']) == 3
    assert [chunk['locator']['pages'] for chunk in manifest['chunks']] == [[1],[2],[3]]
    assert manifest['chunks'][1]['content'] == ''
    assert 'Page One Alpha' in manifest['chunks'][0]['content']
    assert 'Page Three Omega' in manifest['chunks'][2]['content']
    assert manifest['extraction']['backend'].split()[0] == backend
    assert manifest['extraction']['capabilities'] == ['text']
    assert manifest['source']['sha256'] == hashlib.sha256(source.read_bytes()).hexdigest()
    assert manifest == extract_pdf.extract(source, max_bytes=12000, backend=backend)

def test_encrypted_pdf_requires_correct_password():
    if not extract_pdf._backend_available('pypdf'):
        pytest.skip('optional pypdf unavailable; encrypted PDF fixture untested')
    source = FIXTURE / 'source/sample-encrypted.pdf'
    for password in [None, 'wrong']:
        with pytest.raises(RuntimeError, match='encrypted'):
            extract_pdf.extract(source, max_bytes=12000, backend='pypdf', password=password)
    manifest = extract_pdf.extract(source, max_bytes=12000, backend='pypdf', password='fixture-password')
    assert len(manifest['chunks']) == 3

def test_pdftotext_timeout_is_bounded_and_does_not_echo_password(monkeypatch):
    monkeypatch.setattr(extract_pdf.shutil, 'which', lambda _: 'pdftotext')
    def timeout(args, **kwargs):
        assert kwargs['timeout'] <= 60
        raise subprocess.TimeoutExpired(args, kwargs['timeout'])
    monkeypatch.setattr(extract_pdf.subprocess, 'run', timeout)
    with pytest.raises(RuntimeError, match='timed out') as exc:
        extract_pdf._extract_pdftotext(Path('x.pdf'), 'secret-value')
    assert 'secret-value' not in str(exc.value)
