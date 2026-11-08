import json
import subprocess
import sys
import time
import zipfile

import pytest

from media_helpers import (
    SCRIPTS,
    extract_manifest_text,
    manifest_text,
    normalise,
    read_golden,
    write_golden_source,
    write_zip_member,
)

_NS = (
    'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
    'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
    'xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" '
    'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
    'xmlns:c="http://schemas.openxmlformats.org/drawingml/2006/chart" '
    'xmlns:dgm="http://schemas.openxmlformats.org/drawingml/2006/diagram" '
    'xmlns:wps="http://schemas.microsoft.com/office/word/2010/wordprocessingShape" '
    'xmlns:cx="http://schemas.microsoft.com/office/drawing/2014/chartex" '
    'xmlns:wpg="http://schemas.microsoft.com/office/word/2010/wordprocessingGroup" '
    'xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture" '
    'xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006" '
    'xmlns:v="urn:schemas-microsoft-com:vml" xmlns:o="urn:schemas-microsoft-com:office:office"'
)
_PART_ROOTS = {"footnotes": "footnotes", "endnotes": "endnotes", "comments": "comments", "header1": "hdr", "footer1": "ftr"}


def dx_p(text="", *extra):
    run = f'<w:r><w:t xml:space="preserve">{text}</w:t></w:r>' if text else ""
    return f"<w:p>{run}{''.join(extra)}</w:p>"


def dx_pic(rid, descr=None, title=None, attr="embed", wrapper="inline"):
    names = "".join(f' {k}="{v}"' for k, v in (("descr", descr), ("title", title)) if v)
    return (
        f'<w:r><w:drawing><wp:{wrapper}><wp:docPr id="1" name="x"{names}/>'
        f'<a:graphic><a:graphicData><a:blip r:{attr}="{rid}"/></a:graphicData></a:graphic></wp:{wrapper}></w:drawing></w:r>'
    )


def _rels_xml(mapping):
    items = "".join(
        f'<Relationship Id="{k}" Type="t" Target="{v}"/>' for k, v in mapping.items()
    )
    return f'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">{items}</Relationships>'


def dx_parts(body, rels=None, **others):
    """In-memory DOCX members. body is document.xml's content, rels its relationship id ->
    target map; every other story part is name=(content, rels)."""
    def xml(content, tag):
        return f'<?xml version="1.0"?><w:{tag} {_NS}>{content}</w:{tag}>'

    parts = {"word/document.xml": xml(f"<w:body>{body}</w:body>", "document")}
    if rels:
        parts["word/_rels/document.xml.rels"] = _rels_xml(rels)
    for name, (content, part_rels) in others.items():
        parts[f"word/{name}.xml"] = xml(content, _PART_ROOTS[name])
        if part_rels:
            parts[f"word/_rels/{name}.xml.rels"] = _rels_xml(part_rels)
    return parts


_ALTERNATE = (
    '<mc:AlternateContent><mc:Choice Requires="wps">' + dx_pic("rId1") + "</mc:Choice>"
    '<mc:Fallback><w:r><w:pict><v:imagedata r:id="rId1"/></w:pict></w:r></mc:Fallback></mc:AlternateContent>'
)
_TEXT_BOX = (
    "<w:r><w:drawing><wp:anchor><wps:wsp><wps:txbx><w:txbxContent>"
    + dx_p("boxed words")
    + "</w:txbxContent></wps:txbx></wps:wsp></wp:anchor></w:drawing></w:r>"
)
_CHART = '<w:r><w:drawing><a:graphic><a:graphicData><c:chart r:id="rId6"/></a:graphicData></a:graphic></w:drawing></w:r>'
_DIAGRAM = '<w:r><w:drawing><a:graphic><a:graphicData><dgm:relIds r:dm="rId7"/></a:graphicData></a:graphic></w:drawing></w:r>'

