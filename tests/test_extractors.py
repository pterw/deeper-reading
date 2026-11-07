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


@pytest.mark.parametrize(
    ("text", "kinds", "last_heading_path"),
    [
        pytest.param(
            "```\ncode\n```js\nmore code\n```\nafter\n",
            ["fenced_code", "text"],
            None,
            id="fence-ignores-info-string-closer",
        ),
        pytest.param(
            "````\na\n```\nmore code\n````\nafter\n",
            ["fenced_code", "text"],
            None,
            id="fence-ignores-shorter-closer",
        ),
        pytest.param(
            "```\na\n~~~\nmore code\n```\nafter\n",
            ["fenced_code", "text"],
            None,
            id="fence-ignores-other-marker-closer",
        ),
        pytest.param("| a |\n|-|\n| 1 |\n", ["table"], None, id="one-column-short-dash-table"),
        pytest.param("| a | b |\n|-|-|\n| 1 | 2 |\n", ["table"], None, id="later-column-short-dash-table"),
        pytest.param("| a | b |\n|--|--|\n| 1 | 2 |\n", ["table"], None, id="two-dash-table"),
        pytest.param("a|b\n---\n", ["text"], None, id="pipe-line-over-thematic-break"),
        pytest.param("## Using C#\n", ["text"], ["Using C#"], id="heading-keeps-title-hash"),
        pytest.param("## Title ##\n", ["text"], ["Title"], id="heading-drops-closing-run"),
    ],
)
def test_markdown_blocks_follow_commonmark_boundaries(tmp_path, text, kinds, last_heading_path):
    source = tmp_path / "case.md"
    source.write_text(text, encoding="utf-8")
    manifest = run_extractor("extract_markdown.py", source, tmp_path / "case.json", "--max-bytes", "12")
    locators = [c["locator"] for c in manifest["chunks"]]
    assert [loc.get("kind", "text") for loc in locators] == kinds
    if kinds == ["fenced_code", "text"]:
        assert "more code" in manifest["chunks"][0]["content"]
        assert manifest["chunks"][1]["content"].strip() == "after"
    if last_heading_path is not None:
        assert locators[-1]["heading_path"] == last_heading_path


def test_markdown_atomic_blocks_end_with_newline_so_stream_never_glues(tmp_path):
    source = tmp_path / "glue.md"
    source.write_text("```\ncode\n```\n| a |\n|---|\n| 1 |\n# Head\n", encoding="utf-8")
    manifest = run_extractor("extract_markdown.py", source, tmp_path / "glue.json")
    assert_manifest_integrity(manifest, source, "markdown")
    stream = "".join(c["content"] for c in manifest["chunks"])
    assert stream.splitlines() == ["```", "code", "```", "| a |", "|---|", "| 1 |", "# Head"]


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


def assert_chunk_words_are_exactly(manifest: dict, expected: list[str]) -> None:
    words = "".join(c["content"] for c in manifest["chunks"]).split()
    assert words == [w for phrase in expected for w in phrase.split()]


