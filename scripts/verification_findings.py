"""Structured verification findings: stable codes owned by DoD predicates.

One deep implementation for finding identity and grouping. Display text is
carried but never parsed; predicates fail via their owning findings only.
"""
from __future__ import annotations

from dataclasses import dataclass

PREDICATES = (
    "source_identity_verified",
    "skill_preflight_complete",
    "plan_present",
    "plan_resolved",
    "output_containment_valid",
    "source_coverage_complete",
    "failure_protocol_respected",
    "source_fidelity_preserved",
    "format_qa_complete",
    "requested_deliverable_produced",
    "evidence_complete",
    "no_unresolved_required_failures",
    "fresh_final_verification",
    "machine_checks_passed",
)


@dataclass(frozen=True)
class Finding:
    code: str
    predicate: str
    message: str
    detail: str = ""


def codes_of(findings: list[Finding]) -> list[str]:
    return [f.code for f in findings]


def group_by_predicate(findings: list[Finding]) -> dict[str, list[Finding]]:
    grouped: dict[str, list[Finding]] = {}
    for finding in findings:
        grouped.setdefault(finding.predicate, []).append(finding)
    return grouped


def finding_by_code(findings: list[Finding], code: str) -> Finding:
    for finding in findings:
        if finding.code == code:
            return finding
    raise LookupError(f"no finding with code: {code}")