# One row per media syntax: (format, source text, expected media as (kind, syntax, ref, alt)).
# A docx "source text" is a dict of zip members (see dx_parts).
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
    pytest.param("md", "# T\n\nUse `![a](p.png)` to embed.\n", [("image", "md_image", "p.png", "a")], id="md-inline-code-span-recorded"),
    pytest.param("md", "# T\n\n```python\n![a](p.png)\n<img src='x.png'>\n```\n", [], id="md-closed-non-diagram-fence-not-recorded"),
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
    pytest.param("md", "# T\n\nSee ![nodef] here.\n", [("image", "md_image", "nodef", "nodef")], id="md-image-shortcut-without-definition-recorded"),
    pytest.param("md", "# T\n\n<!-- ![a](p.png) -->\n", [("image", "md_image", "p.png", "a")], id="md-image-inside-comment-recorded"),
    pytest.param(
        "md",
        "# T\n\n<!-- old\n![a](old.png) -->\n![b](real.png)\n",
        [("image", "md_image", "old.png", "a"), ("image", "md_image", "real.png", "b")],
        id="md-multiline-comment-then-real-image-both-recorded",
    ),
    pytest.param("md", "# T\n\n![Plot [A]](plot.png)\n", [("image", "md_image", "plot.png", "Plot [A]")], id="md-image-with-bracketed-alt"),
    pytest.param("md", "# T\n\nSee [figure](plot(1).png) here.\n", [("image", "md_link", "plot(1).png", None)], id="md-link-to-parenthesised-destination"),
    pytest.param("md", '# T\n\n![pic](a(b).png "A title")\n', [("image", "md_image", "a(b).png", "pic")], id="md-image-parenthesised-destination-with-title"),
    pytest.param("md", '# T\n\n<svg><svg width="1" /><svg/><circle r="2"/></svg><svg><circle r="3"/></svg>\n', [("svg", "html_svg", None, None), ("svg", "html_svg", None, None)], id="md-self-closing-svg-does-not-deepen-nesting"),
    pytest.param("md", "# T\n\n<svg />\n", [("svg", "html_svg", None, None)], id="md-top-level-self-closing-svg-recorded"),
    pytest.param("md", "# T\n\nUse ``![a](p.png)`` to embed.\n", [("image", "md_image", "p.png", "a")], id="md-double-backtick-span-recorded"),
    pytest.param("md", "# T\n\n    ```\n\n![vis](a.png)\n", [("image", "md_image", "a.png", "vis")], id="md-indented-fence-line-does-not-hide-later-image"),
    pytest.param("md", "# T\n\n```code``` text ![v](a.png)\n\n![x](b.png)\n", [("image", "md_image", "a.png", "v"), ("image", "md_image", "b.png", "x")], id="md-backtick-in-info-fence-is-scanned-as-text"),
    pytest.param("md", "# T\n\n```python\n![a](p.png)\n", [("image", "md_image", "p.png", "a")], id="md-unclosed-fence-is-scanned-as-text"),
    pytest.param("md", "# T\n\n```mermaid\ngraph TD\n", [("diagram", "fence_diagram", None, None)], id="md-unclosed-diagram-fence-still-recorded"),
    pytest.param("md", "# T\n\n````python\n![a](p.png)\n```\n", [("image", "md_image", "p.png", "a")], id="md-shorter-closer-leaves-fence-unclosed"),
    pytest.param("md", "# T\n\n```python\n![a](p.png)\n    ```\n", [("image", "md_image", "p.png", "a")], id="md-closer-indented-four-leaves-fence-unclosed"),
    pytest.param("md", "# T\n\n  ~~~python\n![a](p.png)\n  ~~~~\n\n![b](q.png)\n", [("image", "md_image", "q.png", "b")], id="md-closed-tilde-fence-with-longer-closer-not-recorded"),
    pytest.param("md", "# T\n\n![a\\]b](x.png)\n", [("image", "md_image", "x.png", "a\\]b")], id="md-image-escaped-bracket-in-alt"),
    pytest.param("md", "# T\n\n[a\\]b](x.png)\n", [("image", "md_link", "x.png", None)], id="md-link-escaped-bracket-in-text"),
    pytest.param("md", '# T\n\n<img alt="a > b" src="a.png">\n', [("image", "html_img", "a.png", "a > b")], id="md-html-img-gt-in-quoted-attribute"),
    pytest.param("md", '# T\n\n<div data-x="a>b" class="mermaid">g</div>\n', [("diagram", "html_diagram", None, None)], id="md-diagram-div-gt-in-quoted-attribute"),
    pytest.param("md", '# T\n\n<svg data-x="a>b" /><svg><svg></svg></svg>\n', [("svg", "html_svg", None, None), ("svg", "html_svg", None, None)], id="md-self-closing-svg-gt-in-quoted-attribute"),
    pytest.param("md", "# T\n\nthe <svg> tag\n<svg id=1></svg>\n<svg id=2></svg>\n", [("svg", "html_svg", None, None)] * 3, id="md-unclosed-svg-does-not-hide-later-svgs"),
    pytest.param("md", "# T\n\n    ```python\n![a](p.png)\n```\n", [("image", "md_image", "p.png", "a")], id="md-closed-fence-with-four-space-opener-is-scanned-as-text"),
    pytest.param("md", "# T\n\n```a`b\n![a](p.png)\n```\n", [("image", "md_image", "p.png", "a")], id="md-closed-backtick-fence-with-backtick-in-info-is-scanned-as-text"),
    pytest.param("md", '# T\n\n<img alt=don\'t src="a.png">\n', [("image", "html_img", "a.png", "don't")], id="md-html-img-apostrophe-in-unquoted-attribute"),
    pytest.param("md", '# T\n\n<img src="a.png" alt=don\'t> it\'s <img src="b.png">\n', [("image", "html_img", "a.png", "don't"), ("image", "html_img", "b.png", None)], id="md-html-img-apostrophes-do-not-swallow-the-next-tag"),
    pytest.param("md", '# T\n\n<img alt="x> text <img src="b.png" alt="c">\n', [("image", "html_img", None, '"x'), ("image", "html_img", "b.png", "c")], id="md-html-img-stray-quote-does-not-span-a-later-tag"),
    pytest.param("md", "# T\n\n<img src=a.png alt=it's>\n", [("image", "html_img", "a.png", "it's")], id="md-html-img-apostrophe-in-last-attribute"),
    pytest.param("md", "# T\n\n<img alt=a<b src=x.png>\n", [("image", "html_img", "x.png", "a<b")], id="md-html-img-angle-bracket-inside-tag"),
    pytest.param("md", '# T\n\n<img src="a.png" alt="x>\n', [("image", "html_img", "a.png", '"x')], id="md-html-img-unterminated-quote"),
    pytest.param("md", "# T\n\n<div title=it's class=\"mermaid\">g</div>\n", [("diagram", "html_diagram", None, None)], id="md-diagram-div-apostrophe-in-unquoted-attribute"),
    pytest.param("md", "# T\n\n<img alt=\"x>\n\n<img src=\"b.png\" alt=\"c\">\n", [("image", "html_img", None, '"x'), ("image", "html_img", "b.png", "c")], id="md-html-img-stray-quote-does-not-swallow-next-tag"),
    pytest.param("md", "# T\n\n\\\\[a](p.png)\n", [("image", "md_link", "p.png", None)], id="md-link-after-escaped-backslash"),
    pytest.param("md", "# T\n\n\\![a](p.png)\n", [("image", "md_image", "p.png", "a")], id="md-escaped-bang-image-still-recorded"),
    pytest.param("md", "# T\n\n![broken](bad\n![real](real.png)\n", [("image", "md_image", "bad", "broken"), ("image", "md_image", "real.png", "real")], id="md-unclosed-destination-does-not-swallow-next-image"),
    pytest.param("md", '# T\n\n![a](b.png "open\n![real](real.png)\n', [("image", "md_image", "b.png", "a"), ("image", "md_image", "real.png", "real")], id="md-unclosed-title-does-not-swallow-next-image"),
    pytest.param("md", "# T\n\n[t](x.png\n![real](real.png)\n", [("image", "md_link", "x.png", None), ("image", "md_image", "real.png", "real")], id="md-unclosed-link-keeps-its-record-and-the-next-image"),
    pytest.param("md", "# T\n\n[](<img [x](z.png)\n", [("image", "md_link", "z.png", None)], id="md-malformed-link-destination-does-not-swallow-next-link"),
    pytest.param("md", "# T\n\n[figure](plot\\).png)\n", [("image", "md_link", "plot\\).png", None)], id="md-link-escaped-paren-belongs-to-destination"),
    pytest.param("md", "# T\n\n![a](p\\).png)\n", [("image", "md_image", "p\\).png", "a")], id="md-image-escaped-paren-belongs-to-destination"),
    pytest.param("md", "# T\n\n[figure](plot&#46;png)\n", [("image", "md_link", "plot&#46;png", None)], id="md-link-decimal-reference-in-extension"),
    pytest.param("md", "# T\n\n[a](p&#x2E;png) [b](p&period;png)\n", [("image", "md_link", "p&#x2E;png", None), ("image", "md_link", "p&period;png", None)], id="md-link-hex-and-named-reference-in-extension"),
    pytest.param("md", "# T\n\n[v](p&#46;png?v=2&#35;top)\n", [("image", "md_link", "p&#46;png?v=2&#35;top", None)], id="md-link-reference-extension-then-query-and-fragment"),
    pytest.param("md", "# T\n\n[d](guide&#46;html)\n", [], id="md-link-non-image-after-decoding-ignored"),
    pytest.param("md", "# T\n\n[x](p&num;.png)\n", [], id="md-link-named-hash-reference-is-a-fragment-delimiter"),
    pytest.param("md", "# T\n\n[x](p&#35;.png)\n", [], id="md-link-numeric-hash-reference-is-a-fragment-delimiter"),
    pytest.param("md", f"# T\n\n[x](p&#{'9' * 5000};.png)\n", [("image", "md_link", f"p&#{'9' * 197}", None)], id="md-link-undecodable-reference-recorded"),
    pytest.param("md", f'# T\n\n<img src="a&#{"9" * 5000};.png">\n', [("image", "html_img", "a�.png", None)], id="md-html-img-undecodable-reference-recorded"),
    pytest.param("md", f'# T\n\n<img src="a&#{"0" * 5000}46;png">\n', [("image", "html_img", "a.png", None)], id="md-html-img-long-zero-run-reference-decoded"),
    pytest.param("md", f"# T\n\n[x](plot&#{'0' * 5000}46;html)\n", [], id="md-link-long-zero-run-reference-decoded-non-image"),
    pytest.param("html", '<h1>T</h1><p>See <img src="a.png" alt="a  pic"> now.</p>', [("image", "img", "a.png", "a pic")], id="html-img"),
    pytest.param("html", '<h1>T</h1><img data-src="lazy.png"><p>text</p>', [("image", "img", "lazy.png", None)], id="html-img-data-src-alone-attaches-to-next-block"),
    pytest.param("html", "<h1>T</h1><p>x <svg><svg><g/></svg></svg> y</p>", [("svg", "svg", None, None)], id="html-svg-outermost-once"),
    pytest.param("html", '<h1>T</h1><p>x</p><object data="d.pdf" type="application/pdf"></object>', [("embedded", "object", "d.pdf", None)], id="html-object-embedded"),
    pytest.param("html", '<h1>T</h1><p>x</p><object data="d.svg"></object><embed src="e.png" type="image/png">', [("image", "object", "d.svg", None), ("image", "embed", "e.png", None)], id="html-object-embed-image"),
    pytest.param("html", '<h1>T</h1><div class="a mermaid"><div class="mermaid">graph TD</div></div>', [("diagram", "diagram", None, None)], id="html-diagram-div-nested-once"),
    pytest.param("html", '<h1>T</h1><pre class="mermaid">graph TD</pre>', [("diagram", "diagram", None, None)], id="html-diagram-pre"),
    pytest.param("html", '<h1>T</h1><script><img src="s.png"></script><noscript><img src="n.png"></noscript><p>x</p>', [], id="html-skipped-containers-ignored"),
    pytest.param("html", '<h1>T</h1><table><tr><td>a <img src="t.png" alt="in table"></td></tr></table>', [("image", "img", "t.png", "in table")], id="html-img-inside-table"),
    pytest.param("html", '<h1>T</h1><pre>code <img src="p.png"></pre>', [("image", "img", "p.png", None)], id="html-img-inside-pre"),
    pytest.param(
        "html",
        '<h1>T</h1><p>one <img src="1.png"> two <svg></svg> three <img src="3.png"></p>',
        [("image", "img", "1.png", None), ("svg", "svg", None, None), ("image", "img", "3.png", None)],
        id="html-two-references-in-one-block-keep-source-order",
    ),
    pytest.param("html", '<h1>T</h1><p>x <svg><svg></svg><img src="x.png"></svg></p>', [("svg", "svg", None, None), ("image", "img", "x.png", None)], id="html-img-inside-svg-recorded-after-nested-svg"),
    pytest.param("html", '<h1>T</h1><p>x</p><embed type="image/png" src="x">', [("image", "embed", "x", None)], id="html-embed-image-type-without-extension"),
    pytest.param("html", '<h1>T</h1><div class="mermaidx">graph TD</div>', [], id="html-class-mermaidx-not-a-diagram"),
    pytest.param(
        "html",
        '<h1>T</h1><p>x<svg></p><p><img src="after.png"></p>',
        [("svg", "svg", None, None), ("image", "img", "after.png", None)],
        id="html-unclosed-svg-does-not-hide-later-media",
    ),
    pytest.param(
        "html",
        '<h1>T</h1><p>x <svg><circle r="1"/> text <img src="a.png"></p>',
        [("svg", "svg", None, None), ("image", "img", "a.png", None)],
        id="html-unclosed-svg-does-not-hide-img-in-same-paragraph",
    ),
    pytest.param(
        "html",
        '<h1>T</h1><p>x <svg><svg><g/></svg></svg> y <svg></svg></p>',
        [("svg", "svg", None, None), ("svg", "svg", None, None)],
        id="html-nested-svg-inside-closed-svg-recorded-once",
    ),
    pytest.param(
        "html",
        '<h1>T</h1><p>x <svg></p><p>y <svg></svg></p>',
        [("svg", "svg", None, None), ("svg", "svg", None, None)],
        id="html-unclosed-svg-block-end-lets-later-svg-record",
    ),
    pytest.param(
        "html",
        '<h1>T</h1><p>x <svg><object data="o.png"></object></p>',
        [("svg", "svg", None, None), ("image", "object", "o.png", None)],
        id="html-object-inside-unclosed-svg-recorded",
    ),
    pytest.param(
        "html",
        '<h1>T</h1><p>x <svg><embed src="e.png"></p>',
        [("svg", "svg", None, None), ("image", "embed", "e.png", None)],
        id="html-embed-inside-unclosed-svg-recorded",
    ),
    pytest.param(
        "html",
        '<h1>T</h1><p>x <svg><div class="mermaid">graph TD</div></p>',
        [("svg", "svg", None, None), ("diagram", "diagram", None, None)],
        id="html-mermaid-div-inside-unclosed-svg-recorded",
    ),
    pytest.param("docx", dx_parts(dx_p("See ", dx_pic("rId1", descr="a  pic")), {"rId1": "media/a.png"}), [("image", "drawing", "media/a.png", "a pic")], id="docx-inline-picture"),
    pytest.param(
        "docx",
        dx_parts(f"<w:tbl><w:tr><w:tc>{dx_p('cell', dx_pic('rId2', title='floaty', wrapper='anchor'))}</w:tc></w:tr></w:tbl>", {"rId2": "media/f.jpg"}),
        [("image", "drawing", "media/f.jpg", "floaty")],
        id="docx-floating-picture-in-table-cell",
    ),
    pytest.param(
        "docx",
        dx_parts(dx_p("body", dx_pic("rId1")), {"rId1": "media/body.png"}, header1=(dx_p("head", dx_pic("rId1")), {"rId1": "media/head.png"})),
        [("image", "drawing", "media/body.png", None), ("image", "drawing", "media/head.png", None)],
        id="docx-header-picture-uses-its-own-relationships",
    ),
    pytest.param(
        "docx",
        dx_parts(
            dx_p("t", dx_pic("rId1", attr="link")),
            {"rId1": "https://example.test/x.png"},
            footer1=(dx_p("foot", dx_pic("rId1")), {"rId1": "media/foot.png"}),
            footnotes=(dx_p("note", dx_pic("rId1")), {"rId1": "media/note.png"}),
            endnotes=(dx_p("end", dx_pic("rId1")), {"rId1": "media/end.png"}),
            comments=(dx_p("com", dx_pic("rId1")), {"rId1": "media/com.png"}),
        ),
        [
            ("image", "drawing", "https://example.test/x.png", None),
            ("image", "drawing", "media/foot.png", None),
            ("image", "drawing", "media/note.png", None),
            ("image", "drawing", "media/end.png", None),
            ("image", "drawing", "media/com.png", None),
        ],
        id="docx-linked-picture-and-footer-footnote-endnote-comment-pictures",
    ),
    pytest.param("docx", dx_parts(dx_p("x", _ALTERNATE), {"rId1": "media/c.png"}), [("image", "drawing", "media/c.png", None)], id="docx-alternate-content-choice-only-recorded-once"),
    pytest.param("docx", dx_parts(dx_p("x", dx_pic("rId1", descr="d"))), [("image", "drawing", None, "d")], id="docx-unresolved-relationship-keeps-null-ref"),
    pytest.param("docx", dx_parts(dx_p("x", _TEXT_BOX)), [], id="docx-picture-less-text-box-not-recorded"),
    pytest.param(
        "docx",
        dx_parts('<w:p><w:r><w:t>x</w:t><w:pict><v:shape><v:imagedata r:id="rId3"/></v:shape></w:pict></w:r></w:p>', {"rId3": "media/v.emz"}),
        [("image", "vml_image", "media/v.emz", None)],
        id="docx-vml-image",
    ),
    pytest.param(
        "docx",
        dx_parts(
            '<w:p><w:r><w:t>x</w:t><w:object><v:shape><v:imagedata r:id="rId4"/></v:shape>'
            '<o:OLEObject r:id="rId5"/></w:object></w:r></w:p>',
            {"rId4": "media/preview.emf", "rId5": "embeddings/sheet.xlsx"},
        ),
        [("embedded", "ole_object", "embeddings/sheet.xlsx", None)],
        id="docx-ole-object-with-preview-recorded-once",
    ),
    pytest.param(
        "docx",
        dx_parts(dx_p("x", _CHART, _DIAGRAM), {"rId6": "charts/chart1.xml", "rId7": "diagrams/data1.xml"}),
        [("diagram", "drawing", "charts/chart1.xml", None), ("diagram", "drawing", "diagrams/data1.xml", None)],
        id="docx-chart-and-diagram-data",
    ),
    pytest.param(
        "docx",
        dx_parts(
            dx_p("x", dx_pic("rId1"), '<w:r><w:pict><v:imagedata r:id="rId2"/></w:pict></w:r>', dx_pic("rId3")),
            {"rId1": "1.png", "rId2": "2.png", "rId3": "3.png"},
        ),
        [("image", "drawing", "1.png", None), ("image", "vml_image", "2.png", None), ("image", "drawing", "3.png", None)],
        id="docx-two-references-in-one-block-keep-source-order",
    ),
    pytest.param(
        "docx",
        dx_parts(
            dx_p("x", '<w:r><w:drawing><wp:anchor><wp:docPr id="1" name="g" descr="pair"/><a:graphic><a:graphicData><wpg:wgp>'
                 '<pic:pic><a:blip r:embed="rId1"/></pic:pic><pic:pic><a:blip r:embed="rId2"/></pic:pic>'
                 "</wpg:wgp></a:graphicData></a:graphic></wp:anchor></w:drawing></w:r>"),
            {"rId1": "a.png", "rId2": "b.png"},
        ),
        [("image", "drawing", "a.png", "pair"), ("image", "drawing", "b.png", "pair")],
        id="docx-group-of-two-pictures-records-both-in-order",
    ),
    pytest.param(
        "docx",
        dx_parts(
            dx_p("x", '<w:r><w:drawing><wp:anchor><wp:docPr id="1" name="t" descr="box"/><wps:wsp><wps:txbx><w:txbxContent>'
                 + dx_p("", dx_pic("rId1")) + dx_p("", dx_pic("rId2"))
                 + "</w:txbxContent></wps:txbx></wps:wsp></wp:anchor></w:drawing></w:r>"),
            {"rId1": "a.png", "rId2": "b.png"},
        ),
        [("image", "drawing", "a.png", "box"), ("image", "drawing", "b.png", "box")],
        id="docx-text-box-with-two-images-records-both",
    ),
    pytest.param(
        "docx",
        dx_parts(
            dx_p("x", '<w:r><w:drawing><a:graphic><a:graphicData><cx:chart r:id="rId8"/></a:graphicData></a:graphic></w:drawing></w:r>'),
            {"rId8": "charts/chartEx1.xml"},
        ),
        [("diagram", "drawing", "charts/chartEx1.xml", None)],
        id="docx-chartex-chart-is-a-diagram",
    ),
    pytest.param(
        "docx",
        dx_parts(
            dx_p("x", "<w:r><w:pict><v:shape><v:textbox><w:txbxContent>" + dx_p("", dx_pic("rId1", descr="in vml box"))
                 + "</w:txbxContent></v:textbox></v:shape></w:pict></w:r>"),
            {"rId1": "a.png"},
        ),
        [("image", "drawing", "a.png", "in vml box")],
        id="docx-drawing-inside-a-vml-text-box",
    ),
    pytest.param(
        "docx",
        dx_parts(
            dx_p("x", '<w:r><w:drawing><wp:anchor><a:graphic><a:graphicData><a:blip r:embed="rId1"/></a:graphicData></a:graphic>'
                 '<wps:wsp><wps:txbx><w:txbxContent><w:p><w:r><w:pict><v:imagedata r:id="rId2"/></w:pict></w:r></w:p>'
                 "</w:txbxContent></wps:txbx></wps:wsp></wp:anchor></w:drawing></w:r>"),
            {"rId1": "a.png", "rId2": "b.png"},
        ),
        [("image", "drawing", "a.png", None), ("image", "vml_image", "b.png", None)],
        id="docx-drawing-text-box-holding-a-vml-image-records-both",
    ),
    pytest.param(
        "docx",
        dx_parts(
            dx_p("x", '<w:r><w:drawing><wp:anchor><a:graphic><a:graphicData><a:blip r:embed="rId1"/></a:graphicData></a:graphic>'
                 '<wps:wsp><wps:txbx><w:txbxContent><w:p><w:r><w:object><v:shape><v:imagedata r:id="rId4"/></v:shape>'
                 '<o:OLEObject r:id="rId5"/></w:object></w:r></w:p></w:txbxContent></wps:txbx></wps:wsp></wp:anchor></w:drawing></w:r>'),
            {"rId1": "a.png", "rId4": "media/preview.emf", "rId5": "embeddings/sheet.xlsx"},
        ),
        [("image", "drawing", "a.png", None), ("embedded", "ole_object", "embeddings/sheet.xlsx", None)],
        id="docx-drawing-text-box-holding-an-ole-object-records-it-once",
    ),
    pytest.param(
        "docx",
        dx_parts(
            dx_p("x", '<w:r><w:drawing><wp:anchor><a:graphic><a:graphicData><a:blip r:embed="rId1"/></a:graphicData></a:graphic>'
                 "<wps:wsp><wps:txbx><w:txbxContent><w:p><w:r><w:object>"
                 + dx_pic("rId4")
                 + '<o:OLEObject r:id="rId5"/></w:object></w:r></w:p></w:txbxContent></wps:txbx></wps:wsp></wp:anchor></w:drawing></w:r>'),
            {"rId1": "a.png", "rId4": "media/preview.png", "rId5": "embeddings/sheet.xlsx"},
        ),
        [("image", "drawing", "a.png", None), ("embedded", "ole_object", "embeddings/sheet.xlsx", None)],
        id="docx-ole-object-with-drawing-preview-in-a-text-box-records-no-preview",
    ),
    pytest.param(
        "docx",
        dx_parts(
            dx_p("x", "<w:r><w:drawing><wp:anchor><wps:wsp><wps:txbx><w:txbxContent>"
                 '<w:p><w:r><w:pict><v:imagedata r:id="rId2"/></w:pict></w:r></w:p></w:txbxContent></wps:txbx></wps:wsp>'
                 '<a:graphic><a:graphicData><a:blip r:embed="rId1"/></a:graphicData></a:graphic></wp:anchor></w:drawing></w:r>'),
            {"rId1": "a.png", "rId2": "b.png"},
        ),
        [("image", "vml_image", "b.png", None), ("image", "drawing", "a.png", None)],
        id="docx-vml-image-before-the-drawing-picture-comes-first",
    ),
]


