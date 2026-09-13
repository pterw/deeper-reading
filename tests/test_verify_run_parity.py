import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests.run_fixture import valid_run  # noqa: E402


def _result(tmp_path: Path) -> dict:
    from scripts.verify_run import validate_run, build_dod

    run = valid_run(tmp_path)
    run["_ledger_path"] = str(tmp_path / "run.json")
    return build_dod(run, validate_run(run))


def test_baseline_run_passes_and_predicates_hold(tmp_path):
    result = _result(tmp_path)
    if result["passed"] is not True:
        print("VIOLATIONS:", json.dumps(result["violations"], indent=2))
        print("PREDICATES:", json.dumps(
            {k: v for k, v in result["predicates"].items() if not v}, indent=2))
    assert result["passed"] is True
    assert result["predicates"]["source_coverage_complete"] is True
    assert result["predicates"]["failure_protocol_respected"] is True
    assert result["violations"] == []


def test_build_dod_no_longer_parses_prose():
    import inspect

    from scripts.verify_run import build_dod

    src = inspect.getsource(build_dod)
    assert "for e in errors" not in src
    assert "startswith(" not in src
    for token in (
        "chunk manifest", "manifest chunk", "chunk evidence",
        "missing evidence for emitted chunk", "duplicate evidence for chunk",
        "evidence references unknown chunk", "coverage.required",
        "coverage.completed", "source sha256", 'chunking"',
    ):
        assert token not in src, token


def test_findings_path_and_message_path_agree(tmp_path):
    from scripts.verify_run import _as_findings, build_dod, validate_findings

    run = valid_run(tmp_path)
    run["_ledger_path"] = str(tmp_path / "run.json")
    findings = validate_findings(run)
    by_findings = build_dod(run, findings)
    by_messages = build_dod(run, [f.message for f in findings])
    assert by_findings["passed"] == by_messages["passed"]
    assert by_findings["predicates"] == by_messages["predicates"]
    assert by_messages["codes"] == [f.code for f in findings]
    assert by_findings["violations"] == by_messages["violations"]
