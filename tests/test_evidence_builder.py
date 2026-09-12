import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from evidence_atoms import (
    AmbiguousEvidenceError,
    EvidenceBindingError,
    atom_id,
    bind_atom,
)

BUILD = SCRIPTS / "build_evidence.py"


def write_manifest(tmp_path: Path, contents: list[str]) -> Path:
    chunks = []
    cursor = 0
    for ordinal, content in enumerate(contents, start=1):
        raw = content.encode("utf-8")
        chunk_id = f"markdown-{ordinal:06d}-fixture"
        chunks.append({
            "id": chunk_id,
            "ordinal": ordinal,
            "content": content,
            "content_sha256": hashlib.sha256(raw).hexdigest(),
            "text_byte_start": cursor,
            "text_byte_end": cursor + len(raw),
            "locator": {"heading_path": [f"Chunk {ordinal}"], "blocks": [{"kind": "text"}]},
        })
        cursor += len(raw)
    manifest = {
        "schema_version": 1,
        "source": {"sha256": hashlib.sha256(b"fixture-source").hexdigest(), "format": "markdown"},
        "chunking": {"chunk_count": len(chunks), "max_bytes": 12000},
        "chunks": chunks,
        "extracted_text_bytes": cursor,
        "extracted_text_sha256": hashlib.sha256("".join(contents).encode("utf-8")).hexdigest(),
    }
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return path


def write_draft(tmp_path: Path, entries: list[dict]) -> Path:
    path = tmp_path / "draft.json"
    path.write_text(json.dumps({"entries": entries}, indent=2) + "\n", encoding="utf-8")
    return path


def run_builder(manifest: Path, draft: Path, out: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(BUILD), str(manifest), str(draft), "--out", str(out)],
        capture_output=True,
        text=True,
        check=False,
    )


def test_unique_quote_binds_to_exact_utf8_bytes():
    atom = bind_atom("md-1", "assertion", "alpha β gamma", {"text": "β gamma"})
    assert atom["chunk_byte_start"] == len("alpha ".encode("utf-8"))
    assert atom["chunk_byte_end"] == len("alpha β gamma".encode("utf-8"))
    assert atom["text"] == "β gamma"


def test_missing_quote_is_rejected_with_source_candidates():
    with pytest.raises(EvidenceBindingError, match="does not occur"):
        bind_atom("md-1", "assertion", "source has alpha", {"text": "source has omega"})


def test_repeated_quote_without_span_is_ambiguous():
    content = "same phrase\nmiddle\nsame phrase\n"
    with pytest.raises(AmbiguousEvidenceError, match=r"byte starts \[0, 19\]"):
        bind_atom("md-1", "assertion", content, {"text": "same phrase"})


def test_repeated_quote_with_exact_span_binds_requested_occurrence():
    content = "same phrase\nmiddle\nsame phrase\n"
    second = content.encode("utf-8").rfind(b"same phrase")
    atom = bind_atom(
        "md-1",
        "assertion",
        content,
        {"text": "same phrase", "chunk_byte_start": second, "chunk_byte_end": second + 11},
    )
    assert atom["chunk_byte_start"] == second


def test_partial_explicit_span_is_rejected():
    with pytest.raises(EvidenceBindingError, match="both start and end"):
        bind_atom("md-1", "assertion", "alpha", {"text": "alpha", "chunk_byte_start": 0})


def test_wrong_explicit_span_is_rejected():
    with pytest.raises(EvidenceBindingError, match="does not match"):
        bind_atom(
            "md-1",
            "assertion",
            "alpha beta",
            {"text": "beta", "chunk_byte_start": 0, "chunk_byte_end": 4},
        )


def test_utf8_multibyte_offsets_are_byte_offsets_not_character_offsets():
    atom = bind_atom("md-1", "assertion", "évidence", {"text": "vidence"})
    assert atom["chunk_byte_start"] == len("é".encode("utf-8"))


def test_atom_id_is_deterministic_and_kind_sensitive():
    a = atom_id("md-1", "assertion", 1, 4, "abc")
    b = atom_id("md-1", "assertion", 1, 4, "abc")
    c = atom_id("md-1", "constraint", 1, 4, "abc")
    assert a == b
    assert a != c


def test_builder_requires_exactly_one_verdict_per_manifest_chunk(tmp_path):
    manifest = write_manifest(tmp_path, ["alpha", "beta"])
    draft = write_draft(tmp_path, entries=[{"ordinal": 1, "outcome": "non_match", "reason": "checked"}])
    result = run_builder(manifest, draft, tmp_path / "out.json")
    assert result.returncode == 1
    assert "missing verdict" in result.stdout.lower()
    assert not (tmp_path / "out.json").exists()


def test_non_match_reason_is_required(tmp_path):
    manifest = write_manifest(tmp_path, ["alpha"])
    draft = write_draft(tmp_path, entries=[{"ordinal": 1, "outcome": "non_match", "reason": ""}])
    result = run_builder(manifest, draft, tmp_path / "out.json")
    assert result.returncode == 1
    assert "non_match reason" in result.stdout.lower()
    assert not (tmp_path / "out.json").exists()

FIXTURE = ROOT / "tests" / "fixtures" / "deepseek-first-run"


def _without_atom_ids(ledger: dict) -> dict:
    value = json.loads(json.dumps(ledger))
    for entry in value["entries"]:
        for plural in ("assertions", "constraints"):
            for atom in entry.get(plural, []):
                atom.pop("atom_id", None)
    value["schema_version"] = 1
    return value


def test_deepseek_first_run_rebinds_70_chunks_and_192_assertions(tmp_path):
    manifest = FIXTURE / "chunk-manifest.json"
    draft = FIXTURE / "draft-evidence.json"
    out = tmp_path / "chunk-evidence-v2.json"
    result = subprocess.run(
        [sys.executable, str(BUILD), str(manifest), str(draft), "--out", str(out)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    ledger = json.loads(out.read_text(encoding="utf-8"))
    assert ledger["schema_version"] == 2
    assert len(ledger["entries"]) == 70
    assert sum(len(e.get("assertions", [])) for e in ledger["entries"]) == 192

    known = json.loads((FIXTURE / "chunk-evidence-v1.json").read_text(encoding="utf-8"))
    assert _without_atom_ids(ledger) == known


def test_deepseek_prototype_is_fixture_only_not_runtime():
    prototype = FIXTURE / "prototype"
    assert {p.name for p in prototype.glob("*.py")} == {
        "build_evidence.py", "build_run.py", "dump_chunks.py",
        "assertions_a.py", "assertions_b.py", "assertions_c.py",
    }
    for path in (ROOT / "scripts").glob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert "tests.fixtures" not in text
        assert "deepseek-first-run/prototype" not in text
    manifest = json.loads((ROOT / "MANIFEST.json").read_text(encoding="utf-8"))
    assert "tests" not in manifest["payload"]
