from __future__ import annotations

import inspect
import json
from pathlib import Path

from installer import core, install
from installer.prerequisites import document_profile_status

ROOT = Path(__file__).resolve().parents[1]


def test_manifest_makes_standalone_canonical_without_external_process_prerequisite():
    manifest = json.loads((ROOT / "MANIFEST.json").read_text(encoding="utf-8"))
    assert "superpowers" not in manifest.get("prerequisites", {})
    assert set(manifest["document_profiles"]) == {"standalone", "oai-native"}
    assert "skills" in manifest["payload"]


def test_install_skill_has_no_external_process_parameter():
    signature = inspect.signature(core.install_skill)
    assert "superpowers" not in signature.parameters


def test_installation_dod_has_no_external_process_predicate():
    text = inspect.getsource(core.verify_installation)
    assert "superpowers_ready" not in text
    assert "Superpowers prerequisite" not in text


def test_installer_cli_has_no_superpowers_flag_and_defaults_to_standalone():
    parser = install.build_parser()
    args = parser.parse_args(["install", "--dry-run"])
    assert not hasattr(args, "superpowers")
    assert args.document_profile == "standalone"


def test_standalone_document_profile_uses_bundled_extractors():
    status = document_profile_status("standalone", package_root=ROOT)
    assert status.state == "ready"
    assert any("extract_pdf.py" in item for item in status.evidence)
    assert any("extract_docx.py" in item for item in status.evidence)
    assert any("extract_html.py" in item for item in status.evidence)
    assert any("extract_markdown.py" in item for item in status.evidence)


def test_oai_native_remains_optional_enhancement():
    text = (ROOT / "references" / "runtime-profiles.md").read_text(encoding="utf-8")
    assert "## standalone" in text
    assert "canonical" in text.lower()
    assert "## oai-native" in text
    assert "optional" in text.lower()
