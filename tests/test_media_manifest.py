import json

import pytest

from media_helpers import extract_manifest_text, manifest_text, normalise, read_golden, write_golden_source
from scripts.chunk_common import Block, MediaCollector, build_manifest, pack_blocks

# ---------------------------------------------------------------- no-media guarantees


@pytest.mark.parametrize("fmt", ["md", "html", "docx"])
def test_no_media_manifest_equals_golden_byte_for_byte(tmp_path, fmt):
    source = write_golden_source(fmt, tmp_path / "src")
    raw = extract_manifest_text(fmt, source, tmp_path / "m.json")
    manifest = json.loads(raw)
    assert "media" not in manifest
    # The extractor's own file formatting (indent, ensure_ascii, trailing newline) is part of the
    # contract: only source.path and source.uri differ between machines, and they are normalised.
    assert raw == manifest_text(manifest)
    assert manifest_text(normalise(manifest)) == read_golden(f"manifest_{fmt}.json")


# ---------------------------------------------------------------- collector and manifest


def _block(text, heading="A", **locator):
    return Block(text, {"heading_path": [heading], **locator})


def _manifest(tmp_path, blocks, collector=None, max_bytes=1000):
    source = tmp_path / "source.md"
    source.write_bytes(b"source")
    if collector is not None:
        collector.apply(blocks)
    return build_manifest(
        source, "markdown", pack_blocks(blocks, max_bytes),
        strategy="test", max_bytes=max_bytes,
    )


def _three_blocks():
    return [_block("one\n", "A"), _block("two\n", "B"), _block("three\n", "C")]


@pytest.mark.parametrize(
    ("blocks", "position", "expected_text"),
    [
        pytest.param(_three_blocks(), 1, "two\n", id="at-position"),
        pytest.param([_block("one\n"), Block("", {}), _block("three\n", "C")], 1, "three\n", id="skips-empty-block"),
        pytest.param(_three_blocks(), 9, "three\n", id="past-the-end-uses-last-block"),
    ],
)
def test_entry_attaches_to_first_nonempty_block_at_or_after_position(tmp_path, blocks, position, expected_text):
    collector = MediaCollector()
    collector.add(position, "image", "md_image", "p.png", "alt")
    manifest = _manifest(tmp_path, blocks, collector)
    [entry] = manifest["media"]
    owner = next(c for c in manifest["chunks"] if c["content"] == expected_text)
    assert entry["chunk_id"] == owner["id"]


def test_collector_without_blocks_is_a_noop():
    collector = MediaCollector()
    collector.add(0, "image", "md_image", "p.png")
    collector.apply([])
    collector.apply([Block("", {})])


def test_media_does_not_change_chunk_text_ids_or_hashes(tmp_path):
    plain = _manifest(tmp_path, _three_blocks())
    collector = MediaCollector()
    collector.add(0, "image", "md_image", "p.png", "alt")
    collector.add(2, "svg", "html_svg")
    with_media = _manifest(tmp_path, _three_blocks(), collector)
    assert len(with_media["media"]) == 2
    without_key = {k: v for k, v in with_media.items() if k != "media"}
    assert without_key == plain
    assert "media" not in json.dumps(with_media["chunks"])


def test_media_in_a_split_block_is_listed_once_on_fragment_one(tmp_path):
    collector = MediaCollector()
    collector.add(0, "image", "md_image", "p.png")
    manifest = _manifest(tmp_path, [_block("word " * 30)], collector, max_bytes=40)
    assert len(manifest["chunks"]) > 2
    [entry] = manifest["media"]
    assert entry["chunk_id"] == manifest["chunks"][0]["id"]


def test_manifest_media_ids_follow_manifest_order_and_key_is_absent_when_empty(tmp_path):
    assert "media" not in _manifest(tmp_path, _three_blocks(), MediaCollector())
    collector = MediaCollector()
    collector.add(2, "image", "md_image", "c.png")
    collector.add(0, "svg", "html_svg")
    collector.add(0, "diagram", "fence_diagram")
    manifest = _manifest(tmp_path, _three_blocks(), collector)
    chunks = [c["id"] for c in manifest["chunks"]]
    assert [(m["id"], m["chunk_id"], m["syntax"]) for m in manifest["media"]] == [
        ("media-0001", chunks[0], "html_svg"),
        ("media-0002", chunks[0], "fence_diagram"),
        ("media-0003", chunks[2], "md_image"),
    ]
    assert list(manifest["media"][0]) == ["id", "chunk_id", "kind", "syntax", "ref", "alt"]


def test_atomic_block_media_is_moved_out_of_the_locator(tmp_path):
    collector = MediaCollector()
    collector.add(0, "image", "md_image", "p.png")
    manifest = _manifest(tmp_path, [Block("| a |\n", {"heading_path": ["A"]}, "table")], collector)
    assert manifest["media"][0]["chunk_id"] == manifest["chunks"][0]["id"]
    assert "media" not in manifest["chunks"][0]["locator"]


@pytest.mark.parametrize(
    ("ref", "alt", "expected_ref", "expected_alt"),
    [
        pytest.param("data:image/png;base64," + "A" * 500, "a\n  b\tc", "data:image/png", "a b c", id="data-uri-and-alt-whitespace"),
        pytest.param("x" * 300, "y" * 300, "x" * 200, "y" * 200, id="caps-at-200"),
        pytest.param(None, None, None, None, id="nulls-stay-null"),
    ],
)
def test_media_ref_and_alt_are_normalised(tmp_path, ref, alt, expected_ref, expected_alt):
    collector = MediaCollector()
    collector.add(0, "image", "md_image", ref, alt)
    [entry] = _manifest(tmp_path, [_block("one\n")], collector)["media"]
    assert (entry["ref"], entry["alt"]) == (expected_ref, expected_alt)
