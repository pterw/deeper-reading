#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

from installer.adapters import detect_target, get_adapter
from installer.core import InstallError, install_skill, uninstall_skill, verify_installation
from installer.manifest import load_manifest
from installer.prerequisites import document_profile_status


def _target_name(value: str) -> str:
    return detect_target() if value == "auto" else value


def _target_root(adapter, scope: str, project_dir: str | None) -> Path:
    project = Path(project_dir).resolve() if project_dir else (Path.cwd().resolve() if scope == "project" else None)
    return adapter.resolve_skill_root(scope, project)


def _document_status(profile: str):
    return document_profile_status(profile, package_root=PACKAGE_ROOT)


def _emit(data: dict, as_json: bool) -> None:
    if as_json:
        print(json.dumps(data, indent=2, sort_keys=True))
        return
    for key, value in data.items():
        print(f"{key}: {value}")


def command_doctor(args) -> int:
    target_name = _target_name(args.target)
    adapter = get_adapter(target_name)
    target_root = _target_root(adapter, args.scope, args.project_dir)
    doc = _document_status(args.document_profile)
    data = {
        "command": "doctor",
        "target": target_name,
        "scope": args.scope,
        "target_root": str(target_root),
        "runtime_detected": adapter.detect(),
        "document_profile": args.document_profile,
        "document_status": {"state": doc.state, "evidence": list(doc.evidence), "action": list(doc.action)},
        "can_install": doc.state == "ready",
        "mutation_performed": False,
    }
    _emit(data, args.json)
    return 0


def command_verify(args) -> int:
    target_name = _target_name(args.target)
    adapter = get_adapter(target_name)
    target_root = _target_root(adapter, args.scope, args.project_dir)
    if not target_root.exists():
        data = {"passed": False, "target": target_name, "target_root": str(target_root), "violations": ["installation target missing"]}
        _emit(data, args.json)
        return 2
    result = verify_installation(target_root)
    result.update({"target": target_name, "target_root": str(target_root)})
    if result.get("passed"):
        receipt = json.loads((target_root / ".install-receipt.json").read_text(encoding="utf-8"))
        current_doc = _document_status(receipt.get("document_profile", "standalone"))
        if current_doc.state != "ready":
            result["passed"] = False
            result["violations"].append(f"fresh document profile check failed: {current_doc.state}")
    _emit(result, args.json)
    return 0 if result.get("passed") else 2


def command_install(args) -> int:
    target_name = _target_name(args.target)
    adapter = get_adapter(target_name)
    target_root = _target_root(adapter, args.scope, args.project_dir)
    profile = args.document_profile
    doc = _document_status(profile)

    if doc.state != "ready":
        data = {
            "state": "blocked",
            "target": target_name,
            "target_root": str(target_root),
            "document_profile": profile,
            "document_status": {"state": doc.state, "evidence": list(doc.evidence), "action": list(doc.action)},
            "mutation_performed": False,
        }
        _emit(data, args.json)
        return 2

    try:
        result = install_skill(
            PACKAGE_ROOT,
            target_root,
            load_manifest(PACKAGE_ROOT / "MANIFEST.json"),
            target_name=target_name,
            scope=args.scope,
            runtime_profile="oai-native" if profile == "oai-native" else "standalone",
            document_profile=profile,
            document_status=doc,
            discovery_verifier=None if args.dry_run else adapter.discovery_verify,
            dry_run=args.dry_run,
        )
    except InstallError as exc:
        _emit({"state": "failed", "error": str(exc), "target": target_name, "target_root": str(target_root)}, args.json)
        return 2
    _emit(result, args.json)
    return 0


def command_uninstall(args) -> int:
    target_name = _target_name(args.target)
    adapter = get_adapter(target_name)
    target_root = _target_root(adapter, args.scope, args.project_dir)
    try:
        result = uninstall_skill(target_root, force=args.force)
    except InstallError as exc:
        _emit({"state": "failed", "error": str(exc), "target_root": str(target_root)}, args.json)
        return 2
    _emit(result, args.json)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="deeper-reading-installer")
    sub = parser.add_subparsers(dest="command", required=True)

    def common(p):
        p.add_argument("--target", choices=["auto", "generic-agents", "copilot", "codex", "gemini", "claude"], default="auto")
        p.add_argument("--scope", choices=["user", "project"], default="user")
        p.add_argument("--project-dir")
        p.add_argument("--document-profile", choices=["standalone", "oai-native"], default="standalone")
        p.add_argument("--json", action="store_true")

    p = sub.add_parser("doctor")
    common(p)
    p.set_defaults(func=command_doctor)

    p = sub.add_parser("verify")
    common(p)
    p.set_defaults(func=command_verify)

    p = sub.add_parser("install")
    common(p)
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=command_install)

    p = sub.add_parser("uninstall")
    common(p)
    p.add_argument("--force", action="store_true")
    p.set_defaults(func=command_uninstall)
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
