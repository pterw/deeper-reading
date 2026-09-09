# Installer Smoke Report

Date: 2026-09-08

## Scope

This report records the current hard-standalone installer behavior. It does not claim a live Copilot/Gemini/Codex/Claude discovery smoke in this harness; named runtime adapters remain contract-tested unless a host CLI is actually exercised.

## Current doctor smoke

Command:

```text
python installer/install.py doctor --target generic-agents --json
```

Observed:

```text
can_install: true
document_profile: standalone
document_status.state: ready
mutation_performed: false
runtime_detected: true
```

Standalone readiness evidence was the package's bundled extractors:

```text
scripts/extract_pdf.py
scripts/extract_docx.py
scripts/extract_html.py
scripts/extract_markdown.py
```

No external process prerequisite was required.

## Isolated project-scope install

A real temporary project root was used:

```text
/mnt/data/hard-standalone-smoke
```

Command shape:

```text
python installer/install.py install \
  --target generic-agents \
  --scope project \
  --project-dir /mnt/data/hard-standalone-smoke \
  --document-profile standalone \
  --json
```

Installed target:

```text
/mnt/data/hard-standalone-smoke/.agents/skills/chunking-document-workflows
```

The receipt included `SKILL.md`, README/VERSION, all references, all bundled scripts, and all six package-owned process skills.

## Fresh verify

Command shape:

```text
python installer/install.py verify \
  --target generic-agents \
  --scope project \
  --project-dir /mnt/data/hard-standalone-smoke \
  --json
```

Observed:

```text
passed: true
violations: []
```

All installation predicates were true:

```text
canonical_root
document_profile_resolved
host_discovery_verified_or_explicitly_not_available
no_backup_leftovers
no_staging_leftovers
payload_hashes_match
receipt_matches_installed_root
receipt_written
runtime_document_profile_consistent
```

For the generic Agent Skills target, host discovery was explicitly `not-available`, with evidence that there is no universal discovery CLI. That is a verified state, not a fabricated discovery success.

## Ownership-safe uninstall

Command shape:

```text
python installer/install.py uninstall \
  --target generic-agents \
  --scope project \
  --project-dir /mnt/data/hard-standalone-smoke \
  --json
```

Observed:

```text
state: uninstalled
preserved_root: false
```

The installer removed its receipt-owned runtime payload, including the portable extractors and package-owned skills.

A fresh filesystem check then confirmed:

```text
target absent
```

## Result

The current sovereign generic workflow completed:

```text
doctor: can_install true
-> install
-> verify PASS
-> uninstall
-> target absent
```

The final release still requires repeating package tests and extraction smokes from a clean extraction of the frozen distribution ZIP.
