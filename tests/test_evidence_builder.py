import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from layout import ROOT, SKILL_ROOT
SCRIPTS = SKILL_ROOT / "scripts"
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


def test_deepseek_first_run_rebinds_to_the_known_good_ledger(tmp_path):
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

    known = json.loads((FIXTURE / "chunk-evidence-v1.json").read_text(encoding="utf-8"))
    assert _without_atom_ids(ledger) == known


MEDIA_REFS = [
    {"id": "media-0001", "chunk_id": "markdown-000001-fixture", "kind": "image", "syntax": "md_image", "ref": "a.png", "alt": None},
    {"id": "media-0002", "chunk_id": "markdown-000001-fixture", "kind": "svg", "syntax": "html_svg", "ref": None, "alt": None},
]
READ = {"id": "media-0001", "disposition": "read", "tool": "vision", "summary": "a bar chart"}
NOT_READ = {"id": "media-0002", "disposition": "not_read", "reason": "decorative"}


def _media_manifest(tmp_path: Path) -> Path:
    path = write_manifest(tmp_path, ["alpha"])
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["media"] = MEDIA_REFS
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return path


def _media_draft(tmp_path: Path, media) -> Path:
    path = tmp_path / "draft.json"
    entries = [{"ordinal": 1, "outcome": "non_match", "reason": "checked"}]
    path.write_text(json.dumps({"entries": entries, "media": media}) + "\n", encoding="utf-8")
    return path


@pytest.mark.parametrize(
    ("media", "code"),
    [
        pytest.param([READ], "media.disposition.missing", id="missing"),
        pytest.param([READ, NOT_READ, {**NOT_READ, "id": "media-0007"}], "media.disposition.unknown", id="unknown"),
        pytest.param([READ, NOT_READ, dict(READ)], "media.disposition.duplicate", id="duplicate"),
    ],
)
def test_builder_rejects_bad_dispositions_without_writing_a_ledger(tmp_path, media, code):
    out = tmp_path / "out.json"
    result = run_builder(_media_manifest(tmp_path), _media_draft(tmp_path, media), out)
    assert result.returncode == 1
    assert code in result.stdout
    assert not out.exists()


def test_builder_copies_valid_dispositions_into_the_ledger(tmp_path):
    out = tmp_path / "out.json"
    result = run_builder(_media_manifest(tmp_path), _media_draft(tmp_path, [READ, NOT_READ]), out)
    assert result.returncode == 0, result.stdout
    assert json.loads(out.read_text(encoding="utf-8"))["media"] == [READ, NOT_READ]


def _golden_ledger_inputs(tmp_path: Path):
    sys.path.insert(0, str(ROOT / "tests"))
    from media_helpers import manifest_text, normalise, read_golden

    source = tmp_path / "source.html"
    source.write_text("<h1>A</h1><p>Alpha proof.</p><h1>B</h1><p>Beta caveat.</p>", encoding="utf-8")
    extracted = tmp_path / "raw-manifest.json"
    subprocess.run(
        [sys.executable, str(SCRIPTS / "extract_html.py"), str(source), "--out", str(extracted), "--max-bytes", "80"],
        capture_output=True, text=True, check=True,
    )
    manifest = tmp_path / "manifest.json"
    manifest.write_bytes(manifest_text(normalise(json.loads(extracted.read_text(encoding="utf-8")))).encode("utf-8"))
    entries = [
        {"ordinal": 1, "outcome": "evidence", "assertions": [{"text": "Alpha proof."}]},
        {"ordinal": 2, "outcome": "evidence", "assertions": [{"text": "Beta caveat."}]},
    ]
    return manifest, entries, read_golden("ledger.json")


@pytest.mark.parametrize("draft_media", [None, []], ids=["no-media-key", "empty-media-list"])
def test_no_media_manifest_builds_a_ledger_without_media_key(tmp_path, draft_media):
    manifest, entries, golden = _golden_ledger_inputs(tmp_path)
    draft = tmp_path / "draft.json"
    body = {"entries": entries} if draft_media is None else {"entries": entries, "media": draft_media}
    draft.write_text(json.dumps(body) + "\n", encoding="utf-8")
    out = tmp_path / "out.json"
    result = run_builder(manifest, draft, out)
    assert result.returncode == 0, result.stdout
    ledger = json.loads(out.read_text(encoding="utf-8"))
    assert "media" not in ledger
    # The golden ledger is schema 1 and carries no atom ids; the builder emits schema 2 with ids.
    assert json.dumps(_without_atom_ids(ledger), indent=2) + "\n" == golden
