import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_portable_extractors_are_runtime_payload():
    required = [
        'scripts/extract_pdf.py',
        'scripts/extract_docx.py',
        'scripts/extract_html.py',
        'scripts/extract_markdown.py',
        'scripts/chunk_common.py',
        'scripts/traversal_report.py',
    ]
    for rel in required:
        assert (ROOT / rel).is_file(), rel


def test_lengthy_markdown_reference_exists():
    assert (ROOT / 'references/lengthy-markdown.md').is_file()


def test_manifest_installs_complete_scripts_directory():
    manifest = json.loads((ROOT / 'MANIFEST.json').read_text(encoding='utf-8'))
    assert 'scripts' in manifest['payload']
    assert 'scripts/verify_run.py' not in manifest['payload']


def test_readme_is_installed_with_runtime_payload():
    manifest = json.loads((ROOT / 'MANIFEST.json').read_text(encoding='utf-8'))
    assert 'README.md' in manifest['payload']