@pytest.mark.parametrize(
    ("html", "expected", "heading_path"),
    [
        ("<h1>Only title unclosed<p>All the body text</p>", ["Only title unclosed", "All the body text"], None),
        ("<h1>Alpha intro<h2>Beta</h2><p>Body</p>", ["Alpha intro", "Beta", "Body"], None),
        ("<h3>Closed with wrong</h4><p>b</p>", ["Closed with wrong", "b"], None),
        ("<div><h1>T</div>text", ["T", "text"], ["T"]),
        ("<h1><div>Title</div></h1><p>b</p>", ["Title", "b"], ["Title"]),
        ("<table><caption>Cap</caption><tr><td>a<td>b</tr></table>", ["Cap", "a", "b"], None),
        ("<table><tr><td>one <b>two</b> three</td></tr></table>", ["one two three"], None),
        ("<p>line one<br>line two</p>", ["line one", "line two"], None),
        ("<h1>Ti<br>tle</h1>", ["Ti tle"], None),
        ("<details><summary>Sum</summary>Detail text</details>", ["Sum", "Detail", "text"], None),
        ("<div>a<hr>b</div>", ["a", "b"], None),
        ("<form>Name<input>Value</form>", ["Name", "Value"], None),
        ("<p>A<span>B</span></p>", ["AB"], None),
        ("<p>The<wbr>word</p>", ["Theword"], None),
        ("<h1>Only title at eof", ["Only title at eof"], ["Only title at eof"]),
        ("<h3>Closed with wrong</h4>trailing", ["Closed with wrong", "trailing"], ["Closed with wrong"]),
        ("<h1> <div>Title</div></h1>", ["Title"], ["Title"]),
        ("<h1>T</h1> <br>after", ["T", "after"], ["T"]),
        ("<h1>Head<table><tr><td>x</td></tr></table>", ["Head", "x"], None),
        ("<h1>Head<pre>code</pre>", ["Head", "code"], None),
        ("<table><tr><td>a<br>b</td></tr></table>", ["a", "b"], None),
        (
            "<table><tr><td>outer1<table><tr><td>inner</td></tr></table>outer2</td></tr></table>",
            ["outer1", "inner", "outer2"],
            None,
        ),
        ("<table><tr><td>only cell text", ["only cell text"], None),
        ("<p>x</p><table><tr><td>lost", ["x", "lost"], None),
        ("<p>x</p><pre>code line one\ncode two",["x", "code line one", "code two"], None),
        ("<table><tr><td><ul><li>one</li><li>two</li></ul></td></tr></table>", ["one", "two"], None),
        ("<table><tr><td>one<p>two</p></td></tr></table>", ["one", "two"], None),
        ("<table><tr><td><p>one</p>two</td></tr></table>", ["one", "two"], None),
        ("<table><tr><td>outer1<table>inner</table></td></tr></table>", ["outer1", "inner"], None),
        ("before<details>inside</details>", ["before", "inside"], None),
        ("<table><tr><td>a<hr>b</td></tr></table>", ["a", "b"], None),
        ("<pre>a<br>b</pre>", ["a", "b"], None),
        ("<table><tr><td>a<table><tr><td>b", ["a", "b"], None),
        ("<table><tr><td>a<div>b</div></td></tr></table>", ["a", "b"], None),
        ("<table><tr><td>a<ul>b</ul></td></tr></table>", ["a", "b"], None),
        ("<table><tr><td>a<ol>b</ol></td></tr></table>", ["a", "b"], None),
        ("<table><tr><td>a<h3>b</h3></td></tr></table>", ["a", "b"], None),
        ("<p>中文<br>字 🙂</p><p>word</p>", ["中文", "字 🙂", "word"], None),
    ],
)
def test_html_extractor_keeps_every_word_separate_and_unlost(tmp_path, html, expected, heading_path):
    source = tmp_path / "case.html"
    source.write_text(html, encoding="utf-8")
    manifest = run_extractor("extract_html.py", source, tmp_path / "case.json")
    assert_chunk_words_are_exactly(manifest, expected)
    if heading_path is not None:
        last = expected[-1].split()[-1]
        chunk = next(c for c in manifest["chunks"] if last in c["content"])
        assert chunk["locator"].get("heading_path") == heading_path


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        pytest.param("a | b\n-|-\n1 | 2\nNext\n", ["a | b", "-|-", "1 | 2", "Next"], id="table-no-trailing-pipe-then-text"),
        pytest.param("| a | b |\n|---|---|\n| 1 | 2 |\n\nAfter para\n", ["| a | b |", "|---|---|", "| 1 | 2 |", "After para"], id="piped-table-then-paragraph"),
        pytest.param("```\ncode\n```\n# Head\ntext\n", ["```", "code", "```", "# Head", "text"], id="fence-then-heading-then-text"),
        pytest.param("中文 字 🙂 word\n", ["中文", "字", "🙂", "word"], id="cjk-and-emoji"),
    ],
)
def test_markdown_extractor_keeps_every_word_separate_and_unlost(tmp_path, text, expected):
    source = tmp_path / "case.md"
    source.write_text(text, encoding="utf-8")
    manifest = run_extractor("extract_markdown.py", source, tmp_path / "case.json")
    assert_chunk_words_are_exactly(manifest, expected)


def test_html_table_keeps_row_layout(tmp_path):
    source = tmp_path / "rows.html"
    source.write_text("<table><tr><td>a<td>b</tr><tr><td>c</tr></table>", encoding="utf-8")
    manifest = run_extractor("extract_html.py", source, tmp_path / "rows.json")
    assert [c["content"].rstrip("\n") for c in manifest["chunks"]] == ["a\tb\t\nc"]


