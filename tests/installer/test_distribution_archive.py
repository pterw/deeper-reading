from pathlib import Path
from zipfile import ZipFile

from installer.distribution import build_distribution

ROOT = Path(__file__).resolve().parents[2]


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
