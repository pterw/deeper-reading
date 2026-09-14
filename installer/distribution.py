from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
from zipfile import ZIP_DEFLATED, ZipFile

PACKAGE_ROOT = Path(__file__).resolve().parents[1]

EXCLUDED_PARTS = {'__pycache__', '.pytest_cache', '.git'}
EXCLUDED_NAMES = {'.install-receipt.json'}
EXCLUDED_SUFFIXES = {'.pyc', '.tgz'}
RELEASE_FILES = {'LICENSE', 'MANIFEST.json', 'README.md', 'SKILL.md', 'VERSION',
                 'CHANGELOG.md', 'CONTRIBUTING.md', 'package.json',
                 'requirements-optional.txt'}
RELEASE_DIRECTORIES = {'installer', 'references', 'scripts', 'skills'}


def _included(path: Path, root: Path) -> bool:
    rel = path.relative_to(root)
    if rel.as_posix() not in RELEASE_FILES and rel.parts[0] not in RELEASE_DIRECTORIES:
        return False
    if any(part in EXCLUDED_PARTS for part in rel.parts):
        return False
    if path.name in EXCLUDED_NAMES or path.suffix in EXCLUDED_SUFFIXES:
        return False
    return path.is_file()


def build_distribution(package_root: Path, output_path: Path) -> Path:
    root = Path(package_root).resolve()
    if not (root / 'SKILL.md').is_file():
        raise ValueError('package root must contain SKILL.md')
    requested = Path(output_path).absolute()
    if requested.is_symlink():
        raise ValueError('archive output must not be a symbolic link')
    output = requested.resolve()
    if output.suffix.lower() != '.zip':
        raise ValueError('archive output must have a .zip extension')
    if output.is_relative_to(root) and output.relative_to(root).parts[0] != 'dist':
        raise ValueError('archives inside the package must be written under dist/')
    files = []
    for path in sorted(root.rglob('*')):
        if not _included(path, root):
            continue
        if not path.resolve().is_relative_to(root) or path.is_symlink():
            raise ValueError(f'release file must be a regular contained file: {path}')
        if output.exists() and path.samefile(output):
            raise ValueError(f'archive would overwrite source: {path}')
        files.append(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    prefix = 'deeper-reading'
    with tempfile.NamedTemporaryFile(dir=output.parent, prefix='.deeper-reading-',
                                     suffix='.zip', delete=False) as handle:
        temporary = Path(handle.name)
    try:
        with ZipFile(temporary, 'w', compression=ZIP_DEFLATED) as zf:
            for path in files:
                rel = path.relative_to(root).as_posix()
                zf.write(path, f'{prefix}/{rel}')
        os.replace(temporary, output)
    finally:
        temporary.unlink(missing_ok=True)
    return output


def sha256sum(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog='deeper-reading-dist',
        description='Build distribution zip archive for deeper-reading skill.',
    )
    parser.add_argument(
        '--package-root',
        type=Path,
        default=PACKAGE_ROOT,
        help='Path to deeper-reading repository root.',
    )
    parser.add_argument(
        '--out',
        type=Path,
        default=PACKAGE_ROOT / 'dist' / 'deeper-reading.zip',
        help='Output zip path.',
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='Output result as JSON.',
    )
    args = parser.parse_args(argv)

    out_file = build_distribution(args.package_root, args.out)
    digest = sha256sum(out_file)
    size = out_file.stat().st_size

    data = {
        'status': 'created',
        'archive': str(out_file),
        'bytes': size,
        'sha256': digest,
    }
    if args.json:
        print(json.dumps(data, indent=2))
    else:
        print('Distribution archive built successfully:')
        print(f'  Path:   {out_file}')
        print(f'  Size:   {size} bytes ({size / 1024:.1f} KB)')
        print(f'  SHA256: {digest}')
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (OSError, ValueError) as exc:
        print(f'FAIL: {exc}', file=sys.stderr)
        raise SystemExit(1)