def write_source(fmt, text, directory):
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"source.{fmt}"
    if fmt == "docx":
        with zipfile.ZipFile(path, "w") as zf:
            for name, data in text.items():
                write_zip_member(zf, name, data)
        return path
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


@pytest.mark.parametrize(
    ("opener", "expected"),
    [("![a](", [("image", "md_image", "a", "a")]), ("[a](", [])],
    ids=["image", "link"],
)
def test_unclosed_markdown_destination_scans_in_linear_time(tmp_path, opener, expected):
    text = f"# T\n\n{opener}data:image/png;base64,{'A' * 512 * 1024}\n"
    started = time.monotonic()
    manifest, found = manifest_media("md", text, tmp_path, max_bytes=2_000_000)
    assert time.monotonic() - started < 2
    assert found == expected


@pytest.mark.parametrize(
    "unit",
    [
        "\\[", "\\[ a \\] ", "![a\\[", "![a\\[](", "![", "![a](<", "[a](", "[![a](x.png",
        "![a](\n![b](b.png)\n", "[a](\\)", "[a](\\(", "![a](\\)\\(",
        '<img "', '<img ">a "', "<img a=\">", "<svg ", "<div class=\"mermaid\" ",
    ],
)
def test_adversarial_repeated_shapes_scan_in_linear_time(tmp_path, unit):
    body = (unit * (512 * 1024 // len(unit) + 1))[: 512 * 1024]
    started = time.monotonic()
    manifest_media("md", f"# T\n\n{body}\n", tmp_path, max_bytes=2_000_000)
    assert time.monotonic() - started < 4


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


_FIRST = "<p>first paragraph text</p>"
_AFTER = "<p>after paragraph text</p>"


@pytest.mark.parametrize(
    ("fmt", "text", "owner_has", "owner_lacks"),
    [
        pytest.param("html", f'<h1>T</h1>{_FIRST}<p><img src="a.png"></p>{_AFTER}', "after paragraph", "first paragraph", id="img-alone-in-paragraph-takes-the-next-block"),
        pytest.param("html", f'<h1>T</h1>{_FIRST}<p>last paragraph text</p><p><img src="a.png"></p>', "last paragraph", "first paragraph", id="img-last-in-document-takes-the-last-block"),
        pytest.param("html", f'<h1>T</h1>{_FIRST}<table><tr><td>cell text <img src="a.png"></td></tr></table>{_AFTER}', "cell text", "first paragraph", id="img-in-table-takes-the-table"),
        pytest.param("html", f'<h1>T</h1>{_FIRST}<pre>code text <img src="a.png"></pre>{_AFTER}', "code text", "first paragraph", id="img-in-pre-takes-the-pre"),
        pytest.param("html", f'<h1>T</h1><div>intro loose text<pre class="mermaid">graph TD</pre></div>{_AFTER}', "graph TD", "intro loose", id="mermaid-pre-after-loose-text-takes-its-own-block"),
        pytest.param("html", f'<h1>T</h1><div>intro loose text<div class="mermaid">graph TD</div></div>{_AFTER}', "graph TD", "intro loose", id="mermaid-div-after-loose-text-takes-its-own-block"),
        pytest.param("docx", dx_parts(dx_p("first paragraph text") + dx_p("", dx_pic("rId1")) + dx_p("after paragraph text"), {"rId1": "a.png"}), "after paragraph", "first paragraph", id="docx-image-only-paragraph-takes-the-next-block"),
        pytest.param("docx", dx_parts(dx_p("first paragraph text") + dx_p("last paragraph text") + dx_p("", dx_pic("rId1")), {"rId1": "a.png"}), "last paragraph", "first paragraph", id="docx-image-last-in-document-takes-the-last-block"),
        pytest.param(
            "docx",
            dx_parts(dx_p("first paragraph text") + f"<w:tbl><w:tr><w:tc>{dx_p('cell text', dx_pic('rId1'))}</w:tc></w:tr></w:tbl>" + dx_p("after paragraph text"), {"rId1": "a.png"}),
            "cell text", "first paragraph", id="docx-picture-in-table-cell-takes-the-table",
        ),
        pytest.param(
            "docx",
            dx_parts(dx_p("first paragraph text") + dx_p("", dx_pic("rId1")), {"rId1": "a.png"}, header1=(dx_p("header words here"), None)),
            "header words", "first paragraph", id="docx-image-only-paragraph-at-end-of-body-takes-the-header-block",
        ),
        pytest.param(
            "docx",
            dx_parts(dx_p("first paragraph text") + dx_p("body closing text"), None, header1=(dx_p("header words here", dx_pic("rId1")), {"rId1": "h.png"})),
            "header words", "body closing", id="docx-header-picture-takes-the-header-block",
        ),
    ],
)
def test_reference_attaches_to_the_chunk_of_its_own_block(tmp_path, fmt, text, owner_has, owner_lacks):
    manifest, _ = manifest_media(fmt, text, tmp_path, max_bytes=20)
    assert len(manifest["chunks"]) > 2
    owner = next(c for c in manifest["chunks"] if c["id"] == manifest["media"][0]["chunk_id"])
    assert owner_has in owner["content"]
    assert owner_lacks not in owner["content"]


def test_no_media_markdown_manifest_equals_golden_byte_for_byte(tmp_path):
    source = write_golden_source("md", tmp_path / "src")
    manifest = json.loads(extract_manifest_text("md", source, tmp_path / "m.json"))
    assert "media" not in manifest
    assert manifest_text(normalise(manifest)) == read_golden("manifest_md.json")


_WITHOUT_HOOK = """
import importlib, json, sys
sys.path.insert(0, sys.argv[1])
module = importlib.import_module(sys.argv[3])
exec(sys.argv[4])
from pathlib import Path
print(json.dumps(module.extract(Path(sys.argv[2]), max_bytes=90)))
"""

_SPLIT_WORDS = " ".join(f"word{n}" for n in range(30))


@pytest.mark.parametrize(
    ("fmt", "module", "stub", "text", "count"),
    [
        pytest.param(
            "md", "extract_markdown", "module.collect_media = lambda blocks: None",
            "# T\n\nOne ![a](p.png) two.\n\n```mermaid\ngraph TD\n```\n\n<svg></svg> tail\n", 3, id="md",
        ),
        pytest.param(
            "html", "extract_html", "module.MediaCollector.apply = lambda self, blocks: None",
            f'<h1>T</h1><div>loose <pre class="mermaid">graph TD</pre></div><table><tr><td>c <img src="t.png"></td></tr></table>'
            f'<p>{_SPLIT_WORDS} <svg></svg></p><p><img src="z.png"></p>', 4, id="html",
        ),
        pytest.param(
            "docx", "extract_docx", "module.MediaCollector.apply = lambda self, blocks: None",
            dx_parts(
                dx_p("Price ", dx_pic("rId1"))
                + dx_p(_SPLIT_WORDS, '<w:del w:id="1"><w:r><w:delText>$100</w:delText></w:r></w:del><w:ins w:id="2"><w:r><w:t>$200</w:t></w:r></w:ins>', _CHART)
                + dx_p("", dx_pic("rId1")),
                {"rId1": "a.png", "rId6": "c.xml"},
            ),
            3, id="docx",
        ),
    ],
)
def test_media_changes_nothing_but_the_media_key(tmp_path, fmt, module, stub, text, count):
    source = write_source(fmt, text, tmp_path / "src")
    with_media = json.loads(extract_manifest_text(fmt, source, tmp_path / "m.json", 90))
    result = subprocess.run(
        [sys.executable, "-c", _WITHOUT_HOOK, str(SCRIPTS), str(source), module, stub],
        capture_output=True, text=True, check=True,
    )
    baseline = json.loads(result.stdout)
    assert len(with_media.pop("media")) == count
    assert with_media == baseline
    if fmt == "docx":
        content = " ".join(chunk["content"] for chunk in with_media["chunks"])
        assert "[deleted: $100]" in content
        assert "[inserted: $200]" in content


def test_no_media_html_manifest_equals_golden_byte_for_byte(tmp_path):
    source = write_golden_source("html", tmp_path / "src")
    manifest = json.loads(extract_manifest_text("html", source, tmp_path / "m.json"))
    assert "media" not in manifest
    assert manifest_text(normalise(manifest)) == read_golden("manifest_html.json")


def test_no_media_docx_manifest_equals_golden_byte_for_byte(tmp_path):
    source = write_golden_source("docx", tmp_path / "src")
    manifest = json.loads(extract_manifest_text("docx", source, tmp_path / "m.json"))
    assert "media" not in manifest
    assert manifest_text(normalise(manifest)) == read_golden("manifest_docx.json")
