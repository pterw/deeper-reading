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


CATALOGUE: list[tuple[str, str]] = []