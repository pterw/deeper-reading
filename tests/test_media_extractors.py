import json
import subprocess
import sys

import pytest

from media_helpers import (
    SCRIPTS,
    extract_manifest_text,
    manifest_text,
    normalise,
    read_golden,
    write_golden_source,
)

# One row per media syntax: (format, source text, expected media as (kind, syntax, ref, alt)).
# T8 (HTML) and T9 (DOCX) add rows here.
MEDIA_ROWS = [
    pytest.param("md", "# T\n\nSee ![a pic](img/p.png) now.\n", [("image", "md_image", "img/p.png", "a pic")], id="md-image"),
    pytest.param("md", "# T\n\n![a pic][fig]\n\n[fig]: p.png\n", [("image", "md_image", "fig", "a pic")], id="md-image-reference-form"),
    pytest.param("md", "# T\n\nOpen [the chart](charts/c.JPG) here.\n", [("image", "md_link", "charts/c.JPG", None)], id="md-link-image"),
    pytest.param("md", "# T\n\n[v2](p.png?v=2#top)\n", [("image", "md_link", "p.png?v=2#top", None)], id="md-link-query-string"),
    pytest.param("md", "# T\n\nRead [the docs](guide.html) first.\n", [], id="md-link-non-image-ignored"),
    pytest.param("md", '# T\n\n<img alt="logo  mark" src="l.gif">\n', [("image", "html_img", "l.gif", "logo mark")], id="md-html-img"),
    pytest.param("md", "# T\n\n<svg><svg><g/></svg></svg>\n", [("svg", "html_svg", None, None)], id="md-html-svg-outermost-once"),
    pytest.param("md", '# T\n\n<div class="box mermaid">graph TD</div>\n', [("diagram", "html_diagram", None, None)], id="md-html-diagram-div"),
    pytest.param("md", '# T\n\n<pre class="mermaid">graph TD</pre>\n', [("diagram", "html_diagram", None, None)], id="md-html-diagram-pre"),
    pytest.param("md", "# T\n\n```mermaid\ngraph TD\n```\n", [("diagram", "fence_diagram", None, None)], id="md-fence-mermaid"),
    pytest.param("md", "# T\n\n~~~PlantUML\n@startuml\n~~~\n", [("diagram", "fence_diagram", None, None)], id="md-fence-plantuml"),
    pytest.param("md", "# T\n\nUse `![a](p.png)` to embed.\n", [], id="md-inline-code-span-ignored"),
    pytest.param("md", "# T\n\n```python\n![a](p.png)\n<img src='x.png'>\n```\n", [], id="md-non-diagram-fence-ignored"),
    pytest.param(
        "md",
        '# T\n\n<img src="first.png" alt="one"> and ![two](second.png) and [three](third.gif)\n',
        [
            ("image", "html_img", "first.png", "one"),
            ("image", "md_image", "second.png", "two"),
            ("image", "md_link", "third.gif", None),
        ],
        id="md-two-references-in-one-block-keep-source-order",
    ),
    pytest.param(
        "md",
        "# T\n\n[![badge](b.png)](https://example.test/page)\n",
        [("image", "md_image", "b.png", "badge")],
        id="md-image-inside-a-link",
    ),
    pytest.param("md", "# T\n\n![A  Pic]\n\n[a pic]: p.png\n", [("image", "md_image", "A  Pic", "A Pic")], id="md-image-shortcut-with-definition"),
    pytest.param("md", "# T\n\nSee ![nodef] here.\n", [], id="md-image-shortcut-without-definition-ignored"),
    pytest.param("md", "# T\n\n<!-- ![a](p.png) -->\n", [], id="md-image-inside-comment-ignored"),
    pytest.param(
        "md",
        "# T\n\n<!-- old\n![a](old.png) -->\n![b](real.png)\n",
        [("image", "md_image", "real.png", "b")],
        id="md-multiline-comment-then-real-image-only-real-recorded",
    ),
]


def write_source(fmt, text, directory):
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"source.{fmt}"
    path.write_bytes(text.encode("utf-8"))
    return path


def manifest_media(fmt, text, tmp_path, max_bytes=12000):
    source = write_source(fmt, text, tmp_path / "src")
    manifest = json.loads(extract_manifest_text(fmt, source, tmp_path / "m.json", max_bytes))
    return manifest, [
        (item["kind"], item["syntax"], item["ref"], item["alt"]) for item in manifest.get("media", [])
    ]


@pytest.mark.parametrize(("fmt", "text", "expected"), MEDIA_ROWS)
def test_extractor_records_media_references(tmp_path, fmt, text, expected):
    manifest, found = manifest_media(fmt, text, tmp_path)
    assert found == expected
    assert ("media" in manifest) == bool(expected)
    for item in manifest.get("media", []):
        assert any(chunk["id"] == item["chunk_id"] for chunk in manifest["chunks"])


def test_media_entries_number_in_document_order(tmp_path):
    text = "# T\n\n![a](1.png)\n\n![b](2.png)\n\n![c](3.png)\n"
    manifest, found = manifest_media("md", text, tmp_path)
    assert [item["id"] for item in manifest["media"]] == ["media-0001", "media-0002", "media-0003"]
    assert [ref for _, _, ref, _ in found] == ["1.png", "2.png", "3.png"]


def test_fragment_split_paragraph_yields_the_reference_once(tmp_path):
    words = " ".join(f"word{n}" for n in range(60))
    manifest, found = manifest_media("md", f"# T\n\n![a](p.png) {words}\n", tmp_path, max_bytes=90)
    assert len(manifest["chunks"]) > 2
    assert found == [("image", "md_image", "p.png", "a")]
    owner = next(c for c in manifest["chunks"] if c["id"] == manifest["media"][0]["chunk_id"])
    assert "![a](p.png)" in owner["content"]


def test_no_media_markdown_manifest_equals_golden_byte_for_byte(tmp_path):
    source = write_golden_source("md", tmp_path / "src")
    manifest = json.loads(extract_manifest_text("md", source, tmp_path / "m.json"))
    assert "media" not in manifest
    assert manifest_text(normalise(manifest)) == read_golden("manifest_md.json")


_WITHOUT_HOOK = """
import json, sys
sys.path.insert(0, sys.argv[1])
import extract_markdown
extract_markdown.collect_media = lambda blocks: None
from pathlib import Path
print(json.dumps(extract_markdown.extract(Path(sys.argv[2]), max_bytes=90)))
"""


def test_media_changes_nothing_but_the_media_key(tmp_path):
    text = "# T\n\nOne ![a](p.png) two.\n\n```mermaid\ngraph TD\n```\n\n<svg></svg> tail\n"
    source = write_source("md", text, tmp_path / "src")
    with_media = json.loads(extract_manifest_text("md", source, tmp_path / "m.json", 90))
    result = subprocess.run(
        [sys.executable, "-c", _WITHOUT_HOOK, str(SCRIPTS), str(source)],
        capture_output=True, text=True, check=True,
    )
    baseline = json.loads(result.stdout)
    assert len(with_media.pop("media")) == 3
    assert with_media == baseline
