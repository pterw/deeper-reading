import json
from pathlib import Path
import re

import pytest

from layout import ROOT, SKILL_ROOT


def test_distribution_files_exist():
    assert (SKILL_ROOT / 'VERSION').is_file()
    assert (ROOT / 'MANIFEST.json').is_file()


def test_manifest_contract():
    manifest = json.loads((ROOT / 'MANIFEST.json').read_text(encoding='utf-8'))
    assert manifest['skill']['name'] == 'deeper-reading'
    assert manifest['skill']['entrypoint'] == 'SKILL.md'
    assert 'SKILL.md' in manifest['payload']
    assert 'references' in manifest['payload']
    assert 'scripts' in manifest['payload']
    assert 'tests' not in manifest['payload']
    assert 'installer' not in manifest['payload']
    assert manifest.get('prerequisites') == {}
    assert 'modules' in manifest['payload']
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


def _synthetic_package(tmp_path: Path, skill: dict, skill_dir: str = '.'):
    from installer.manifest import Manifest

    pkg = tmp_path / 'pkg'
    folder = pkg / skill_dir
    (folder / 'modules').mkdir(parents=True)
    (folder / 'SKILL.md').write_text('---\nname: deeper-reading\ndescription: Use when testing.\n---\n', encoding='utf-8')
    data = {
        'schema_version': 1,
        'skill': {'name': 'deeper-reading', 'entrypoint': 'SKILL.md', **skill},
        'payload': ['SKILL.md', 'modules'],
        'prerequisites': {},
        'document_profiles': {'standalone': {}, 'oai-native': {}},
        'targets': ['generic-agents'],
    }
    return Manifest(data, pkg / 'MANIFEST.json'), pkg


def test_skill_root_places_skill_and_payload_under_that_folder(tmp_path: Path):
    from installer.manifest import skill_root, validate_manifest

    manifest, pkg = _synthetic_package(tmp_path, {'root': 'skills/deeper-reading'}, 'skills/deeper-reading')
    assert validate_manifest(manifest, pkg) == []
    assert skill_root(manifest.data, pkg) == (pkg / 'skills' / 'deeper-reading').resolve()


def test_payload_without_modules_is_refused(tmp_path: Path):
    from installer.manifest import validate_manifest

    manifest, pkg = _synthetic_package(tmp_path, {})
    manifest.data['payload'] = ['SKILL.md']
    assert validate_manifest(manifest, pkg) == ['Standalone runtime payload must include package-owned modules']


def test_skill_root_defaults_to_package_root(tmp_path: Path):
    from installer.manifest import skill_root, validate_manifest

    absent, pkg = _synthetic_package(tmp_path, {})
    assert validate_manifest(absent, pkg) == []
    assert skill_root(absent.data, pkg) == pkg.resolve()
    absent.data['skill']['root'] = '.'
    assert validate_manifest(absent, pkg) == []
    assert skill_root(absent.data, pkg) == pkg.resolve()


@pytest.mark.parametrize(
    ('value', 'expected'),
    [
        (5, 'skill.root must be a string'),
        ('/elsewhere', 'skill.root must be a relative path'),
        ('', 'skill.root must be a relative path'),
        ('skills\\deeper-reading', 'skill.root must be a relative path'),
        ('C:skills', 'skill.root must be a relative path'),
        ('../outside', 'skill.root must not contain ..'),
        ('skills/../skills', 'skill.root must not contain ..'),
        ('link', 'skill.root is outside the package root'),
        ('empty', 'Missing canonical SKILL.md at package root'),
        ('SKILL.md', 'Missing canonical SKILL.md at package root'),
        # Breaks two rules (absolute, and no SKILL.md there): only the first is reported.
        ('/missing', 'skill.root must be a relative path'),
    ],
)
def test_skill_root_refuses_each_bad_form_with_one_error(tmp_path: Path, value, expected):
    from installer.manifest import skill_root, validate_manifest

    manifest, pkg = _synthetic_package(tmp_path, {'root': value}, 'real')
    (pkg / 'empty').mkdir()
    outside = tmp_path / 'outside'
    outside.mkdir()
    (outside / 'SKILL.md').write_text('---\nname: deeper-reading\n---\n', encoding='utf-8')
    if value == 'link':
        try:
            (pkg / 'link').symlink_to(outside, target_is_directory=True)
        except OSError:
            pytest.skip('directory symlinks unavailable')
    assert validate_manifest(manifest, pkg) == [expected]
    with pytest.raises(ValueError, match=re.escape(expected)):
        skill_root(manifest.data, pkg)


def test_npm_control_plane_is_not_installed_as_skill_payload():
    manifest = json.loads((ROOT / 'MANIFEST.json').read_text(encoding='utf-8'))
    assert 'package.json' not in manifest['payload']
    assert 'installer/node' not in manifest['payload']


def _payload_files(manifest: dict) -> set[str]:
    files: set[str] = set()
    for entry in manifest['payload']:
        path = SKILL_ROOT / entry
        found = [path] if path.is_file() else [p for p in path.rglob('*') if p.is_file()]
        files.update(p.relative_to(SKILL_ROOT).as_posix() for p in found)
    return files


def test_payload_markdown_links_resolve_inside_payload():
    import posixpath
    import re

    manifest = json.loads((ROOT / 'MANIFEST.json').read_text(encoding='utf-8'))
    files = _payload_files(manifest)
    broken = []
    for rel in sorted(f for f in files if f.endswith('.md')):
        text = (SKILL_ROOT / rel).read_text(encoding='utf-8')
        # Text inside a fenced code block is an example, not a navigable link.
        text = re.sub(r'^(```|~~~)[^\n]*\n.*?^\1', '', text, flags=re.M | re.S)
        # Likewise an inline code span: a backtick run to the next run of the
        # same length, within one paragraph.
        text = re.sub(r'(?<!`)(`+)(?!`)(?:(?!\n[ \t]*\n).)*?(?<!`)\1(?!`)', '', text, flags=re.S)
        for link in re.findall(r'\]\(([^)\s]+)\)', text):
            if re.match(r'[A-Za-z][A-Za-z0-9+.-]*:|#', link):
                continue
            base = '' if rel.startswith('modules/') else posixpath.dirname(rel)  # R107
            target = posixpath.normpath(posixpath.join(base, link.split('#')[0]))
            if target not in files:
                broken.append(f'{rel} -> {link}')
    assert broken == []
