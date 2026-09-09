import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def test_distribution_files_exist():
    assert (ROOT / 'VERSION').is_file()
    assert (ROOT / 'MANIFEST.json').is_file()


def test_manifest_contract():
    manifest = json.loads((ROOT / 'MANIFEST.json').read_text(encoding='utf-8'))
    assert manifest['skill']['name'] == 'deeper-reading'
    assert manifest['skill']['entrypoint'] == 'SKILL.md'
    assert 'SKILL.md' in manifest['payload']
    assert 'references' in manifest['payload']
    assert 'scripts' in manifest['payload']
    assert 'scripts/verify_run.py' not in manifest['payload']
    assert 'tests' not in manifest['payload']
    assert 'installer' not in manifest['payload']
    assert manifest.get('prerequisites') == {}
    assert 'skills' in manifest['payload']
    assert set(manifest['document_profiles']) == {'standalone', 'oai-native'}


def test_manifest_parser_validates_root_and_frontmatter():
    from installer.manifest import load_manifest, validate_manifest

    manifest = load_manifest(ROOT / 'MANIFEST.json')
    assert validate_manifest(manifest, ROOT) == []


def test_manifest_parser_rejects_path_traversal(tmp_path: Path):
    from installer.manifest import load_manifest, validate_manifest

    bad = {
        'schema_version': 1,
        'skill': {'name': 'deeper-reading', 'entrypoint': 'SKILL.md'},
        'payload': ['../escape'],
        'prerequisites': {},
        'document_profiles': {'standalone': {}, 'oai-native': {}},
        'targets': ['generic-agents'],
    }
    path = tmp_path / 'MANIFEST.json'
    path.write_text(json.dumps(bad), encoding='utf-8')
    root = tmp_path / 'pkg'
    root.mkdir()
    (root / 'SKILL.md').write_text('---\nname: deeper-reading\ndescription: Use when testing.\n---\n', encoding='utf-8')
    errors = validate_manifest(load_manifest(path), root)
    assert any('traversal' in error.lower() or 'outside' in error.lower() for error in errors)
