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
