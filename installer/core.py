from __future__ import annotations

from dataclasses import asdict
from contextlib import contextmanager, nullcontext
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from pathlib import PurePosixPath
import re
import shutil
import uuid
from typing import Callable

from .manifest import Manifest, validate_manifest
from .prerequisites import PrerequisiteStatus


class InstallError(RuntimeError):
    pass


@contextmanager
def _target_lock(target: Path):
    """Shared Python/Node mkdir protocol; never steal a possibly live lock.

    The caller resolves target before entry and holds this sibling directory
    through every rollback and cleanup operation, including uninstall.
    """
    lock = target.parent / f'.{target.name}.install-lock'
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        lock.mkdir()
    except FileExistsError as exc:
        raise InstallError(f'installation target is locked: {lock}; retry after the active operation finishes') from exc
    except OSError as exc:
        raise InstallError(f'cannot acquire installation lock: {lock}: {exc}') from exc
    try:
        yield
    finally:
        # Only an owner that successfully created the directory can release it.
        # Never recursively delete lock contents or recover by age/PID guessing.
        try:
            lock.rmdir()
        except OSError as exc:
            raise InstallError(f'cannot release installation lock: {lock}: {exc}') from exc


_WINDOWS_DRIVE_RE = re.compile(r'^[A-Za-z]:')


def _managed_relpath(raw: object) -> Path:
    if not isinstance(raw, str) or not raw.strip():
        raise InstallError('managed payload path must be a non-empty relative path')
    normalized = raw.replace('\\', '/')
    if normalized.startswith('/') or normalized.startswith('//') or _WINDOWS_DRIVE_RE.match(normalized):
        raise InstallError(f'managed payload path escapes install root: {raw!r}')
    raw_parts = normalized.split('/')
    if any(part in {'', '.', '..'} for part in raw_parts):
        raise InstallError(f'managed payload path escapes install root: {raw!r}')
    pure = PurePosixPath(normalized)
    return Path(*pure.parts)


def _managed_path(root: Path, raw: object) -> Path:
    root = Path(root).resolve()
    candidate = root / _managed_relpath(raw)
    try:
        candidate.resolve(strict=False).relative_to(root)
    except ValueError as exc:
        raise InstallError(f'managed payload path escapes install root: {raw!r}') from exc
    return candidate


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def payload_files(package_root: Path, manifest: Manifest) -> list[Path]:
    root = Path(package_root)
    files: list[Path] = []
    for raw in manifest['payload']:
        path = root / raw
        if path.is_dir():
            files.extend(sorted(p for p in path.rglob('*') if p.is_file() and '__pycache__' not in p.parts and '.pytest_cache' not in p.parts))
        elif path.is_file():
            files.append(path)
    return sorted(set(files))


def payload_hashes(package_root: Path, manifest: Manifest) -> dict[str, str]:
    root = Path(package_root)
    return {str(path.relative_to(root)).replace(os.sep, '/'): _sha256(path) for path in payload_files(root, manifest)}


def _copy_payload(package_root: Path, stage: Path, manifest: Manifest) -> None:
    root = Path(package_root)
    for raw in manifest['payload']:
        src = root / raw
        dst = stage / raw
        if src.is_dir():
            shutil.copytree(src, dst, dirs_exist_ok=True, ignore=shutil.ignore_patterns('__pycache__', '.pytest_cache'))
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)


def verify_installed(target_root: Path, expected_hashes: dict[str, str]) -> list[str]:
    target = Path(target_root)
    errors: list[str] = []
    if not (target / 'SKILL.md').is_file():
        errors.append('missing canonical SKILL.md at installed root')
    for rel, expected in expected_hashes.items():
        path = _managed_path(target, rel)
        if not path.is_file():
            errors.append(f'missing payload file: {rel}')
        elif _sha256(path) != expected:
            errors.append(f'payload hash mismatch: {rel}')
    return errors


def _remove_tree(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)



def _upgrade_ownership(target_root: Path, expected_hashes: dict[str, str]) -> tuple[dict, set[str]]:
    receipt_path = target_root / '.install-receipt.json'
    if not receipt_path.is_file():
        raise InstallError('existing target is unmanaged; installation receipt missing')
    try:
        receipt = json.loads(receipt_path.read_text(encoding='utf-8'))
    except Exception as exc:
        raise InstallError(f'existing target has invalid installation receipt: {exc}') from exc
    old_owned = receipt.get('payload_hashes') or {}
    if not isinstance(old_owned, dict) or not old_owned:
        raise InstallError('existing target has no managed payload ownership record')
    modified: list[str] = []
    for rel, expected in old_owned.items():
        path = _managed_path(target_root, rel)
        if not path.is_file() or _sha256(path) != expected:
            modified.append(rel)
    if modified:
        raise InstallError('modified managed files: ' + ', '.join(sorted(modified)))
    stale = set(old_owned) - set(expected_hashes)
    return receipt, stale


