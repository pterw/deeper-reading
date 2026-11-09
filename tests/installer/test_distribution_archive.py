import json
import os
from pathlib import Path
import subprocess
import sys
from zipfile import ZipFile
import pytest

from installer.distribution import build_distribution

ROOT = Path(__file__).resolve().parents[2]


SHIPPED = ['deeper-reading/MANIFEST.json', 'deeper-reading/skills/deeper-reading/SKILL.md']


def _shipped_source(tmp_path):
    root = tmp_path / 'source'
    (root / 'skills' / 'deeper-reading').mkdir(parents=True)
    (root / 'skills' / 'deeper-reading' / 'SKILL.md').write_text('skill')
    (root / 'MANIFEST.json').write_text('{"skill": {"root": "skills/deeper-reading"}}')
    return root


def test_distribution_excludes_private_and_generated_worktree_files(tmp_path):
    root = _shipped_source(tmp_path)
    (root / '.env').write_text('private')
    (root / 'personal-review.html').write_text('private')
    (root / 'dist').mkdir()
    (root / 'dist' / 'old.zip').write_bytes(b'old archive')
    archive = build_distribution(root, tmp_path / 'bundle.zip')
    with ZipFile(archive) as zf:
        assert zf.namelist() == SHIPPED


def test_distribution_refuses_to_overwrite_source(tmp_path):
    source = tmp_path / 'SKILL.md'
    source.write_text('keep')
    with pytest.raises(ValueError):
        build_distribution(tmp_path, source)
    assert source.read_text() == 'keep'


def test_failed_distribution_preserves_previous_archive(tmp_path, monkeypatch):
    import installer.distribution as distribution
    root = _shipped_source(tmp_path)
    archive = tmp_path / 'bundle.zip'
    archive.write_bytes(b'previous archive')
    def fail(*args, **kwargs):
        raise OSError('injected write failure')
    monkeypatch.setattr(distribution.ZipFile, 'write', fail)
    with pytest.raises(OSError, match='injected'):
        build_distribution(root, archive)
    assert archive.read_bytes() == b'previous archive'
    assert set(tmp_path.iterdir()) == {root, archive}


def test_distribution_archive_has_one_canonical_skill_root(tmp_path):
    archive = tmp_path / 'bundle.zip'
    build_distribution(ROOT, archive)
    with ZipFile(archive) as zf:
        names = set(zf.namelist())
    prefix = 'deeper-reading/'
    assert prefix + 'skills/deeper-reading/SKILL.md' in names
    assert prefix + 'SKILL.md' not in names
    assert prefix + 'MANIFEST.json' in names
    assert prefix + 'installer/install.py' in names
    assert prefix + 'installer/install.sh' in names
    assert prefix + 'installer/install.ps1' in names
    assert prefix + 'README.md' in names
    assert prefix + 'CONTRIBUTING.md' not in names
    assert prefix + 'deeper-reading/SKILL.md' not in names


def test_extracted_archive_installs_the_0_2_6_file_list(tmp_path):
    archive = tmp_path / 'bundle.zip'
    build_distribution(ROOT, archive)
    with ZipFile(archive) as zf:
        zf.extractall(tmp_path / 'extracted')
    package = tmp_path / 'extracted' / 'deeper-reading'
    home = tmp_path / 'home'
    project = tmp_path / 'project'
    home.mkdir()
    project.mkdir()
    env = {**os.environ, 'HOME': str(home), 'USERPROFILE': str(home), 'PYTHONUTF8': '1'}
    install = str(package / 'installer' / 'install.py')
    for args in (['doctor'], ['install', '--target', 'generic-agents', '--scope', 'project',
                              '--project-dir', str(project)]):
        proc = subprocess.run([sys.executable, install, *args, '--json'], cwd=tmp_path, env=env,
                              capture_output=True, text=True, timeout=120)
        assert proc.returncode == 0, proc.stdout + proc.stderr
    target = project / '.agents' / 'skills' / 'deeper-reading'
    installed = sorted(p.relative_to(target).as_posix() for p in target.rglob('*') if p.is_file())
    pin = json.loads((ROOT / 'tests' / 'fixtures' / 'installed-files-0.2.6.json').read_text(encoding='utf-8'))
    assert [name for name in installed if name != '.install-receipt.json'] == pin


def _rooted_source(tmp_path, *, skill_at):
    root = tmp_path / 'source'
    (root / skill_at).mkdir(parents=True)
    (root / skill_at / 'SKILL.md').write_text('skill')
    (root / 'MANIFEST.json').write_text('{"skill": {"root": "inner/skill"}}')
    return root


def test_distribution_skill_guard_follows_manifest_skill_root(tmp_path):
    root = _rooted_source(tmp_path, skill_at='inner/skill')
    assert build_distribution(root, tmp_path / 'bundle.zip').is_file()


def test_distribution_refuses_when_skill_is_missing_at_manifest_skill_root(tmp_path):
    root = _rooted_source(tmp_path, skill_at='.')
    with pytest.raises(ValueError):
        build_distribution(root, tmp_path / 'bundle.zip')


def test_distribution_excludes_caches_and_generated_receipts(tmp_path):
    archive = tmp_path / 'bundle.zip'
    build_distribution(ROOT, archive)
    with ZipFile(archive) as zf:
        names = zf.namelist()
    assert not any('__pycache__' in name for name in names)
    assert not any('.pytest_cache' in name for name in names)
    assert not any(name.endswith('.install-receipt.json') for name in names)


def test_distribution_includes_npm_metadata_and_node_installer(tmp_path):
    archive = tmp_path / 'bundle.zip'
    build_distribution(ROOT, archive)
    with ZipFile(archive) as zf:
        names = set(zf.namelist())
    assert 'deeper-reading/package.json' in names
    assert 'deeper-reading/installer/node/cli.js' in names
    assert 'deeper-reading/installer/node/core.js' in names
    assert 'deeper-reading/installer/node/manifest.js' in names


def test_distribution_excludes_npm_tarballs(tmp_path):
    root = _shipped_source(tmp_path)
    scripts = root / 'skills' / 'deeper-reading' / 'scripts'
    scripts.mkdir()
    (scripts / 'deeper-reading-test-only.tgz').write_bytes(b'not a release artifact')
    archive = build_distribution(root, tmp_path / 'bundle.zip')
    with ZipFile(archive) as zf:
        assert zf.namelist() == SHIPPED
