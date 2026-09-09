# Standalone Installer Usage

The canonical skill entrypoint remains `../SKILL.md`. The installer copies the manifest-owned runtime payload into a supported Agent Skills root; it does not wrap, rename, or relocate the canonical skill inside the distribution.

The normal runtime is sovereign and **standalone**: the package includes its own process skills plus bundled extractors for PDF, DOCX, HTML, and Markdown. No external process framework is required.

## Inspect first

```text
python installer/install.py doctor --target generic-agents --json
```

`doctor` is read-only. It reports the resolved target root, runtime detection, document-profile status, bundled extractor evidence, and whether installation can proceed.

## Install

```text
python installer/install.py install --target generic-agents --scope user --document-profile standalone --json
```

Use `--dry-run` to calculate the transaction without writing files. Use `--scope project --project-dir PATH` for project-local installation.

Targets: `auto`, `generic-agents`, `copilot`, `codex`, `gemini`, `claude`.

Document profiles:

- `standalone` — canonical/default. Basic text traversal is supplied by the bundled extractors:
  - `scripts/extract_pdf.py`
  - `scripts/extract_docx.py`
  - `scripts/extract_html.py`
  - `scripts/extract_markdown.py`
- `oai-native` — optional enhancement only when native OpenAI PDF/DOCX rendering, OCR, or richer layout tooling actually exists. It may add QA capability but cannot weaken or replace the standalone anti-skimming evidence contract.

The installed runtime payload also includes the package-owned planning, execution, debugging, recovery, and verification skills under `skills/`.

## Verify

```text
python installer/install.py verify --target generic-agents --scope user --json
```

Verification re-reads installed bytes and checks the canonical root, payload hashes, document-profile state, runtime/profile consistency, host-discovery state where available, receipt identity, and transaction leftovers.

## Uninstall

```text
python installer/install.py uninstall --target generic-agents --scope user --json
```

Uninstall removes only files owned by the installation receipt. Modified managed files cause refusal unless the explicit force path is used. Unowned user files are preserved.

## Windows and POSIX wrappers

```text
installer/install.ps1 doctor --target copilot
installer/install.sh doctor --target gemini
```

The wrappers contain no installer logic; they delegate to `install.py`.
