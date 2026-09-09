import hashlib
import json
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


def run_extractor(name: str, source: Path, out: Path, *extra: str) -> dict:
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / name), str(source), "--out", str(out), *extra],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert out.is_file(), result.stdout + result.stderr
    return json.loads(out.read_text(encoding="utf-8"))


def assert_manifest_integrity(manifest: dict, source: Path, fmt: str) -> None:
    assert manifest["schema_version"] == 1
    assert manifest["source"]["format"] == fmt
    assert manifest["source"]["sha256"] == hashlib.sha256(source.read_bytes()).hexdigest()
    assert manifest["chunking"]["chunk_count"] == len(manifest["chunks"])
    cursor = 0
    seen = set()
    stream = bytearray()
    for ordinal, chunk in enumerate(manifest["chunks"], start=1):
        assert chunk["ordinal"] == ordinal
        assert chunk["id"] not in seen
        seen.add(chunk["id"])
        content = chunk["content"]
        raw = content.encode("utf-8")
        assert chunk["content_sha256"] == hashlib.sha256(raw).hexdigest()
        assert chunk["text_byte_start"] == cursor
        cursor += len(raw)
        assert chunk["text_byte_end"] == cursor
        stream.extend(raw)
    assert manifest["extracted_text_bytes"] == cursor
    assert manifest["extracted_text_sha256"] == hashlib.sha256(bytes(stream)).hexdigest()


def test_markdown_extractor_is_deterministic_and_keeps_fences_tables_atomic(tmp_path):
    source = tmp_path / "long.md"
    source.write_text(
        "# Intro\n\nAlpha paragraph with enough words to form content.\n\n"
        "## Details\n\n"
        "| Name | Value |\n| --- | --- |\n| alpha | 1 |\n| beta | 2 |\n\n"
        "```python\n# this is code, not a heading\nprint('alpha')\nprint('beta')\n```\n\n"
        "### Tail\n\nOmega paragraph.\n",
        encoding="utf-8",
    )
    a = run_extractor("extract_markdown.py", source, tmp_path / "a.json", "--max-bytes", "70")
    b = run_extractor("extract_markdown.py", source, tmp_path / "b.json", "--max-bytes", "70")
    assert a == b
    assert_manifest_integrity(a, source, "markdown")

    contents = [c["content"] for c in a["chunks"]]
    full_table = "| Name | Value |\n| --- | --- |\n| alpha | 1 |\n| beta | 2 |"
    full_fence = "```python\n# this is code, not a heading\nprint('alpha')\nprint('beta')\n```"
    assert sum(full_table in content for content in contents) == 1
    assert sum(full_fence in content for content in contents) == 1
    assert any(c.get("oversize_atomic") for c in a["chunks"] if full_fence in c["content"])
    assert any("Tail" in c.get("locator", {}).get("heading_path", []) for c in a["chunks"])


def test_html_extractor_uses_structure_and_omits_script_style(tmp_path):
    source = tmp_path / "source.html"
    source.write_text(
        "<html><head><style>.x{display:none}</style><script>bad()</script></head>"
        "<body><h1>Intro</h1><p>Alpha text.</p><h2>Data</h2>"
        "<table><tr><th>A</th><th>B</th></tr><tr><td>1</td><td>2</td></tr></table>"
        "<pre><code># literal code heading\nprint(1)</code></pre></body></html>",
        encoding="utf-8",
    )
    manifest = run_extractor("extract_html.py", source, tmp_path / "html.json", "--max-bytes", "80")
    assert_manifest_integrity(manifest, source, "html")
    text = "".join(c["content"] for c in manifest["chunks"])
    assert "Alpha text." in text
    assert "A" in text and "B" in text and "1" in text and "2" in text
    assert "literal code heading" in text
    assert "bad()" not in text
    assert "display:none" not in text


def _write_minimal_docx(path: Path) -> None:
    ns = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    document = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<w:document xmlns:w="{ns}"><w:body>'
        '<w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>Body Heading</w:t></w:r></w:p>'
        '<w:p><w:r><w:t>Body paragraph.</w:t></w:r></w:p>'
        '<w:tbl><w:tr><w:tc><w:p><w:r><w:t>Cell A</w:t></w:r></w:p></w:tc>'
        '<w:tc><w:p><w:r><w:t>Cell B</w:t></w:r></w:p></w:tc></w:tr></w:tbl>'
        '</w:body></w:document>'
    )
    header = f'<w:hdr xmlns:w="{ns}"><w:p><w:r><w:t>Header text</w:t></w:r></w:p></w:hdr>'
    comments = f'<w:comments xmlns:w="{ns}"><w:comment w:id="0"><w:p><w:r><w:t>Reviewer note</w:t></w:r></w:p></w:comment></w:comments>'
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("word/document.xml", document)
        zf.writestr("word/header1.xml", header)
        zf.writestr("word/comments.xml", comments)


def test_docx_extractor_reads_story_parts_without_oai_paths(tmp_path):
    source = tmp_path / "source.docx"
    _write_minimal_docx(source)
    manifest = run_extractor("extract_docx.py", source, tmp_path / "docx.json", "--max-bytes", "80")
    assert_manifest_integrity(manifest, source, "docx")
    text = "".join(c["content"] for c in manifest["chunks"])
    for expected in ["Body Heading", "Body paragraph.", "Cell A", "Cell B", "Header text", "Reviewer note"]:
        assert expected in text
    locators = json.dumps([c["locator"] for c in manifest["chunks"]])
    assert "word/document.xml" in locators
    assert "word/header1.xml" in locators
    assert "word/comments.xml" in locators


def test_pdf_extractor_reads_every_page_with_portable_backend(tmp_path):
    reportlab = pytest.importorskip("reportlab.pdfgen.canvas")
    source = tmp_path / "source.pdf"
    canvas = reportlab.Canvas(str(source))
    canvas.drawString(72, 720, "Page One Alpha")
    canvas.showPage()
    canvas.drawString(72, 720, "Page Two Omega")
    canvas.save()

    manifest = run_extractor(
        "extract_pdf.py", source, tmp_path / "pdf.json", "--max-bytes", "80", "--backend", "pypdf"
    )
    assert_manifest_integrity(manifest, source, "pdf")
    text = "".join(c["content"] for c in manifest["chunks"])
    assert "Page One Alpha" in text
    assert "Page Two Omega" in text
    pages = {p for c in manifest["chunks"] for p in c["locator"].get("pages", [])}
    assert pages == {1, 2}
    assert "/home/oai/skills" not in (SCRIPTS / "extract_pdf.py").read_text(encoding="utf-8")
