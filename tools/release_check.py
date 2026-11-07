#!/usr/bin/env python3
"""Check that the release labels agree before anything is published.

Without --tag (every pull request): VERSION and package.json name the same
version, and CHANGELOG.md has a section for it. With --tag (the release gate,
before an npm publish that cannot be undone): the tag is v<version> and that
CHANGELOG section is dated. --notes writes the section body for the GitHub
Release. Exit 0 when every check passes; exit 1 with FAIL lines otherwise.

Development tool only: it lives outside scripts/ and installer/, so it is
never part of the skill payload, the npm package or the release ZIP.
"""
from __future__ import annotations

import argparse
import datetime
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# "## 0.2.3 - 2026-11-07"; the separator may be a hyphen, en dash or em dash.
HEADING = re.compile(r"^## +(\S+)(?: +[-–—] +(.*?))? *$")


def is_date(text: str) -> bool:
    """True when text is a real calendar date written YYYY-MM-DD.

    The shape check keeps the verdict identical on every Python: from 3.11
    fromisoformat also accepts 20261107 and 2026-W45-6.
    """
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        return False
    try:
        datetime.date.fromisoformat(text)
    except ValueError:
        return False
    return True


def changelog_section(text: str, version: str) -> tuple[str, str] | None:
    """Return (heading suffix, body) of the version's section, or None."""
    lines = text.splitlines()
    for index, line in enumerate(lines):
        match = HEADING.match(line)
        if match and match.group(1) == version:
            body = []
            for following in lines[index + 1:]:
                if following.startswith("## "):
                    break
                body.append(following)
            return match.group(2) or "", "\n".join(body).strip() + "\n"
    return None


def check(root: Path, tag: str | None) -> tuple[list[str], str | None]:
    """Return the failures and, when the section exists, its body."""
    failures = []
    version = (root / "VERSION").read_text(encoding="utf-8").strip()
    package = json.loads((root / "package.json").read_text(encoding="utf-8"))["version"]
    if package != version:
        failures.append(f"package.json version {package} differs from VERSION {version}")
    if tag is not None and tag != f"v{version}":
        failures.append(f"tag {tag} does not match VERSION v{version}")
    section = changelog_section((root / "CHANGELOG.md").read_text(encoding="utf-8"), version)
    if section is None:
        failures.append(f"CHANGELOG.md has no '## {version}' section")
        return failures, None
    suffix, body = section
    if tag is not None and not is_date(suffix):
        failures.append(f"CHANGELOG.md section {version} is not dated: '## {version} - YYYY-MM-DD'")
    if tag is not None and not body.strip():
        failures.append(f"CHANGELOG.md section {version} has no entries")
    return failures, body


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--tag", help="release tag; requires a dated CHANGELOG section")
    parser.add_argument("--notes", type=Path, help="write the CHANGELOG section body here")
    parser.add_argument("--root", type=Path, default=ROOT, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    failures, body = check(args.root, args.tag)
    for failure in failures:
        print(f"FAIL: {failure}")
    if failures:
        return 1
    if args.notes is not None:
        args.notes.write_text(body, encoding="utf-8")
    print("PASS: release labels agree")
    return 0


if __name__ == "__main__":
    sys.exit(main())
