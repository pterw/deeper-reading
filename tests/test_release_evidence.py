from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_installer_usage_matches_sovereign_standalone_contract():
    body = read("installer/USAGE.md")
    lower = body.lower()
    assert "--superpowers" not in body
    assert "superpowers is a separate prerequisite" not in lower
    assert "portable-openai" not in lower
    assert "standalone" in lower
    assert "bundled extractors" in lower
    assert "oai-native" in lower and "optional" in lower


def test_audit_describes_current_hard_standalone_payload_and_prefreeze_gate():
    body = read("AUDIT.md")
    lower = body.lower()
    assert "189/189" in body
    assert "scripts/extract_pdf.py" in body
    assert "scripts/extract_docx.py" in body
    assert "scripts/extract_html.py" in body
    assert "scripts/extract_markdown.py" in body
    assert "skills/exhaustive-document-traversal/SKILL.md" in body
    assert "skills/verifying-exhaustive-traversal/SKILL.md" in body
    assert "standalone" in lower
    assert "no required superpowers" in lower or "no superpowers runtime prerequisite" in lower


def test_mutation_report_covers_anti_skimming_and_process_threat_models():
    body = read("MUTATION_REPORT.md")
    lower = body.lower()
    assert "12 emitted" in lower
    assert "4 evidenced" in lower
    assert "skipped middle" in lower
    assert "early done" in lower
    assert "forged smaller manifest" in lower
    assert "source re-extraction" in lower
    assert "process mutation" in lower
    assert "11/11" in body


def test_smoke_report_matches_current_sovereign_generic_smoke():
    body = read("docs/installer-smoke-report.md")
    lower = body.lower()
    assert "can_install" in lower and "true" in lower
    for name in ("extract_pdf.py", "extract_docx.py", "extract_html.py", "extract_markdown.py"):
        assert name in body
    assert "install" in lower and "verify" in lower and "uninstall" in lower
    assert "superpowers prerequisite" not in lower
    assert "target absent" in lower
