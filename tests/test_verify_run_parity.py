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
    assert result["predicates"]["source_coverage_complete"] is True
    assert result["predicates"]["failure_protocol_respected"] is True
    assert result["violations"] == []
