from pathlib import Path

import pytest

from layout import ROOT, SKILL_ROOT

DOD = "references/definition-of-done.md"
EVIDENCE = "references/evidence.md"
DELIVERABLE = "references/deliverable.md"
RUNTIME = "references/runtime-profiles.md"
DEPENDENCIES = "references/dependencies.md"
MARKDOWN = "references/lengthy-markdown.md"
RUN_WORKSPACE = "references/run-workspace.md"
EXHAUSTIVE = "exhaustive-document-traversal"
PLANNING = "planning-document-traversal"
EXECUTING = "executing-document-traversal"
VERIFYING = "verifying-exhaustive-traversal"
DEBUGGING = "debugging-document-workflows"


def text(rel: str, base: Path = SKILL_ROOT) -> str:
    return (base / rel).read_text(encoding="utf-8")


# (instruction an agent executes, file that states it, module whose SKILL.md
# loads that file; None for files that are not loaded by a phase module).
# P edits these rows when it moves prose; the test body stays.
INSTRUCTIONS = [
    ("exactly one verified `evidence` or explicit `non_match` verdict", "SKILL.md", None),
    ("**exactly one** bound entry in `evidence/chunk-evidence.json`", DOD, VERIFYING),
    ("all 12 discrete `chunk_verified` events", DOD, VERIFYING),
    ("`done` at chunk 4 is premature", DOD, VERIFYING),
    ("the traversal report is `deliverables/TRAVERSAL_REPORT.md`", DOD, VERIFYING),
    ("outside its canonical run-root namespace, the run is **NOT DONE**", DOD, VERIFYING),
    ('"manifest_sha256": "..."', EVIDENCE, EXECUTING),
    ("`chunk_byte_start`/`chunk_byte_end`", EVIDENCE, EXECUTING),
    ("**Schema v1 remains accepted**", EVIDENCE, EXECUTING),
    ("deterministic `atom_id`", EVIDENCE, EXECUTING),
    ("the draft must provide an **explicit byte span**", EVIDENCE, EXECUTING),
    ("exactly one `chunk_verified` event per canonical manifest chunk", EVIDENCE, EXECUTING),
    ("`scripts/inspect_chunks.py`", DELIVERABLE, PLANNING),
    ("python <skill-root>/scripts/extract_html.py SOURCE --run-root <run-root>", RUN_WORKSPACE, EXHAUSTIVE),
    ("python <skill-root>/scripts/extract_markdown.py SOURCE --run-root <run-root>", RUN_WORKSPACE, EXHAUSTIVE),
    ("python <skill-root>/scripts/extract_docx.py SOURCE --run-root <run-root>", RUN_WORKSPACE, EXHAUSTIVE),
    ("python <skill-root>/scripts/extract_pdf.py SOURCE --run-root <run-root>", RUN_WORKSPACE, EXHAUSTIVE),
    ("`# / ## / ### / #### / ##### / ######`", MARKDOWN, EXHAUSTIVE),
    ("`oversize_atomic: true`", MARKDOWN, EXHAUSTIVE),
    ("`scripts/extract_markdown.py`", MARKDOWN, EXHAUSTIVE),
    ("`scripts/extract_html.py`", "references/html.md", EXHAUSTIVE),
    ("`scripts/extract_pdf.py`", "references/pdf.md", EXHAUSTIVE),
    ("`scripts/extract_docx.py`", "references/docx.md", EXHAUSTIVE),
    ("**every non-skipped DOM text node exactly once**", "references/html.md", EXHAUSTIVE),
    ("paragraph styles named `Heading1` through `Heading6`", "references/docx.md", EXHAUSTIVE),
    ("exactly one ordered `chunk_verified` event per canonical emitted chunk", RUNTIME, EXHAUSTIVE),
    ("Text backends cannot justify an `ocr-verified` QA claim", "references/pdf.md", EXHAUSTIVE),
    ("copy the extractor manifest's `extraction` object into `run.json`", "references/pdf.md", EXHAUSTIVE),
    ("**every Markdown file in that selected tree in full before execution**", "references/oai-native.md", EXHAUSTIVE),
    ("**do not attempt a fourth fix**", "references/failure-recovery.md", DEBUGGING),
    ("Do not require an external document skill merely to perform basic exhaustive text extraction", DEPENDENCIES, EXHAUSTIVE),
    ("do not substitute a derivative for the source", "references/control-flow.md", EXHAUSTIVE),
]


@pytest.mark.parametrize(("instruction", "rel", "module"), INSTRUCTIONS, ids=[row[0] for row in INSTRUCTIONS])
def test_required_instruction_is_stated_where_its_phase_loads_it(instruction, rel, module):
    assert instruction in text(rel)
    if module is not None:
        assert f"](../../{rel})" in text(f"skills/{module}/SKILL.md")


def test_readme_explains_chunk_contract_access_and_future_scope():
    body = text("README.md", ROOT).lower()
    assert "what is a chunk" in body
    assert "chunk id" in body
    assert "evidence/chunk-manifest.json" in body
    assert "traversal_report.md" in body
    assert "markdown" in body and "heading" in body
    assert "pdf" in body and "page" in body
    assert "docx" in body and "ooxml" in body
    assert "html" in body and "heading" in body
    assert "xlsx" in body and "csv" in body and "future" in body
    assert "derived" in body and ("reconstruct" in body or "rebuild" in body)


def test_readme_documents_receipt_ownership_and_evidence_schema():
    readme = text("README.md", ROOT).lower()
    assert "receipt-owned" in readme and "install root" in readme
    assert "schema v2" in readme and "atom_id" in readme


def test_control_flow_keeps_the_exhaustive_obligation_against_a_forged_manifest():
    control = text("references/control-flow.md").lower()
    assert "twelve emitted chunks require twelve" in control
    assert "forged smaller manifest" in control


def test_run_workspace_namespaces_every_emitted_artifact():
    evidence = text("references/evidence.md")
    deliverable = text("references/deliverable.md")
    assert "evidence/chunk-manifest.json" in evidence
    assert "evidence/chunk-evidence.json" in evidence
    assert "deliverables/TRAVERSAL_REPORT.md" in evidence
    assert "deliverables/TRAVERSAL_REPORT.md" in deliverable
    assert "<run-root>/deliverables/" in deliverable
