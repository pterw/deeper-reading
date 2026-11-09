"""Shared helpers for the media tests: golden sources, the one normaliser, golden reads."""

import hashlib
import json
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = ROOT / "skills" / "deeper-reading"
SCRIPTS = SKILL_ROOT / "scripts"
GOLDEN = ROOT / "tests" / "golden_no_media"
GOLDEN_MAX_BYTES = 90

_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"

# One no-media source per format. Bytes are fixed so the source sha is stable on every OS.
GOLDEN_SOURCES = {
    "md": (
        "source.md",
        "# Intro\n\nAlpha paragraph with enough words to need a second chunk when packed small.\n\n"
        "| Name | Value |\n| --- | --- |\n| alpha | 1 |\n\n"
        "```python\nprint('alpha')\n```\n\n## Tail\n\nOmega `code` paragraph.\n",
    ),
    "html": (
        "source.html",
        "<h1>Intro</h1><p>Alpha paragraph with enough words to need a second chunk when packed small.</p>"
        "<table><tr><td>alpha</td><td>1</td></tr></table><pre>print('alpha')</pre>"
        "<script>var skipped = 1;</script><h2>Tail</h2><p>Omega paragraph.</p>\n",
    ),
}


def _run(text: str) -> str:
    return f'<w:r><w:t xml:space="preserve">{text}</w:t></w:r>'


def write_zip_member(zf: zipfile.ZipFile, name: str, data: str) -> None:
    """Write one stored member with every header field that varies by platform pinned.

    ZipInfo defaults create_system to 0 on win32 and 3 elsewhere, and external_attr to 0, so
    an unpinned zip has a different sha256 per OS. Stored (not deflated) keeps it independent
    of the zlib build."""
    info = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
    info.create_system = 3
    info.external_attr = 0o600 << 16
    info.compress_type = zipfile.ZIP_STORED
    zf.writestr(info, data)


def docx_document_xml() -> str:
    body = (
        f'<w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr>{_run("Intro")}</w:p>'
        f"<w:p>{_run('Alpha paragraph with enough words to need a second chunk when packed small. ')}"
        '<w:del w:id="1"><w:r><w:delText>$100</w:delText></w:r></w:del>'
        '<w:ins w:id="2"><w:r><w:t>$200</w:t></w:r></w:ins></w:p>'
        f"<w:p>{_run('Omega paragraph.')}</w:p>"
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<w:document xmlns:w="{_W}"><w:body>{body}</w:body></w:document>'
    )


def write_docx_source(path: Path) -> None:
    """A no-media DOCX with an O7 tracked change, byte-identical on every platform."""
    with zipfile.ZipFile(path, "w") as zf:
        write_zip_member(zf, "word/document.xml", docx_document_xml())


def write_golden_source(fmt: str, directory: Path) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    if fmt == "docx":
        path = directory / "source.docx"
        write_docx_source(path)
        return path
    name, text = GOLDEN_SOURCES[fmt]
    path = directory / name
    path.write_bytes(text.encode("utf-8"))
    return path


def extract_manifest_text(fmt: str, source: Path, out: Path, max_bytes: int = GOLDEN_MAX_BYTES) -> str:
    """Run the extractor and return the manifest file it wrote, as text."""
    script = {"md": "extract_markdown.py", "html": "extract_html.py", "docx": "extract_docx.py"}[fmt]
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / script), str(source), "--out", str(out), "--max-bytes", str(max_bytes)],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return out.read_text(encoding="utf-8")


def manifest_text(manifest: dict) -> str:
    return json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"


def normalise(manifest: dict, ledger: dict | None = None):
    """The one golden-comparison normaliser: fix source.path and source.uri, and rebind the
    ledger's manifest_sha256 to the normalised manifest. Nothing else changes."""
    fixed = json.loads(json.dumps(manifest))
    fixed["source"]["path"] = "/golden/source"
    fixed["source"]["uri"] = "file:///golden/source"
    if ledger is None:
        return fixed
    rebound = json.loads(json.dumps(ledger))
    rebound["manifest_sha256"] = hashlib.sha256(manifest_text(fixed).encode("utf-8")).hexdigest()
    return fixed, rebound


def read_golden(name: str) -> str:
    # read_text, not read_bytes: Windows checkouts may apply autocrlf to the golden files.
    return (GOLDEN / name).read_text(encoding="utf-8")
