"""The worked first run in references/evidence.md must pass the real scripts.

Only the labelled fences of the doc are used; nothing comes from run_fixture.
"""

import json
import re
import shlex
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_DOC = ROOT / "references" / "evidence.md"
FENCE = re.compile(r"^```(\w+) (\S+)\n(.*?)\n```$", re.MULTILINE | re.DOTALL)
SOURCE_REL = "source/source.md"


def fences(doc: str) -> dict[str, str]:
    return {f"{kind} {label}": body for kind, label, body in FENCE.findall(doc)}


def run_command(line: str, fills: dict[str, str]) -> subprocess.CompletedProcess[str]:
    argv = []
    for token in shlex.split(line):
        for placeholder, value in fills.items():
            token = token.replace(placeholder, value)
        argv.append(sys.executable if token == "python" else token)
    # Bounded: a hung extractor or verifier fails the test instead of blocking the suite.
    return subprocess.run(
        argv, cwd=ROOT, capture_output=True, text=True, check=False, timeout=120
    )


def sha_of(blocks: dict[str, str], path: Path) -> str:
    result = run_command(blocks["sh sha256"], {"<file>": str(path)})
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


def drive_documented_run(doc: str, run_root: Path) -> subprocess.CompletedProcess[str]:
    blocks = fences(doc)
    run = json.loads(blocks["json run.json"])
    fills = {
        "<run-root>": run_root.as_posix(),
        "<source>": (run_root / SOURCE_REL).as_posix(),
        "<source-uri>": run["source"]["uri"],
    }
    source = run_root / SOURCE_REL
    source.parent.mkdir(parents=True)
    source.write_bytes((blocks["markdown source.md"] + "\n").encode("utf-8"))
    (run_root / "draft-evidence.json").write_text(
        blocks["json draft-evidence.json"] + "\n", encoding="utf-8"
    )
    commands = [ln for ln in blocks["sh first-run"].splitlines() if ln.strip()]
    for line in commands:
        done = run_command(line, fills)
        assert done.returncode == 0, line + "\n" + done.stdout + done.stderr

    manifest_path = run_root / "evidence" / "chunk-manifest.json"
    chunk = json.loads(manifest_path.read_text(encoding="utf-8"))["chunks"][0]
    text = blocks["json run.json"]
    for placeholder, value in {
        "<SOURCE_PATH>": SOURCE_REL,
        "<SOURCE_SHA256>": sha_of(blocks, source),
        "<MANIFEST_SHA256>": sha_of(blocks, manifest_path),
        "<CHUNK_ID>": chunk["id"],
        "<CHUNK_SHA256>": chunk["content_sha256"],
    }.items():
        text = text.replace(placeholder, value)
    (run_root / "run.json").write_text(text + "\n", encoding="utf-8")

    for rel in json.loads(text)["evidence"].values():
        target = run_root / rel
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("recorded by the agent\n", encoding="utf-8")
    return run_command(blocks["sh verify"], fills)


def with_run_json(doc: str, edit) -> str:
    original = fences(doc)["json run.json"]
    run = json.loads(original)
    edit(run)
    return doc.replace(original, json.dumps(run, indent=2))


def drop_preflight(run: dict) -> None:
    del run["preflight"]


def drop_qa(run: dict) -> None:
    del run["qa"]


def drop_evidence_entry(run: dict) -> None:
    del run["evidence"]["format_qa"]


def drop_chunk_verified(run: dict) -> None:
    run["events"] = [e for e in run["events"] if e["type"] != "chunk_verified"]


def test_documented_first_run_passes_the_real_verifier(tmp_path: Path) -> None:
    doc = EVIDENCE_DOC.read_text(encoding="utf-8")
    result = drive_documented_run(doc, tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr
    dod = json.loads((tmp_path / "dod.json").read_text(encoding="utf-8"))
    assert dod["passed"] is True


@pytest.mark.parametrize(
    "edit",
    [drop_preflight, drop_qa, drop_evidence_entry, drop_chunk_verified],
)
def test_incomplete_documented_run_fails_verification(tmp_path: Path, edit) -> None:
    doc = with_run_json(EVIDENCE_DOC.read_text(encoding="utf-8"), edit)
    result = drive_documented_run(doc, tmp_path)
    assert result.returncode != 0