def _prune_owned_files(stage: Path, stale: set[str]) -> None:
    for rel in sorted(stale, key=lambda x: len(Path(x).parts), reverse=True):
        path = _managed_path(stage, rel)
        if path.is_file():
            path.unlink()
    for path in sorted((p for p in stage.rglob('*') if p.is_dir()), key=lambda p: len(p.parts), reverse=True):
        try:
            path.rmdir()
        except OSError:
            pass

def install_skill(
    package_root: Path,
    target_root: Path,
    manifest: Manifest,
    *,
    target_name: str,
    scope: str,
    runtime_profile: str,
    document_profile: str,
    document_status: PrerequisiteStatus,
    discovery_state: str = 'not-available',
    discovery_verifier=None,
    dry_run: bool = False,
    failure_injector: Callable[[str], None] | None = None,
) -> dict:
    package_root = Path(package_root).resolve()
    target_root = Path(target_root).expanduser().resolve()
    manifest_errors = validate_manifest(manifest, package_root)
    if manifest_errors:
        raise InstallError('; '.join(manifest_errors))
    if document_status.state != 'ready':
        raise InstallError(f'Document profile not ready: {document_status.state}')

    expected_hashes = payload_hashes(package_root, manifest)
    with nullcontext() if dry_run else _target_lock(target_root):
        had_target = target_root.exists()
        stale_owned: set[str] = set()
        if had_target:
            _, stale_owned = _upgrade_ownership(target_root, expected_hashes)

        if dry_run:
            return {
                'state': 'dry-run',
                'target': str(target_root),
                'payload_files': sorted(expected_hashes),
                'stale_owned_files': sorted(stale_owned),
                'document_profile': document_profile,
            }

        parent = target_root.parent
        parent.mkdir(parents=True, exist_ok=True)
        token = uuid.uuid4().hex
        stage = parent / f'.{target_root.name}.stage-{token}'
        backup = parent / f'.{target_root.name}.backup-{token}'
        replaced = False

        def inject(point: str) -> None:
            if failure_injector is not None:
                failure_injector(point)

        try:
            if had_target:
                shutil.copytree(target_root, stage)
                _prune_owned_files(stage, stale_owned)
            else:
                stage.mkdir()
            _copy_payload(package_root, stage, manifest)
            staged_errors = verify_installed(stage, expected_hashes)
            if staged_errors:
                raise InstallError('; '.join(staged_errors))
            inject('after-stage')

            if had_target:
                os.replace(target_root, backup)
                inject('after-backup')
            os.replace(stage, target_root)
            replaced = True
            inject('after-replace')

            installed_errors = verify_installed(target_root, expected_hashes)
            if installed_errors:
                raise InstallError('; '.join(installed_errors))
            inject('after-verify')

            discovery_evidence = ()
            if discovery_verifier is not None:
                discovery = discovery_verifier(manifest['skill']['name'])
                discovery_state = discovery.state
                discovery_evidence = tuple(getattr(discovery, 'evidence', ()))
                if discovery_state not in {'verified', 'not-available'}:
                    raise InstallError(f'host discovery verification failed: {discovery_state}: {discovery_evidence}')

            receipt = {
                'skill': manifest['skill']['name'],
                'version': (package_root / 'VERSION').read_text(encoding='utf-8').strip(),
                'target': target_name,
                'scope': scope,
                'installed_root': str(target_root),
                'runtime_profile': runtime_profile,
                'document_profile': document_profile,
                'document_status': asdict(document_status),
                'host_discovery': {'state': discovery_state, 'evidence': list(discovery_evidence)},
                'payload_hashes': expected_hashes,
                'installed_at': datetime.now(timezone.utc).isoformat(),
            }
            receipt_path = target_root / '.install-receipt.json'
            receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n', encoding='utf-8')
            inject('after-receipt')

            _remove_tree(backup)
            return {'state': 'installed', 'target': str(target_root), 'receipt': receipt}
        except Exception as exc:
            try:
                _remove_tree(stage)
                if replaced:
                    _remove_tree(target_root)
                if backup.exists():
                    os.replace(backup, target_root)
            except Exception as rollback_exc:
                raise InstallError(f'{exc}; rollback failed: {rollback_exc}') from rollback_exc
            if isinstance(exc, InstallError):
                raise
            raise InstallError(str(exc)) from exc
        finally:
            _remove_tree(stage)
            if backup.exists() and target_root.exists():
                _remove_tree(backup)


