from pathlib import Path
from zipfile import ZipFile
import pytest

from installer.distribution import build_distribution

ROOT = Path(__file__).resolve().parents[2]


def test_distribution_excludes_private_and_generated_worktree_files(tmp_path):
    root = tmp_path / 'source'
    root.mkdir()
    (root / 'SKILL.md').write_text('skill')
    (root / '.env').write_text('private')
    (root / 'personal-review.html').write_text('private')
    (root / 'dist').mkdir()
    (root / 'dist' / 'old.zip').write_bytes(b'old archive')
    archive = build_distribution(root, tmp_path / 'bundle.zip')
    with ZipFile(archive) as zf:
        assert zf.namelist() == ['deeper-reading/SKILL.md']


def test_distribution_refuses_to_overwrite_source(tmp_path):
    source = tmp_path / 'SKILL.md'
    source.write_text('keep')
    with pytest.raises(ValueError):
        build_distribution(tmp_path, source)
    assert source.read_text() == 'keep'


def test_failed_distribution_preserves_previous_archive(tmp_path, monkeypatch):
    import installer.distribution as distribution
    root = tmp_path / 'source'
    root.mkdir()
    (root / 'SKILL.md').write_text('skill')
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
    assert prefix + 'SKILL.md' in names
    assert prefix + 'MANIFEST.json' in names
    assert prefix + 'installer/install.py' in names
    assert prefix + 'installer/install.sh' in names
    assert prefix + 'installer/install.ps1' in names
    assert prefix + 'deeper-reading/SKILL.md' not in names


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
    candidate = ROOT / 'deeper-reading-test-only.tgz'
    candidate.write_bytes(b'not a release artifact')
    try:
        archive = tmp_path / 'bundle.zip'
        build_distribution(ROOT, archive)
        with ZipFile(archive) as zf:
            assert not any(name.endswith('.tgz') for name in zf.namelist())
    finally:
        candidate.unlink(missing_ok=True)
