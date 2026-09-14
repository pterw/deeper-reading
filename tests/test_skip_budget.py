import xml.etree.ElementTree as ET
from tests.check_skip_budget import violations


def test_missing_pdf_validation_is_not_a_permitted_ci_skip():
    report = ET.fromstring('<testsuite><testcase><skipped message="optional pypdf unavailable; encrypted PDF fixture untested"/></testcase></testsuite>')
    assert violations(report, symlink_budget=9)


def test_named_environment_gaps_are_bounded():
    report = ET.fromstring('<testsuite><testcase><skipped message="directory symlinks unavailable"/></testcase></testsuite>')
    assert violations(report, symlink_budget=0)
    assert not violations(report, symlink_budget=1)