def verify_installation(target_root: Path) -> dict:
    target = Path(target_root).expanduser().resolve()
    predicates = {
        'canonical_root': False,
        'receipt_written': False,
        'payload_hashes_match': False,
        'document_profile_resolved': False,
        'runtime_document_profile_consistent': False,
        'receipt_matches_installed_root': False,
        'host_discovery_verified_or_explicitly_not_available': False,
        'no_staging_leftovers': False,
        'no_backup_leftovers': False,
    }
    violations: list[str] = []

    predicates['canonical_root'] = (target / 'SKILL.md').is_file() and not (target / target.name / 'SKILL.md').exists()
    if not predicates['canonical_root']:
        violations.append('canonical SKILL.md missing or nested incorrectly')

    receipt_path = target / '.install-receipt.json'
    if not receipt_path.is_file():
        violations.append('installation receipt missing')
        return {'passed': False, 'predicates': predicates, 'violations': violations}

    predicates['receipt_written'] = True
    try:
        receipt = json.loads(receipt_path.read_text(encoding='utf-8'))
    except Exception as exc:
        violations.append(f'invalid receipt: {exc}')
        return {'passed': False, 'predicates': predicates, 'violations': violations}

    hash_ok = True
    owned = receipt.get('payload_hashes') or {}
    if not isinstance(owned, dict) or not owned:
        hash_ok = False
        violations.append('receipt has no managed payload ownership record')
        owned = {}
    for rel, expected in owned.items():
        try:
            path = _managed_path(target, rel)
        except InstallError as exc:
            hash_ok = False
            violations.append(str(exc))
            continue
        if not path.is_file() or _sha256(path) != expected:
            hash_ok = False
            violations.append(f'payload hash mismatch or missing: {rel}')
    predicates['payload_hashes_match'] = hash_ok and bool(owned)

    predicates['document_profile_resolved'] = receipt.get('document_status', {}).get('state') == 'ready' and bool(receipt.get('document_profile'))
    if not predicates['document_profile_resolved']:
        violations.append('document profile is not resolved')

    runtime_profile = receipt.get('runtime_profile')
    document_profile = receipt.get('document_profile')
    predicates['runtime_document_profile_consistent'] = not (document_profile == 'oai-native' and runtime_profile != 'oai-native')
    if not predicates['runtime_document_profile_consistent']:
        violations.append(f'inconsistent runtime/document profiles: {runtime_profile!r} with {document_profile!r}')

    predicates['receipt_matches_installed_root'] = receipt.get('installed_root') == str(target)
    if not predicates['receipt_matches_installed_root']:
        violations.append('receipt installed_root does not match verified target')

    discovery = receipt.get('host_discovery', {}).get('state')
    predicates['host_discovery_verified_or_explicitly_not_available'] = discovery in {'verified', 'not-available'}
    if not predicates['host_discovery_verified_or_explicitly_not_available']:
        violations.append(f'host discovery state is not acceptable: {discovery!r}')

    parent = target.parent
    predicates['no_staging_leftovers'] = not any(parent.glob(f'.{target.name}.stage-*'))
    predicates['no_backup_leftovers'] = not any(parent.glob(f'.{target.name}.backup-*'))
    if not predicates['no_staging_leftovers']:
        violations.append('staging leftovers remain')
    if not predicates['no_backup_leftovers']:
        violations.append('backup leftovers remain')

    return {
        'passed': all(predicates.values()),
        'predicates': predicates,
        'violations': violations,
    }


def uninstall_skill(target_root: Path, *, force: bool = False) -> dict:
    target = Path(target_root).expanduser().resolve()
    with _target_lock(target):
        receipt_path = target / '.install-receipt.json'
        if not receipt_path.is_file():
            raise InstallError('installation receipt missing; refusing unmanaged uninstall')
        receipt = json.loads(receipt_path.read_text(encoding='utf-8'))
        owned = receipt.get('payload_hashes') or {}
        if not isinstance(owned, dict) or not owned:
            raise InstallError('installation receipt has no managed payload ownership record')

        modified: list[str] = []
        for rel, expected in owned.items():
            path = _managed_path(target, rel)
            if path.is_file() and _sha256(path) != expected:
                modified.append(rel)
        if modified and not force:
            raise InstallError('modified owned files: ' + ', '.join(sorted(modified)))

        removed: list[str] = []
        for rel in sorted(owned, key=lambda x: len(Path(x).parts), reverse=True):
            path = _managed_path(target, rel)
            if path.is_file():
                path.unlink()
                removed.append(rel)

        if receipt_path.exists():
            receipt_path.unlink()

        for path in sorted((p for p in target.rglob('*') if p.is_dir()), key=lambda p: len(p.parts), reverse=True):
            try:
                path.rmdir()
            except OSError:
                pass
        try:
            target.rmdir()
        except OSError:
            pass

        return {'state': 'uninstalled', 'removed': removed, 'preserved_root': target.exists()}
