from __future__ import annotations

import inspect
import json
from pathlib import Path

from installer import core

ROOT = Path(__file__).resolve().parents[1]

RUNTIME_TEXT_FILES = [
    ROOT / "SKILL.md",
    ROOT / "README.md",
    *sorted((ROOT / "references").glob("*.md")),
    ROOT / "scripts" / "verify_run.py",
]


def test_runtime_payload_does_not_require_external_process_framework():
    offenders = []
    needles = ("Superpowers", "superpowers:", "@Superpowers")
    for path in RUNTIME_TEXT_FILES:
        text = path.read_text(encoding="utf-8")
        if any(needle in text for needle in needles):
            offenders.append(path.relative_to(ROOT).as_posix())
    assert offenders == [], offenders


def test_manifest_has_no_required_superpowers_prerequisite():
    manifest = json.loads((ROOT / "MANIFEST.json").read_text(encoding="utf-8"))
    superpowers = manifest.get("prerequisites", {}).get("superpowers")
    assert not (isinstance(superpowers, dict) and superpowers.get("required") is True)


def test_root_compatibility_does_not_require_external_process_framework():
    skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    frontmatter = skill.split("---", 2)[1]
    assert "Superpowers" not in frontmatter


def test_installer_basic_path_has_no_superpowers_parameter():
    signature = inspect.signature(core.install_skill)
    assert "superpowers" not in signature.parameters


def test_verifier_rejects_legacy_superpowers_preflight_keys():
    text = (ROOT / "scripts" / "verify_run.py").read_text(encoding="utf-8")
    required_block = text.split("REQUIRED_PREFLIGHT = (", 1)[1].split(")", 1)[0]
    for key in (
        "using_superpowers_read",
        "superpowers_list_consumed",
        "applicable_skills_read",
        "live_dependencies_read",
    ):
        assert key not in required_block
    assert "legacy preflight key is not allowed" in text


def test_verifier_uses_package_native_process_vocabulary():
    text = (ROOT / "scripts" / "verify_run.py").read_text(encoding="utf-8")
    for token in ("failure_diagnosed", "architecture_stop", "alternative_designed", "plan_revised"):
        assert token in text
    assert "legacy process event is not allowed" in text