@pytest.mark.parametrize(
    ("html", "words"),
    [
        ("<table><tr><td>c3</td></tr></table>after", ["c3", "after"]),
        ("<table><tr><td>c3</td></tr></table><p>after</p>", ["c3", "after"]),
        ("<pre>code</pre>after", ["code", "after"]),
        ("<pre>code</pre><p>after</p>", ["code", "after"]),
        ("<table><tr><td>c3</td></tr></table><h2>Head</h2>", ["c3", "Head"]),
    ],
)
def test_html_atomic_blocks_never_glue_to_the_next_block(tmp_path, html, words):
    source = tmp_path / "glue.html"
    source.write_text(html, encoding="utf-8")
    manifest = run_extractor("extract_html.py", source, tmp_path / "glue.json")
    contents = [c["content"] for c in manifest["chunks"]]
    assert "".join(contents).split() == words
    for chunk in manifest["chunks"]:
        assert chunk["content"].endswith("\n")
        assert not chunk["content"].endswith("\n\n")


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


def _write_docx_body(path: Path, body: str) -> None:
    w = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    mc = "http://schemas.openxmlformats.org/markup-compatibility/2006"
    document = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<w:document xmlns:w="{w}" xmlns:mc="{mc}"><w:body>{body}</w:body></w:document>'
    )
    info = zipfile.ZipInfo("word/document.xml", date_time=(2020, 1, 1, 0, 0, 0))
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr(info, document)


def _run(text: str) -> str:
    return f"<w:r><w:t xml:space=\"preserve\">{text}</w:t></w:r>"


_TEXT_BOX = '<w:txbxContent><w:p><w:r><w:t>Boxed text</w:t></w:r></w:p></w:txbxContent>'
_ALTERNATE_CONTENT = (
    '<w:r><mc:AlternateContent>'
    f'<mc:Choice Requires="wps"><w:drawing>{_TEXT_BOX}</w:drawing></mc:Choice>'
    f'<mc:Fallback><w:pict>{_TEXT_BOX}</w:pict></mc:Fallback>'
    '</mc:AlternateContent></w:r>'
)
_FIELD = (
    '<w:r><w:fldChar w:fldCharType="begin"/></w:r>'
    '<w:r><w:instrText> HYPERLINK "http://example.com" </w:instrText></w:r>'
    '<w:r><w:fldChar w:fldCharType="separate"/></w:r>'
    '<w:r><w:t>link text</w:t></w:r>'
    '<w:r><w:fldChar w:fldCharType="end"/></w:r>'
)
_REDLINE = (
    _run("Pay is ")
    + '<w:del w:id="1"><w:r><w:delText>$100</w:delText></w:r></w:del>'
    + '<w:ins w:id="2"><w:r><w:t>$200</w:t></w:r></w:ins>'
    + _run(".")
)
_PARAGRAPH_MARK_REVISION = (
    '<w:pPr><w:rPr><w:ins w:id="3"/></w:rPr></w:pPr>' + _run("Plain end.")
)
_BLOCK_ALTERNATE_CONTENT = (
    '<mc:AlternateContent>'
    '<mc:Choice Requires="wps"><w:p><w:r><w:t>Chosen</w:t></w:r></w:p></mc:Choice>'
    '<mc:Fallback><w:p><w:r><w:t>Chosen</w:t></w:r></w:p></mc:Fallback>'
    '</mc:AlternateContent>'
)
_NESTED_BOX = (
    '<w:r><w:drawing><w:txbxContent><w:p><w:r><w:t>box</w:t></w:r></w:p>'
    '</w:txbxContent></w:drawing></w:r>'
)
_MOVED_OUT = '<w:moveFrom w:id="7"><w:r><w:delText>old spot</w:delText></w:r></w:moveFrom>'
_MOVED_IN = '<w:moveTo w:id="8"><w:r><w:t>new spot</w:t></w:r></w:moveTo>'


def _cell(inner: str) -> str:
    return f"<w:tbl><w:tr><w:tc>{inner}</w:tc></w:tr></w:tbl>"


