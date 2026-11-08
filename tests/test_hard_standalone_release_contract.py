from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

RUNTIME_TEXT_FILES = [
    ROOT / "SKILL.md",
    ROOT / "README.md",
    ROOT / "installer" / "USAGE.md",
    *sorted((ROOT / "references").glob("*.md")),
    *sorted((ROOT / "skills").glob("*/SKILL.md")),
    ROOT / "scripts" / "verify_run.py",
]


def test_runtime_payload_does_not_require_external_process_framework():
    for pattern in ("references/*.md", "skills/*/SKILL.md"):
        assert list(ROOT.glob(pattern)), f"{pattern} matches no file"
    offenders = []
    for path in RUNTIME_TEXT_FILES:
        if "superpowers" in path.read_text(encoding="utf-8").lower():
            offenders.append(path.relative_to(ROOT).as_posix())
    assert offenders == [], offenders


def test_scripts_do_not_import_from_tests():
    scripts = sorted((ROOT / "scripts").rglob("*.py"))
    assert scripts, "scripts/ matches no .py file"
    pattern = re.compile(r"^\s*(from|import)\s+tests\b", re.MULTILINE)
    offenders = [
        path.relative_to(ROOT).as_posix()
        for path in scripts
        if pattern.search(path.read_text(encoding="utf-8"))
    ]
    assert offenders == [], offenders


def test_verifier_uses_package_native_process_vocabulary():
    text = (ROOT / "scripts" / "verify_run.py").read_text(encoding="utf-8")
    for token in ("failure_diagnosed", "architecture_stop", "alternative_designed", "plan_revised"):
        assert token in text
