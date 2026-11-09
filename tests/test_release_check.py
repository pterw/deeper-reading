"""The release gate refuses a publish whose version labels disagree."""
import json
import re
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


def make_root(tmp_path, *, version="1.2.0", package="1.2.0", heading="1.2.0 - 2026-11-07", changelog=None,
              manifest=None, version_dir=None):
    if changelog is None:
        changelog = CHANGELOG.format(heading=heading)
    version_home = tmp_path / version_dir if version_dir else tmp_path
    version_home.mkdir(parents=True, exist_ok=True)
    (version_home / "VERSION").write_text(version + "\n", encoding="utf-8")
    if manifest is not None:
        (tmp_path / "MANIFEST.json").write_text(json.dumps(manifest), encoding="utf-8")
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


def test_version_is_read_from_the_skill_root(tmp_path, capsys):
    root = make_root(tmp_path, manifest={"skill": {"root": "skills/x"}}, version_dir="skills/x")
    assert main(["--root", str(root)]) == 0
    assert "FAIL:" not in capsys.readouterr().out


def test_a_manifest_without_skill_root_reads_version_at_the_root(tmp_path):
    assert main(["--root", str(make_root(tmp_path, manifest={"payload": []}))]) == 0


@pytest.mark.parametrize(
    "bad", ["../x", 5, "/abs", "a/../../x", "", "a\\b", "C:x"],
    ids=["dotdot", "not-a-string", "absolute", "escapes", "empty", "backslash", "drive"],
)
def test_a_bad_skill_root_fails_instead_of_falling_back(tmp_path, capsys, bad):
    # VERSION sits at the root, so a silent fallback to "." would pass.
    root = make_root(tmp_path, manifest={"skill": {"root": bad}})
    assert main(["--root", str(root)]) == 1
    assert "FAIL:" in capsys.readouterr().out


def test_a_skill_root_that_leaves_the_root_through_a_link_fails(tmp_path, capsys):
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "VERSION").write_text("1.2.0\n", encoding="utf-8")
    (tmp_path / "pkg").mkdir()
    root = make_root(tmp_path / "pkg", manifest={"skill": {"root": "link"}})
    try:
        (root / "link").symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("directory symlinks unavailable")
    assert main(["--root", str(root)]) == 1
    assert "FAIL:" in capsys.readouterr().out


@pytest.mark.parametrize("raw", [b"{not json", b"", b"\xef\xbb\xbf{}", b"[]"],
                         ids=["invalid-json", "empty", "bom", "not-an-object"])
def test_an_unreadable_manifest_fails_with_a_line(tmp_path, capsys, raw):
    root = make_root(tmp_path)
    (root / "MANIFEST.json").write_bytes(raw)
    assert main(["--root", str(root)]) == 1
    assert "FAIL:" in capsys.readouterr().out


@pytest.mark.parametrize(
    "skill",
    ["skills/x", "", 0, False, []],
    ids=["string", "empty-string", "zero", "false", "list"],
)
def test_a_skill_entry_that_is_not_an_object_fails(tmp_path, capsys, skill):
    root = make_root(tmp_path, manifest={"skill": skill})
    assert main(["--root", str(root)]) == 1
    assert "FAIL:" in capsys.readouterr().out


def test_a_missing_version_at_the_skill_root_fails_with_a_line(tmp_path, capsys):
    root = make_root(tmp_path, manifest={"skill": {"root": "skills/x"}})
    (root / "skills" / "x").mkdir(parents=True)
    assert main(["--root", str(root)]) == 1
    assert "FAIL:" in capsys.readouterr().out


def test_release_workflow_version_reads_name_existing_files():
    repo = Path(__file__).resolve().parents[1]
    workflow = (repo / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
    paths = re.findall(r"\$\(cat ([\w./-]*VERSION)\)", workflow)
    assert paths
    assert [p for p in paths if not (repo / p).is_file()] == []
