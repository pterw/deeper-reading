"""The verifier enforces media dispositions (F5) on a run built by the real Markdown extractor."""

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.verification_findings import codes_of
from scripts.verify_run import _build_dod_from_findings, validate_findings
from tests.run_fixture import REQUIRED_EVIDENCE_FILES, valid_run

from layout import SKILL_ROOT
SCRIPTS = SKILL_ROOT / "scripts"

SOURCE = "# Title\n\nalpha text\n\n![diagram](diagram.png)\n\n```mermaid\ngraph TD\n```\n"
READ = {"id": "media-0001", "disposition": "read", "tool": "vision", "summary": "a diagram"}
NOT_READ = {"id": "media-0002", "disposition": "not_read", "reason": "decorative"}
CODES = ["missing", "unknown", "duplicate", "invalid"]


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def _run_script(script: str, *args: object) -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / script), *map(str, args)],
        capture_output=True, text=True, check=False, timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def _entry(chunk: dict) -> dict:
    base = {"chunk_id": chunk["id"], "ordinal": chunk["ordinal"], "chunk_sha256": chunk["content_sha256"]}
    start = chunk["content"].encode("utf-8").find(b"alpha")
    if start < 0:
        return {**base, "outcome": "non_match", "reason": "no claim here"}
    atom = {"text": "alpha", "chunk_byte_start": start, "chunk_byte_end": start + 5}
    return {**base, "outcome": "evidence", "assertions": [atom], "constraints": []}


def _media_run(tmp_path: Path, dispositions=None) -> dict:
    """A done-sealed Markdown run: manifest, ledger and report all from the real scripts."""
    run = valid_run(tmp_path)
    source = tmp_path / "source" / "source.md"
    source.write_text(SOURCE, encoding="utf-8")
    uri = run["source"]["uri"]
    _run_script("extract_markdown.py", source, "--run-root", tmp_path, "--max-bytes", 4096, "--source-uri", uri)
    manifest_path = tmp_path / "evidence" / "chunk-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    chunks = manifest["chunks"]
    entries = [_entry(chunk) for chunk in chunks]
    ledger = {
        "schema_version": 1,
        "manifest_sha256": _sha(manifest_path.read_bytes()),
        "source_sha256": manifest["source"]["sha256"],
        "entries": entries,
    }
    if dispositions is not None:
        ledger["media"] = dispositions
    _write_json(tmp_path / "evidence" / "chunk-evidence.json", ledger)
    _run_script("traversal_report.py", "--run-root", tmp_path)
    run["source"].update(format="markdown", local_path=str(source.resolve()), sha256=_sha(source.read_bytes()))
    run["chunking"]["manifest_sha256"] = _sha(manifest_path.read_bytes())
    ids = [chunk["id"] for chunk in chunks]
    run["plan"]["nodes"] = ["acquire", *ids]
    run["coverage"] = {"required": ids, "completed": ids}
    ledger_ref = "evidence/chunk-evidence.json"
    per_chunk = [
        event
        for chunk in chunks
        for event in (
            {"type": "node_started", "node": chunk["id"]},
            {"type": "chunk_verified", "chunk_id": chunk["id"], "chunk_sha256": chunk["content_sha256"],
             "evidence": ledger_ref},
            {"type": "node_passed", "node": chunk["id"], "evidence": ledger_ref},
        )
    ]
    run["events"][4:7] = per_chunk
    return run


def _codes(run: dict) -> list[str]:
    return codes_of(validate_findings(run))


def test_the_fixture_run_records_two_media_and_passes_with_full_dispositions(tmp_path):
    run = _media_run(tmp_path, [READ, NOT_READ])
    manifest = json.loads((tmp_path / "evidence" / "chunk-manifest.json").read_text(encoding="utf-8"))
    assert [m["id"] for m in manifest["media"]] == ["media-0001", "media-0002"]
    assert validate_findings(run) == []


def test_a_run_without_dispositions_fails_each_media_id_and_format_qa(tmp_path):
    run = _media_run(tmp_path)
    findings = validate_findings(run)
    missing = [f for f in findings if f.code == "media.disposition.missing"]
    assert [f.detail for f in missing] == ["media-0001", "media-0002"]
    dod = _build_dod_from_findings(run, findings)
    assert dod["predicates"]["format_qa_complete"] is False


