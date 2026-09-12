from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def text(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_root_skill_states_exhaustive_traversal_is_mission_and_chunking_is_mechanism():
    body = text("SKILL.md").lower()
    assert "exhaustive traversal" in body
    assert "chunking is the mechanism" in body
    assert "every emitted chunk" in body


def test_definition_of_done_uses_extractor_manifest_as_authoritative_coverage_universe():
    body = text("references/definition-of-done.md").lower()
    assert "extractor manifest" in body
    assert "authoritative coverage universe" in body
    assert "exactly one" in body and "evidence" in body
    assert "premature" in body and "done" in body


def test_evidence_contract_has_single_machine_chunk_evidence_ledger_bound_to_manifest():
    body = text("references/evidence.md").lower()
    assert "chunk-evidence.json" in body
    assert "evidence/chunk-manifest.json" in body
    assert "manifest_sha256" in body
    assert "non_match" in body
    assert "coverage" in body and "optional" in body


def test_lengthy_markdown_contract_is_structural_and_atomic():
    body = text("references/lengthy-markdown.md").lower()
    assert "# / ## / ###" in body
    assert "fenced code" in body and "atomic" in body
    assert "table" in body and "atomic" in body
    assert "oversize_atomic" in body
    assert "extract_markdown.py" in body


def test_format_references_use_bundled_portable_extractors():
    assert "scripts/extract_html.py" in text("references/html.md")
    assert "scripts/extract_pdf.py" in text("references/pdf.md")
    assert "scripts/extract_docx.py" in text("references/docx.md")


def test_portable_profile_owns_basic_extraction_and_external_skills_are_enhancements():
    body = text("references/runtime-profiles.md").lower()
    assert "bundled" in body and "extract" in body
    assert "basic" in body and "text" in body
    assert "optional" in body or "advanced" in body
    assert "visual" in body or "ocr" in body

def test_dependencies_do_not_require_external_document_skills_for_basic_portable_text_extraction():
    body = text("references/dependencies.md").lower()
    assert "bundled" in body and "extract" in body
    assert "basic" in body and "text" in body
    assert "external" in body and ("advanced" in body or "visual" in body)


def test_evidence_contract_requires_atomic_extractive_spans_and_user_visible_report():
    evidence = text("references/evidence.md").lower()
    deliverable = text("references/deliverable.md").lower()
    dod = text("references/definition-of-done.md").lower()
    assert "atomic extractive" in evidence
    assert "chunk_byte_start" in evidence and "chunk_byte_end" in evidence
    assert "traversal_report.md" in evidence
    assert "traversal_report.md" in deliverable and "user-visible" in deliverable
    assert "chunk_verified" in dod


def test_runtime_and_control_flow_preserve_exhaustive_product_invariant():
    runtime = text("references/runtime-profiles.md").lower()
    control = text("references/control-flow.md").lower()
    assert "atomic extractive" in runtime
    assert "chunk_verified" in runtime
    assert "traversal_report.md" in runtime
    assert "twelve emitted chunks require twelve" in control
    assert "forged smaller manifest" in control


def test_readme_explains_chunk_contract_access_and_future_scope():
    body = text("README.md").lower()
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


def test_run_workspace_namespaces_every_emitted_artifact():
    evidence = text("references/evidence.md")
    deliverable = text("references/deliverable.md")
    assert "evidence/chunk-manifest.json" in evidence
    assert "evidence/chunk-evidence.json" in evidence
    assert "deliverables/TRAVERSAL_REPORT.md" in evidence
    assert "deliverables/TRAVERSAL_REPORT.md" in deliverable
    assert "<run-root>/deliverables/" in deliverable


def test_definition_of_done_requires_output_containment_in_run_root():
    body = text("references/definition-of-done.md").lower()
    assert "run-root" in body
    assert "output containment" in body
    assert "outside" in body and "not done" in body


def test_root_skill_states_run_root_is_the_output_proof_boundary():
    body = text("SKILL.md").lower()
    assert "run root" in body
    assert "output" in body and "proof boundary" in body


def test_v02_evidence_and_report_docs_match_hardened_runtime():
    evidence = text("references/evidence.md").lower()
    deliverable = text("references/deliverable.md").lower()
    html = text("references/html.md").lower()
    docx = text("references/docx.md").lower()
    markdown = text("references/lengthy-markdown.md").lower()
    readme = text("README.md").lower()
    skill = text("SKILL.md").lower()

    assert "schema v1" in evidence and "remains accepted" in evidence
    assert "schema v2" in evidence and "atom_id" in evidence
    assert "ambiguous" in evidence and "explicit byte span" in evidence
    assert "grouped by canonical chunk" in deliverable
    assert "inspect_chunks.py" in deliverable
    assert all(token in html for token in ("script", "style", "noscript", "template"))
    assert "non-skipped dom text" in html and "exactly once" in html
    assert "h1-h6" in html
    assert "heading1" in docx and "heading6" in docx
    assert "h1-h6" in markdown
    assert "receipt-owned" in readme and "install root" in readme
    assert "schema v2" in readme and "atom_id" in readme
    assert "human audit" in skill
