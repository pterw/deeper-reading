from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PrerequisiteStatus:
    state: str
    evidence: tuple[str, ...] = ()
    action: tuple[str, ...] = ()


BUNDLED_EXTRACTORS = (
    "extract_pdf.py",
    "extract_docx.py",
    "extract_html.py",
    "extract_markdown.py",
)


def document_profile_status(
    profile: str,
    *,
    package_root: Path | str | None = None,
    native_pdf: Path | str | None = None,
    native_docx: Path | str | None = None,
) -> PrerequisiteStatus:
    profile = profile.lower()
    package = Path(package_root) if package_root is not None else Path(__file__).resolve().parents[1]

    if profile == "standalone":
        scripts = package / "scripts"
        required = [scripts / name for name in BUNDLED_EXTRACTORS]
        missing = [path for path in required if not path.is_file()]
        if missing:
            return PrerequisiteStatus(
                "missing",
                tuple(f"missing:{path}" for path in missing),
                ("Restore the bundled extraction payload before installation.",),
            )
        return PrerequisiteStatus(
            "ready",
            tuple(f"bundled={path}" for path in required),
        )

    if profile == "oai-native":
        pdf = Path(native_pdf) if native_pdf is not None else Path("/home/oai/skills/pdfs")
        docx = Path(native_docx) if native_docx is not None else Path("/home/oai/skills/docx")
        missing = [str(path) for path in (pdf, docx) if not (path / "SKILL.md").is_file()]
        if missing:
            return PrerequisiteStatus(
                "missing",
                tuple(f"missing:{item}" for item in missing),
                ("Use the standalone profile or run inside an OAI-native harness.",),
            )
        return PrerequisiteStatus(
            "ready",
            (
                f"pdf={pdf}",
                f"docx={docx}",
                "enhancement=oai-native-does-not-alter-anti-skimming-contract",
            ),
        )

    return PrerequisiteStatus("unsupported", (f"unknown document profile: {profile}",))
