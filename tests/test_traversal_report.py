import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

from media_helpers import normalise, read_golden

from layout import ROOT, SKILL_ROOT
VERIFY = SKILL_ROOT / "scripts" / "verify_run.py"
REPORT = SKILL_ROOT / "scripts" / "traversal_report.py"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_verify():
    spec = importlib.util.spec_from_file_location("verify_run_report", VERIFY)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def make_run(tmp_path: Path) -> dict:
    source_dir = tmp_path / "source"
    source_dir.mkdir(parents=True, exist_ok=True)
    source = source_dir / "source.html"
    source.write_text("<h1>A</h1><p>Alpha proof.</p><h1>B</h1><p>Beta caveat.</p>", encoding="utf-8")
    manifest_path = tmp_path / "evidence" / "chunk-manifest.json"
    result = subprocess.run([sys.executable, str(SKILL_ROOT / "scripts" / "extract_html.py"), str(source), "--run-root", str(tmp_path), "--max-bytes", "80"], capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stdout + result.stderr
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert len(manifest["chunks"]) == 2
    entries = []
    for chunk in manifest["chunks"]:
        content = chunk["content"]
        text = content.strip().split("\n")[-1]
        start = content.encode("utf-8").find(text.encode("utf-8"))
        entries.append({
            "chunk_id": chunk["id"],
            "ordinal": chunk["ordinal"],
            "chunk_sha256": chunk["content_sha256"],
            "outcome": "evidence",
            "assertions": [{"text": text, "chunk_byte_start": start, "chunk_byte_end": start + len(text.encode("utf-8"))}],
            "constraints": [],
        })
    ledger = {
        "schema_version": 1,
        "manifest_sha256": sha(manifest_path.read_bytes()),
        "source_sha256": sha(source.read_bytes()),
        "entries": entries,
    }
    evidence_path = tmp_path / "evidence" / "chunk-evidence.json"
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    evidence_path.write_text(json.dumps(ledger, indent=2) + "\n", encoding="utf-8")
    (tmp_path / "plan.md").write_text("evidence\n", encoding="utf-8")
    for name in ["skill-preflight.md", "source-manifest.md", "failure-ledger.md", "verification-log.txt", "format-qa.md"]:
        path = tmp_path / "evidence" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("evidence\n", encoding="utf-8")
    return {
        "_ledger_path": str(tmp_path / "run.json"),
        "source": {"uri": manifest["source"]["uri"], "local_path": str(source.resolve()), "sha256": sha(source.read_bytes()), "format": "html", "authority": "primary", "identity_verified": True},
        "fidelity": {"preserved": True, "substitutions": []},
        "preflight": {"skill_read": True, "required_references_read": True, "helper_help_read": True, "runtime_profile_resolved": True, "traversal_plan_ready": True},
        "plan": {"path": "plan.md", "nodes": ["read-document"]},
        "events": [{"type": "plan_written"}, {"type": "execution_started"}, {"type": "node_started", "node": "read-document"}, *[{"type": "chunk_verified", "chunk_id": c["id"], "chunk_sha256": c["content_sha256"], "evidence": "evidence/chunk-evidence.json"} for c in manifest["chunks"]], {"type": "node_passed", "node": "read-document", "evidence": "evidence/chunk-evidence.json"}, {"type": "verification_started"}, {"type": "verification_passed", "evidence": "evidence/verification-log.txt"}, {"type": "done"}],
        "chunking": {"manifest": "evidence/chunk-manifest.json", "manifest_sha256": sha(manifest_path.read_bytes()), "evidence_ledger": "evidence/chunk-evidence.json", "traversal_report": "deliverables/TRAVERSAL_REPORT.md"},
        "coverage": {"required": [c["id"] for c in manifest["chunks"]], "completed": [c["id"] for c in manifest["chunks"]]},
        "qa": {"required": ["html-structure"], "passed": ["html-structure"]},
        "deliverable": {"requested": "answer", "provided": True, "paths": [], "traversal_report": "deliverables/TRAVERSAL_REPORT.md"},
        "evidence": {"plan_status": "plan.md", "skill_preflight": "evidence/skill-preflight.md", "source_manifest": "evidence/source-manifest.md", "chunk_ledger": "evidence/chunk-evidence.json", "failure_ledger": "evidence/failure-ledger.md", "verification_log": "evidence/verification-log.txt", "format_qa": "evidence/format-qa.md", "traversal_report": "deliverables/TRAVERSAL_REPORT.md"},
    }


def write_report(tmp_path: Path) -> None:
    result = subprocess.run([sys.executable, str(REPORT), "--run-root", str(tmp_path)], capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stdout + result.stderr


def finding_codes(module, run: dict) -> list[str]:
    return module.codes_of(module.validate_findings(run))


def test_abstractive_string_assertions_are_rejected(tmp_path):
    module = load_verify()
    run = make_run(tmp_path)
    ledger_path = tmp_path / "evidence" / "chunk-evidence.json"
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    ledger["entries"][0]["assertions"] = ["This is a prose summary, not extractive evidence."]
    ledger_path.write_text(json.dumps(ledger, indent=2) + "\n", encoding="utf-8")
    assert "atoms.entry.type" in finding_codes(module, run)


def test_atomic_assertion_span_must_match_exact_chunk_bytes(tmp_path):
    module = load_verify()
    run = make_run(tmp_path)
    ledger_path = tmp_path / "evidence" / "chunk-evidence.json"
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    ledger["entries"][0]["assertions"][0]["text"] = "fabricated"
    ledger_path.write_text(json.dumps(ledger, indent=2) + "\n", encoding="utf-8")
    assert "atoms.span.mismatch" in finding_codes(module, run)


def test_traversal_report_is_required_and_must_be_reproducible(tmp_path):
    module = load_verify()
    run = make_run(tmp_path)
    missing = finding_codes(module, run)
    assert "coverage.report_path.missing" in missing
    assert "evidence.traversal_report.missing" in missing
    write_report(tmp_path)
    assert finding_codes(module, run) == []
    (tmp_path / "deliverables" / "TRAVERSAL_REPORT.md").write_text("# forged report\n", encoding="utf-8")
    assert "coverage.report.mismatch" in finding_codes(module, run)


def test_traversal_report_has_one_chunk_mapping_with_locator_outcome_and_atomic_text(tmp_path):
    make_run(tmp_path)
    write_report(tmp_path)
    text = (tmp_path / "deliverables" / "TRAVERSAL_REPORT.md").read_text(encoding="utf-8")
    manifest = json.loads((tmp_path / "evidence" / "chunk-manifest.json").read_text(encoding="utf-8"))
    for chunk in manifest["chunks"]:
        assert chunk["id"] in text
    assert "## Run summary" in text
    assert "## Chunk index" in text
    assert "## Chunk details" in text
    assert "| # | Chunk | Location | Kinds | Outcome | Atoms |" in text
    assert "- Locator:" in text
    assert "- Outcome:" in text
    assert "**Assertions**" in text
    assert "Alpha proof." in text
    assert "Beta caveat." in text


def test_first_run_report_is_grouped_complete_and_deterministic():
    from scripts.chunk_common import render_traversal_report

    fixture = ROOT / "tests" / "fixtures" / "deepseek-first-run"
    manifest = json.loads((fixture / "chunk-manifest.json").read_text(encoding="utf-8"))
    ledger = json.loads((fixture / "chunk-evidence-v1.json").read_text(encoding="utf-8"))
    first = render_traversal_report(manifest, ledger)
    second = render_traversal_report(manifest, ledger)
    assert first == second
    assert "## Run summary" in first
    assert "## Chunk index" in first
    assert "## Chunk details" in first
    atoms = sum(len(entry.get("assertions", [])) for entry in ledger["entries"])
    assert f"Assertions: {atoms}" in first
    assert first.count("\n### ") == len(ledger["entries"])
    assert first.count("\n- bytes `") == atoms
    for chunk in manifest["chunks"]:
        assert chunk["id"] in first

    # A chunk with multiple assertions gets one detail section, not one repeated locator row per atom.
    multi = next(entry for entry in ledger["entries"] if len(entry.get("assertions", [])) > 1)
    detail_start = first.index(f"### {multi['ordinal']:02d} · `{multi['chunk_id']}`")
    next_heading = first.find("\n### ", detail_start + 1)
    detail = first[detail_start: next_heading if next_heading >= 0 else None]
    assert detail.count("<details><summary>Full locator</summary>") == 1


def _normalised_run(tmp_path: Path):
    make_run(tmp_path)
    manifest = json.loads((tmp_path / "evidence" / "chunk-manifest.json").read_text(encoding="utf-8"))
    ledger = json.loads((tmp_path / "evidence" / "chunk-evidence.json").read_text(encoding="utf-8"))
    return normalise(manifest, ledger)


def test_no_media_manifest_ledger_and_report_equal_their_goldens(tmp_path):
    from scripts.chunk_common import render_traversal_report

    manifest, ledger = _normalised_run(tmp_path)
    assert "media" not in manifest
    assert "media" not in ledger
    assert json.dumps(ledger, indent=2) + "\n" == read_golden("ledger.json")
    assert render_traversal_report(manifest, ledger) == read_golden("TRAVERSAL_REPORT.md")


_MEDIA_HEAD = (
    "## Media\n"
    "\n"
    "Chunk is the first chunk of the nearest following block, and the coverage above is of extracted text only.\n"
    "\n"
    "| Media | Chunk | Kind | Syntax | Reference | Alt | Disposition | Tool or reason |\n"
    "|---|---|---|---|---|---|---|---|\n"
)


@pytest.mark.parametrize(
    ("dispositions", "counts", "last_cells"),
    [
        pytest.param(
            [
                {"id": "media-0001", "disposition": "read", "tool": "vision", "summary": "a chart"},
                {"id": "media-0002", "disposition": "not_read", "reason": "decorative"},
            ],
            (1, 1, 1),
            ("read | vision", "not_read | decorative", "missing | "),
            id="one-of-each",
        ),
        pytest.param(None, (0, 0, 3), ("missing | ",) * 3, id="no-ledger-media-key"),
    ],
)
def test_report_lists_each_media_with_its_disposition_and_counts_missing(tmp_path, dispositions, counts, last_cells):
    from scripts.chunk_common import render_traversal_report

    manifest, ledger = _normalised_run(tmp_path)
    first = manifest["chunks"][0]["id"]
    manifest["media"] = [
        {"id": "media-0001", "chunk_id": first, "kind": "image", "syntax": "md_image", "ref": "p1.png", "alt": "a|b"},
        {"id": "media-0002", "chunk_id": first, "kind": "svg", "syntax": "html_svg", "ref": None, "alt": None},
        {"id": "media-0003", "chunk_id": first, "kind": "diagram", "syntax": "fence_diagram", "ref": None, "alt": "flow"},
    ]
    if dispositions is not None:
        ledger["media"] = dispositions
    report = render_traversal_report(manifest, ledger)
    read, not_read, missing = counts
    summary = (
        f"- Media references: 3\n- Media read: {read}\n"
        f"- Media not read: {not_read}\n- Media without disposition: {missing}\n"
    )
    assert summary in report
    prefixes = (
        f"| `media-0001` | `{first}` | image | md_image | p1.png | a\\|b | ",
        f"| `media-0002` | `{first}` | svg | html_svg |  |  | ",
        f"| `media-0003` | `{first}` | diagram | fence_diagram |  | flow | ",
    )
    rows = "".join(f"{prefix}{cells} |\n" for prefix, cells in zip(prefixes, last_cells, strict=True))
    # The whole section, from its heading to the blank line before "## Chunk index".
    assert report[report.index("## Media") : report.index("## Chunk index")] == _MEDIA_HEAD + rows + "\n"


def test_deliverable_contract_makes_traversal_report_user_visible():
    body = (SKILL_ROOT / "references" / "deliverable.md").read_text(encoding="utf-8").lower()
    assert "traversal_report.md" in body
    assert "user-visible" in body
    assert "requested" in body and "deliverable" in body