_DOCX_WORDS_CASES = [
    pytest.param(f"<w:p>{_run('Before')}{_NESTED_BOX}{_run('after')}</w:p>", "Before box after", id="text-box-no-spaces"),
    pytest.param(
        f"<w:p><w:pPr><w:pStyle w:val=\"Heading1\"/></w:pPr>{_run('Title')}{_NESTED_BOX}{_run('end')}</w:p>",
        "Title box end",
        id="text-box-no-spaces-in-heading",
    ),
    pytest.param(_BLOCK_ALTERNATE_CONTENT, "Chosen", id="block-alternate-content-read-once"),
    pytest.param(_cell(_BLOCK_ALTERNATE_CONTENT), "Chosen", id="cell-alternate-content-read-once"),
    pytest.param(_cell("<w:sdt><w:sdtContent><w:p>" + _run("in sdt") + "</w:p></w:sdtContent></w:sdt>"), "in sdt", id="cell-paragraph-in-sdt"),
    pytest.param(_cell("<w:ins><w:p>" + _run("in ins") + "</w:p></w:ins>"), "in ins", id="cell-paragraph-in-ins"),
    pytest.param(_cell("<w:p>" + _run("outer") + "</w:p>" + _cell("<w:p>" + _run("inner") + "</w:p>")), "outer inner", id="cell-nested-table"),
    pytest.param(f"<w:p>{_run('A ')}{_MOVED_OUT}{_MOVED_IN}{_run(' B')}</w:p>", "A [deleted: old spot][inserted: new spot] B", id="inline-moves-marked"),
    pytest.param(
        f"<w:p>{_MOVED_OUT}</w:p><w:p>{_MOVED_IN}</w:p>",
        "[deleted: old spot] [inserted: new spot]",
        id="moved-paragraphs-marked",
    ),
    pytest.param(
        f"<w:p>{_run('Before ')}{_ALTERNATE_CONTENT}{_run(' after')}</w:p>",
        "Before Boxed text after",
        id="text-box-read-once",
    ),
    pytest.param(f"<w:p>{_REDLINE}</w:p>", "Pay is [deleted: $100][inserted: $200].", id="redlines-marked"),
    pytest.param(f"<w:p>{_run('中文 字 🙂 ')}{_run('word')}</w:p>", "中文 字 🙂 word", id="cjk-and-emoji"),
    pytest.param(f"<w:p>{_run('See ')}{_FIELD}</w:p>", "See link text", id="field-instruction-dropped"),
    pytest.param(f"<w:p>{_PARAGRAPH_MARK_REVISION}</w:p>", "Plain end.", id="paragraph-mark-revision-silent"),
    pytest.param(
        f"<w:tbl><w:tr><w:tc><w:p>{_ALTERNATE_CONTENT}</w:p></w:tc></w:tr></w:tbl>",
        "Boxed text",
        id="text-box-in-table-cell-read-once",
    ),
]


@pytest.mark.parametrize(("body", "visible"), _DOCX_WORDS_CASES)
def test_docx_chunk_text_is_the_visible_text_of_the_document(tmp_path, body, visible):
    source = tmp_path / "source.docx"
    _write_docx_body(source, body)
    manifest = run_extractor("extract_docx.py", source, tmp_path / "docx.json")
    assert_manifest_integrity(manifest, source, "docx")
    text = "".join(c["content"] for c in manifest["chunks"])
    assert text.split() == visible.split()


@pytest.mark.parametrize(
    ("body", "marker"),
    [
        pytest.param(
            '<w:p><w:ins><w:r><w:t xml:space="preserve"> x </w:t></w:r></w:ins></w:p>',
            "[inserted: x]",
            id="inserted-text-is-stripped",
        ),
        pytest.param(
            '<w:p><w:del><w:r><w:delText xml:space="preserve"> y </w:delText></w:r></w:del></w:p>',
            "[deleted: y]",
            id="deleted-text-is-stripped",
        ),
        pytest.param(
            f"<w:p>{_MOVED_OUT.replace('old spot', ' old spot ')}</w:p>",
            "[deleted: old spot]",
            id="moved-from-text-is-stripped",
        ),
    ],
)
def test_docx_markers_are_stripped_and_exact(tmp_path, body, marker):
    source = tmp_path / "source.docx"
    _write_docx_body(source, body)
    manifest = run_extractor("extract_docx.py", source, tmp_path / "docx.json")
    text = "".join(c["content"] for c in manifest["chunks"])
    assert text.strip() == marker


def test_docx_tracked_change_in_heading_marks_the_heading_path(tmp_path):
    source = tmp_path / "heading.docx"
    heading = (
        '<w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr>' + _run("Terms ")
        + '<w:del w:id="1"><w:r><w:delText>old</w:delText></w:r></w:del></w:p>'
    )
    _write_docx_body(source, heading + "<w:p>" + _run("Body.") + "</w:p>")
    manifest = run_extractor("extract_docx.py", source, tmp_path / "heading.json")
    body = [c for c in manifest["chunks"] if "Body." in c["content"]]
    assert body[0]["locator"]["heading_path"] == ["Terms [deleted: old]"]


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
