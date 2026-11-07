"""The release gate refuses a publish whose version labels disagree."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from release_check import main  # noqa: E402

CHANGELOG = "# Changelog\n\n## {heading}\n\n- A change users notice.\n\n## 0.1.0 - 2026-09-09\n\n- Old.\n"
RC_FIRST = "## 1.2.0-rc.1 - prepared\n\n- Candidate.\n\n## 1.2.0 - 2026-11-07\n\n- Real.\n"
RC_ONLY = "## 1.2.0-rc.1 - 2026-10-01\n\n- Candidate.\n"
EMPTY_SECTION = "## 1.2.0 - 2026-11-07\n\n## 0.1.0 - 2026-09-09\n\n- Old.\n"
SUBHEADING = "## 1.2.0 - 2026-11-07\n\n### Fixed\n\n- A fix.\n\n## 0.1.0 - 2026-09-09\n\n- Old.\n"
LAST_BLOCK = "## 0.1.0 - 2026-09-09\n\n- Old.\n\n## 1.2.0 - 2026-11-07\n\n- First.\n- Last."


def make_root(tmp_path, *, version="1.2.0", package="1.2.0", heading="1.2.0 - 2026-11-07", changelog=None):
    if changelog is None:
        changelog = CHANGELOG.format(heading=heading)
    (tmp_path / "VERSION").write_text(version + "\n", encoding="utf-8")
    (tmp_path / "package.json").write_text(json.dumps({"version": package}), encoding="utf-8")
    (tmp_path / "CHANGELOG.md").write_bytes(changelog.encode("utf-8"))
    return tmp_path


@pytest.mark.parametrize("labels, tag, expected", [
    ({}, None, 0),
    ({}, "v1.2.0", 0),
    ({"heading": "1.2.0 — prepared, not published"}, None, 0),
    ({"heading": "1.2.0 — prepared, not published"}, "v1.2.0", 1),
    ({"heading": "1.2.0"}, "v1.2.0", 1),
    ({"heading": "1.2.0 - 9999-99-99"}, "v1.2.0", 1),
    ({"heading": "1.2.0 - 2026-11-07 (draft)"}, "v1.2.0", 1),
    ({"package": "1.1.0"}, None, 1),
    ({"heading": "1.1.9 - 2026-11-07"}, None, 1),
    ({}, "v1.2.1", 1),
    ({}, "v11.2.0", 1),
    ({"changelog": RC_FIRST}, "v1.2.0", 0),
    ({"changelog": RC_ONLY}, None, 1),
    ({"changelog": EMPTY_SECTION}, "v1.2.0", 1),
    ({"heading": "1.2.0 - 20261107"}, "v1.2.0", 1),
    ({"heading": "1.2.0 - 2026-W45-6"}, "v1.2.0", 1),
    ({"changelog": EMPTY_SECTION}, None, 0),
    ({}, "1.2.0", 1),
    ({}, "v1.2.0.1", 1),
], ids=[
    "aligned", "aligned-tagged", "undated-untagged", "undated-tagged", "no-suffix-tagged",
    "impossible-date", "date-with-trailing-text", "package-differs", "no-section",
    "tag-differs", "tag-suffix-match", "rc-section-first", "rc-only-changelog", "empty-body-tagged",
    "compact-date", "iso-week-date", "empty-body-untagged", "tag-without-v", "tag-extends-version",
])
def test_release_gate_verdict(tmp_path, capsys, labels, tag, expected):
    root = make_root(tmp_path, **labels)
    argv = ["--root", str(root)] + (["--tag", tag] if tag else [])
    assert main(argv) == expected
    assert ("FAIL:" in capsys.readouterr().out) == bool(expected)


@pytest.mark.parametrize("changelog, expected", [
    (None, "- A change users notice.\n"),
    (SUBHEADING, "### Fixed\n\n- A fix.\n"),
    (LAST_BLOCK, "- First.\n- Last.\n"),
    (CHANGELOG.format(heading="1.2.0 - 2026-11-07").replace("\n", "\r\n"), "- A change users notice.\n"),
], ids=["version-section-only", "subheading-kept", "last-block", "crlf"])
def test_notes_are_the_version_section_only(tmp_path, changelog, expected):
    root = make_root(tmp_path, changelog=changelog)
    notes = tmp_path / "notes.md"
    assert main(["--root", str(root), "--tag", "v1.2.0", "--notes", str(notes)]) == 0
    assert notes.read_text(encoding="utf-8") == expected
