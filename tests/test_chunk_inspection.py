import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from chunk_view import compact_locator
from inspect_chunks import main as inspect_main


def write_inspection_manifest(tmp_path: Path, chunks: list[dict]) -> Path:
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps({"chunks": chunks}, indent=2) + "\n", encoding="utf-8")
    return path


def test_summary_prints_ordinal_id_kinds_size_and_location(tmp_path, capsys):
    manifest = write_inspection_manifest(tmp_path, [{
        "id": "markdown-000001-fixture",
        "ordinal": 1,
        "content": "proof",
        "text_byte_start": 0,
        "text_byte_end": 5,
        "locator": {"heading_path": ["A", "B"], "blocks": [{"kind": "text"}]},
    }])
    assert inspect_main([str(manifest), "--summary"]) == 0
    output = capsys.readouterr().out
    assert "01" in output
    assert "markdown-000001" in output
    assert "[text]" in output
    assert "A > B" in output
    assert "5B" in output


def test_detail_range_prints_only_requested_ordinals(tmp_path, capsys):
    manifest = write_inspection_manifest(tmp_path, [
        {"id": f"markdown-{n:06d}-fixture", "ordinal": n, "content": f"chunk {n}",
         "text_byte_start": (n - 1) * 7, "text_byte_end": n * 7,
         "locator": {"heading_path": [f"H{n}"], "blocks": [{"kind": "text"}]}}
        for n in range(1, 4)
    ])
    assert inspect_main([str(manifest), "--from", "2", "--to", "2"]) == 0
    output = capsys.readouterr().out
    assert "CHUNK 02" in output
    assert "CHUNK 01" not in output
    assert "CHUNK 03" not in output
    assert "chunk 2" in output


def test_compact_locator_prefers_heading_path_then_page_then_part():
    assert compact_locator({"locator": {"heading_path": ["A", "B"]}}) == "A > B"
    assert compact_locator({"locator": {"pages": [3]}}) == "page 3"
    assert compact_locator({"locator": {"pages": [3, 4]}}) == "pages 3-4"
    assert compact_locator({"locator": {"part": "word/header1.xml"}}) == "word/header1.xml"


def test_compact_locator_falls_back_to_canonical_json():
    assert compact_locator({"locator": {"z": 2, "a": 1}}) == '{"a":1,"z":2}'


def test_summary_rejects_malformed_manifest(tmp_path, capsys):
    path = tmp_path / "bad.json"
    path.write_text(json.dumps({"chunks": "nope"}), encoding="utf-8")
    assert inspect_main([str(path), "--summary"]) == 1
    assert "FAIL: manifest must contain a chunks list" in capsys.readouterr().out
