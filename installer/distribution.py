from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from zipfile import ZIP_DEFLATED, ZipFile

PACKAGE_ROOT = Path(__file__).resolve().parents[1]

EXCLUDED_PARTS = {'__pycache__', '.pytest_cache', '.git'}
EXCLUDED_NAMES = {'.install-receipt.json'}


def _included(path: Path, root: Path) -> bool:
    rel = path.relative_to(root)
    if any(part in EXCLUDED_PARTS for part in rel.parts):
        return False
    if path.name in EXCLUDED_NAMES or path.suffix == '.pyc':
        return False
    return path.is_file()


def build_distribution(package_root: Path, output_path: Path) -> Path:
    root = Path(package_root).resolve()
    output = Path(output_path).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    prefix = 'deeper-reading'
    with ZipFile(output, 'w', compression=ZIP_DEFLATED) as zf:
        for path in sorted(root.rglob('*')):
            if not _included(path, root):
                continue
            if path.resolve() == output:
                continue
            rel = path.relative_to(root).as_posix()
            zf.write(path, f'{prefix}/{rel}')
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
    raise SystemExit(main())

