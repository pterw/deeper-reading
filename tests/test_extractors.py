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


def test_markdown_extractor_tracks_h1_through_h6(tmp_path):
    source = tmp_path / "deep.md"
    source.write_text(
        "# A\n## B\n### C\n#### D\n##### E\n###### F\nDeep proof.\n",
        encoding="utf-8",
    )
    manifest = run_extractor("extract_markdown.py", source, tmp_path / "deep.json")
    assert any(c["locator"].get("heading_path") == ["A", "B", "C", "D", "E", "F"] for c in manifest["chunks"])


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


def test_html_extractor_keeps_generic_visible_dom_text_once(tmp_path):
    source = tmp_path / "generic.html"
    source.write_text(
        "<main>Lead text<div>Visible div prose.</div>"
        "<section><span>Section inline text.</span></section>Tail text</main>",
        encoding="utf-8",
    )
    manifest = run_extractor("extract_html.py", source, tmp_path / "generic.json")
    text = "".join(c["content"] for c in manifest["chunks"])
    for expected in ["Lead text", "Visible div prose.", "Section inline text.", "Tail text"]:
        assert text.count(expected) == 1


def test_html_extractor_tracks_h1_through_h6(tmp_path):
    source = tmp_path / "headings.html"
    source.write_text(
        "<h1>A</h1><h2>B</h2><h3>C</h3><h4>D</h4><h5>E</h5><h6>F</h6><p>Proof.</p>",
        encoding="utf-8",
    )
    manifest = run_extractor("extract_html.py", source, tmp_path / "h.json")
    assert any(c["locator"].get("heading_path") == ["A", "B", "C", "D", "E", "F"] for c in manifest["chunks"])


def test_html_extractor_keeps_visible_text_once_and_excludes_skipped_content(tmp_path):
    source = tmp_path / "mixed.html"
    source.write_text(
        "<body><h1>Root</h1>Body lead"
        "<div>Div text <span>inline span</span></div>"
        "<section>Section text</section><article>Article text</article>"
        "<ul><li>List item</li></ul>"
        "<table><tr><td>Table cell</td></tr></table>"
        "<pre>Pre literal</pre>"
        "<script>script hidden</script><style>style hidden</style>"
        "<noscript>noscript hidden</noscript><template>template hidden</template>"
        "Tail text</body>",
        encoding="utf-8",
    )
    manifest = run_extractor("extract_html.py", source, tmp_path / "mixed.json")
    text = "".join(c["content"] for c in manifest["chunks"])
    for expected in [
        "Body lead", "Div text", "inline span", "Section text", "Article text",
        "List item", "Table cell", "Pre literal", "Tail text",
    ]:
        assert text.count(expected) == 1
    for excluded in ["script hidden", "style hidden", "noscript hidden", "template hidden"]:
        assert excluded not in text


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


def _write_deep_heading_docx(path: Path) -> None:
    ns = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    headings = "".join(
        f'<w:p><w:pPr><w:pStyle w:val="Heading{level}"/></w:pPr>'
        f'<w:r><w:t>H{level}</w:t></w:r></w:p>'
        for level in range(1, 7)
    )
    document = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<w:document xmlns:w="{ns}"><w:body>'
        + headings
        + '<w:p><w:r><w:t>Deep body.</w:t></w:r></w:p>'
        + '</w:body></w:document>'
    )
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("word/document.xml", document)


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


def test_docx_extractor_tracks_heading1_through_heading6(tmp_path):
    source = tmp_path / "deep.docx"
    _write_deep_heading_docx(source)
    manifest = run_extractor("extract_docx.py", source, tmp_path / "deep-docx.json")
    assert any(
        c["locator"].get("heading_path") == ["H1", "H2", "H3", "H4", "H5", "H6"]
        for c in manifest["chunks"]
        if "Deep body." in c["content"]
    )


def test_pdf_extractor_reads_every_page_with_portable_backend(tmp_path):
    sys.path.insert(0, str(SCRIPTS))
    from extract_pdf import choose_backend
    try:
        backend = choose_backend('auto')
    except RuntimeError:
        pytest.skip('no PDF text backend installed; PDF extraction untested on this machine')
    source = ROOT / 'tests/fixtures/pdf-first-run/source/sample.pdf'
    manifest = run_extractor('extract_pdf.py', source, tmp_path / 'pdf.json', '--backend', backend)
    assert_manifest_integrity(manifest, source, 'pdf')
    assert [c['locator']['pages'] for c in manifest['chunks']] == [[1], [2], [3]]
    assert manifest['chunks'][1]['content'] == ''
    assert 'Page One Alpha' in manifest['chunks'][0]['content']
    assert 'Page Three Omega' in manifest['chunks'][2]['content']