@pytest.mark.parametrize(
    ("dispositions", "code"),
    [
        pytest.param([READ], "media.disposition.missing", id="missing"),
        pytest.param([READ, NOT_READ, {**NOT_READ, "id": "media-0009"}], "media.disposition.unknown", id="unknown"),
        pytest.param([READ, NOT_READ, READ], "media.disposition.duplicate", id="duplicate"),
        pytest.param([READ, {"id": "media-0002", "disposition": "not_read", "reason": " "}],
                     "media.disposition.invalid", id="invalid"),
    ],
)
def test_each_disposition_problem_emits_its_code_under_format_qa_complete(tmp_path, dispositions, code):
    run = _media_run(tmp_path, dispositions)
    findings = validate_findings(run)
    assert {f.predicate for f in findings if f.code == code} == {"format_qa_complete"}
    dod = _build_dod_from_findings(run, findings)
    assert code in dod["codes"]
    assert dod["predicates"]["format_qa_complete"] is False
    flipped = {name for name, ok in dod["predicates"].items() if not ok}
    assert flipped <= {"format_qa_complete", "machine_checks_passed"}


def test_every_media_code_reaches_dod_codes_and_flips_only_format_qa(tmp_path):
    seen: set[str] = set()
    everything = [READ, READ, {**NOT_READ, "id": "media-0009"}, {"id": "media-0002", "disposition": "bogus"}]
    for index, dispositions in enumerate([None, everything]):
        run = _media_run(tmp_path / f"r{index}", dispositions)
        dod = _build_dod_from_findings(run, validate_findings(run))
        seen |= {c for c in dod["codes"] if c.startswith("media.disposition.")}
        assert {n for n, ok in dod["predicates"].items() if not ok} == {"format_qa_complete", "machine_checks_passed"}
    assert seen == {f"media.disposition.{c}" for c in CODES}


def test_a_source_without_media_passes_with_no_media_key_anywhere(tmp_path):
    run = valid_run(tmp_path)
    assert validate_findings(run) == []
    for name in ("chunk-manifest.json", "chunk-evidence.json"):
        assert "media" not in json.loads((tmp_path / "evidence" / name).read_text(encoding="utf-8"))
    report = (tmp_path / REQUIRED_EVIDENCE_FILES["traversal_report"]).read_text(encoding="utf-8")
    assert "Media" not in report


def test_a_manifest_changed_after_the_ledger_was_built_stales_the_ledger(tmp_path):
    run = _media_run(tmp_path, [READ, NOT_READ])
    manifest_path = tmp_path / "evidence" / "chunk-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["media"][0]["alt"] = "edited"
    _write_json(manifest_path, manifest)
    run["chunking"]["manifest_sha256"] = _sha(manifest_path.read_bytes())
    assert "coverage.ledger.manifest_sha.mismatch" in _codes(run)


def _strip_media_by_hand(tmp_path: Path, run: dict) -> None:
    """Remove `media` from the manifest and rebind every hash a careful forger would fix."""
    manifest_path = tmp_path / "evidence" / "chunk-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    del manifest["media"]
    _write_json(manifest_path, manifest)
    manifest_sha = _sha(manifest_path.read_bytes())
    ledger_path = tmp_path / "evidence" / "chunk-evidence.json"
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    ledger["manifest_sha256"] = manifest_sha
    ledger.pop("media", None)
    _write_json(ledger_path, ledger)
    run["chunking"]["manifest_sha256"] = manifest_sha
    _run_script("traversal_report.py", "--run-root", tmp_path)


def test_a_manifest_with_media_removed_by_hand_fails_reproduction(tmp_path):
    run = _media_run(tmp_path)
    _strip_media_by_hand(tmp_path, run)
    assert "reproduction.mismatch" in _codes(run)


def test_a_manifest_that_predates_media_gets_the_re_extract_hint(tmp_path):
    run = _media_run(tmp_path)
    _strip_media_by_hand(tmp_path, run)
    [mismatch] = [f for f in validate_findings(run) if f.code == "reproduction.mismatch"]
    assert "manifest predates media recording; re-extract" in mismatch.message


def test_a_genuine_mismatch_does_not_get_the_media_hint(tmp_path):
    run = _media_run(tmp_path, [READ, NOT_READ])
    manifest_path = tmp_path / "evidence" / "chunk-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["chunking"]["strategy"] = "forged"
    _write_json(manifest_path, manifest)
    [mismatch] = [f for f in validate_findings(run) if f.code == "reproduction.mismatch"]
    assert "predates media" not in mismatch.message