CATALOGUE: list[tuple[str, str]] = [
    ('atoms.atom_id.duplicate', 'source_coverage_complete'),
    ('atoms.atom_id.mismatch', 'source_coverage_complete'),
    ('atoms.atom_id.required', 'source_coverage_complete'),
    ('atoms.entry.type', 'source_coverage_complete'),
    ('atoms.list.type', 'source_coverage_complete'),
    ('atoms.span.invalid', 'source_coverage_complete'),
    ('atoms.span.mismatch', 'source_coverage_complete'),
    ('atoms.span.missing', 'source_coverage_complete'),
    ('chunking.required', 'source_coverage_complete'),
    ('chunking.type', 'source_coverage_complete'),
    ('containment.deliverable.paths', 'output_containment_valid'),
    ('containment.deliverable.report', 'output_containment_valid'),
    ('containment.evidence', 'output_containment_valid'),
    ('containment.evidence_ledger', 'output_containment_valid'),
    ('containment.ledger', 'output_containment_valid'),
    ('containment.manifest', 'output_containment_valid'),
    ('containment.plan', 'output_containment_valid'),
    ('containment.plan_status', 'output_containment_valid'),
    ('containment.traversal_report', 'output_containment_valid'),
    ('coverage.chunk.atomic_kind.missing', 'source_coverage_complete'),
    ('coverage.chunk.byte_end.mismatch', 'source_coverage_complete'),
    ('coverage.chunk.byte_start.not_contiguous', 'source_coverage_complete'),
    ('coverage.chunk.content.type', 'source_coverage_complete'),
    ('coverage.chunk.content_sha.mismatch', 'source_coverage_complete'),
    ('coverage.chunk.id.duplicate', 'source_coverage_complete'),
    ('coverage.chunk.id.missing', 'source_coverage_complete'),
    ('coverage.chunk.ordinal.mismatch', 'source_coverage_complete'),
    ('coverage.chunk.oversize', 'source_coverage_complete'),
    ('coverage.chunk.type', 'source_coverage_complete'),
    ('coverage.entry.chunk_id.missing', 'source_coverage_complete'),
    ('coverage.entry.duplicate', 'source_coverage_complete'),
    ('coverage.entry.hash.mismatch', 'source_coverage_complete'),
    ('coverage.entry.missing', 'source_coverage_complete'),
    ('coverage.entry.non_match.reason.missing', 'source_coverage_complete'),
    ('coverage.entry.ordinal.mismatch', 'source_coverage_complete'),
    ('coverage.entry.outcome.invalid', 'source_coverage_complete'),
    ('coverage.entry.type', 'source_coverage_complete'),
    ('coverage.entry.unknown_chunk', 'source_coverage_complete'),
    ('coverage.entry.verdict.missing', 'source_coverage_complete'),
    ('coverage.evidence_path.required', 'source_coverage_complete'),
    ('coverage.ledger.entries.type', 'source_coverage_complete'),
    ('coverage.ledger.manifest_sha.mismatch', 'source_coverage_complete'),
    ('coverage.ledger.schema_version', 'source_coverage_complete'),
    ('coverage.ledger.source_sha.mismatch', 'source_coverage_complete'),
    ('coverage.manifest.chunk_count', 'source_coverage_complete'),
    ('coverage.manifest.chunks.type', 'source_coverage_complete'),
    ('coverage.manifest.schema_version', 'source_coverage_complete'),
    ('coverage.manifest.text_bytes.mismatch', 'source_coverage_complete'),
    ('coverage.manifest.text_sha.mismatch', 'source_coverage_complete'),
    ('coverage.manifest_path.required', 'source_coverage_complete'),
    ('coverage.manifest_sha.mismatch', 'source_coverage_complete'),
    ('coverage.manifest_sha.missing', 'source_coverage_complete'),
    ('coverage.manifest_source.format.mismatch', 'source_coverage_complete'),
    ('coverage.manifest_source.sha.mismatch', 'source_coverage_complete'),
    ('coverage.manifest_source.type', 'source_coverage_complete'),
    ('coverage.manifest_source.uri.mismatch', 'source_coverage_complete'),
    ('coverage.mirror.completed.mismatch', 'source_coverage_complete'),
    ('coverage.mirror.required.mismatch', 'source_coverage_complete'),
    ('coverage.mirror.type', 'source_coverage_complete'),
    ('coverage.report.mismatch', 'source_coverage_complete'),
    ('coverage.report_path.missing', 'source_coverage_complete'),
    ('coverage.report_path.required', 'source_coverage_complete'),
    ('coverage.report_path.unreadable', 'source_coverage_complete'),
    ('coverage.source_local_path.missing', 'source_coverage_complete'),
    ('coverage.source_sha.mismatch', 'source_coverage_complete'),
    ('coverage.source_sha.missing', 'source_coverage_complete'),
    ('deliverable.path.missing', 'requested_deliverable_produced'),
    ('deliverable.provided.required', 'requested_deliverable_produced'),
    ('deliverable.requested.required', 'requested_deliverable_produced'),
    ('deliverable.traversal_report.required', 'requested_deliverable_produced'),
    ('done.failure.unresolved', 'no_unresolved_required_failures'),
    ('done.node.unresolved', 'plan_resolved'),
    ('done.verification.stale', 'fresh_final_verification'),
    ('done.verification_passed.missing', 'fresh_final_verification'),
    ('done.verification_started.missing', 'fresh_final_verification'),
    ('events.chunk_verified.duplicate', 'source_coverage_complete'),
    ('events.chunk_verified.mirror', 'source_coverage_complete'),
    ('events.chunk_verified.missing', 'source_coverage_complete'),
    ('events.chunk_verified.order', 'source_coverage_complete'),
    ('events.chunk_verified.unknown', 'source_coverage_complete'),
    ('events.entry.type', 'machine_checks_passed'),
    ('events.execution.order', 'plan_resolved'),
    ('events.execution_started.missing', 'plan_resolved'),
    ('events.legacy', 'machine_checks_passed'),
    ('events.plan_written.missing', 'plan_resolved'),
    ('events.type', 'machine_checks_passed'),
    ('evidence.chunk_ledger.invalid', 'evidence_complete'),
    ('evidence.chunk_ledger.missing', 'evidence_complete'),
    ('evidence.failure_ledger.invalid', 'evidence_complete'),
    ('evidence.failure_ledger.missing', 'evidence_complete'),
    ('evidence.format_qa.invalid', 'evidence_complete'),
    ('evidence.format_qa.missing', 'evidence_complete'),
    ('evidence.plan_status.invalid', 'evidence_complete'),
    ('evidence.plan_status.missing', 'evidence_complete'),
    ('evidence.skill_preflight.invalid', 'evidence_complete'),
    ('evidence.skill_preflight.missing', 'evidence_complete'),
    ('evidence.source_manifest.invalid', 'evidence_complete'),
    ('evidence.source_manifest.missing', 'evidence_complete'),
    ('evidence.traversal_report.invalid', 'evidence_complete'),
    ('evidence.traversal_report.missing', 'evidence_complete'),
    ('evidence.verification_log.invalid', 'evidence_complete'),
    ('evidence.verification_log.missing', 'evidence_complete'),
    ('extraction.backend.missing', 'format_qa_complete'),
    ('extraction.backend.unknown', 'format_qa_complete'),
    ('extraction.capabilities.mismatch', 'format_qa_complete'),
    ('extraction.format.mismatch', 'format_qa_complete'),
    ('extraction.manifest.mismatch', 'format_qa_complete'),
    ('extraction.qa.mismatch', 'format_qa_complete'),
    ('extraction.qa.type', 'format_qa_complete'),
    ('failure.protocol.alternative.order', 'failure_protocol_respected'),
    ('failure.protocol.alternative.prerequisites', 'failure_protocol_respected'),
    ('failure.protocol.architecture_stop.repair', 'failure_protocol_respected'),
    ('failure.protocol.diagnosis', 'failure_protocol_respected'),
    ('failure.protocol.plan_revised', 'failure_protocol_respected'),
    ('fidelity.preserved.required', 'source_fidelity_preserved'),
    ('fidelity.required', 'source_fidelity_preserved'),
    ('fidelity.substitutions.type', 'source_fidelity_preserved'),
    ('json.file.missing', 'machine_checks_passed'),
    ('json.file.type', 'machine_checks_passed'),
    ('json.file.unreadable', 'machine_checks_passed'),
    ('json.ledger.type', 'machine_checks_passed'),
    ('json.ledger.unreadable', 'machine_checks_passed'),
    ('ledger.validation.error', 'machine_checks_passed'),
    ('mapping.type', 'machine_checks_passed'),
    ('plan.nodes.required', 'plan_present'),
    ('plan.path.missing', 'plan_resolved'),
    ('plan.path.required', 'plan_present'),
    ('preflight.helper_help_read.false', 'skill_preflight_complete'),
    ('preflight.legacy', 'skill_preflight_complete'),
    ('preflight.required_references_read.false', 'skill_preflight_complete'),
    ('preflight.runtime_profile_resolved.false', 'skill_preflight_complete'),
    ('preflight.skill_read.false', 'skill_preflight_complete'),
    ('preflight.traversal_plan_ready.false', 'skill_preflight_complete'),
    ('qa.missing', 'format_qa_complete'),
    ('qa.required', 'format_qa_complete'),
    ('qa.type', 'format_qa_complete'),
    ('reproduction.backend.required', 'source_coverage_complete'),
    ('reproduction.failed', 'source_coverage_complete'),
    ('reproduction.format.unsupported', 'source_coverage_complete'),
    ('reproduction.max_bytes.invalid', 'source_coverage_complete'),
    ('reproduction.mismatch', 'source_coverage_complete'),
    ('reproduction.script.missing', 'source_coverage_complete'),
    ('reproduction.spawn.failed', 'source_coverage_complete'),
    ('reproduction.timeout', 'source_coverage_complete'),
    ('reproduction.unreadable', 'source_coverage_complete'),
    ('source.authority.invalid', 'source_identity_verified'),
    ('source.format.invalid', 'source_identity_verified'),
    ('source.identity.unverified', 'source_identity_verified'),
    ('source.uri.required', 'source_identity_verified'),
    ('traversal.report.mismatch', 'output_containment_valid'),
]