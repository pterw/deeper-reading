"""The release gate refuses a publish whose version labels disagree."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from release_check import main  # noqa: E402

CHANGELOG = "# Changelog\n\n## {heading}\n\n- A change users notice.\n\n## 0.1.0 - 2026-09-09\n\n- Old.\n"


def make_root(tmp_path, *, version="1.2.0", package="1.2.0", heading="1.2.0 - 2026-11-07"):
    (tmp_path / "VERSION").write_text(version + "\n", encoding="utf-8")
    (tmp_path / "package.json").write_text(json.dumps({"version": package}), encoding="utf-8")
    (tmp_path / "CHANGELOG.md").write_text(CHANGELOG.format(heading=heading), encoding="utf-8")
    return tmp_path


@pytest.mark.parametrize("labels, tag, expected", [
    ({}, None, 0),
    ({}, "v1.2.0", 0),
    ({"heading": "1.2.0 — prepared, not published"}, None, 0),
    ({"heading": "1.2.0 — prepared, not published"}, "v1.2.0", 1),
    ({"heading": "1.2.0"}, "v1.2.0", 1),
    ({"package": "1.1.0"}, None, 1),
    ({"heading": "1.1.9 - 2026-11-07"}, None, 1),
    ({}, "v1.2.1", 1),
])
def test_release_gate_verdict(tmp_path, capsys, labels, tag, expected):
    root = make_root(tmp_path, **labels)
    argv = ["--root", str(root)] + (["--tag", tag] if tag else [])
    assert main(argv) == expected
    assert ("FAIL:" in capsys.readouterr().out) == bool(expected)


def test_notes_are_the_version_section_only(tmp_path):
    root = make_root(tmp_path)
    notes = tmp_path / "notes.md"
    assert main(["--root", str(root), "--tag", "v1.2.0", "--notes", str(notes)]) == 0
    assert notes.read_text(encoding="utf-8") == "- A change users notice.\n"
