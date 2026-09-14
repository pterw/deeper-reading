# Standalone Installer Usage

The canonical skill entrypoint remains `../SKILL.md`. The installer copies the manifest-owned runtime payload into a supported Agent Skills root; it does not wrap, rename, or relocate the canonical skill inside the distribution.

The normal runtime is sovereign and **standalone**: the package includes its own process skills plus bundled extractors for PDF, DOCX, HTML, and Markdown. No external process framework is required.

## Node CLI

Node.js 20 or newer can install, inspect, verify, and uninstall the skill without a Python installer runtime. Installing the npm package does not install the skill:

```text
npm install -g deeper-reading
```

Use an explicit command for every Agent Skills mutation:

```text
npx deeper-reading doctor --target auto --scope user --json
deeper-reading install --target auto --scope user --json
deeper-reading verify --target auto --scope user --json
deeper-reading uninstall --target auto --scope user --json
```

`doctor` is read-only. `install --dry-run` computes the transaction without writing it. `uninstall --force` permits removal of modified receipt-owned files; unowned files remain preserved. For project scope, pass `--scope project --project-dir PATH`; omitted `--project-dir` defaults to the current directory. `--document-profile` accepts `standalone` or `oai-native`. `--json` emits structured output. Blocked or failed operations exit with status 2.

The Node installer does not require Python. The installed extraction and verification scripts require Python 3.10 through 3.13, and `doctor` reports installer readiness separately from Python runtime readiness. No npm lifecycle hook writes into an Agent Skills directory. The Python commands below remain supported.

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

## Concurrent operations and interrupted installs

Python and Node share an atomic directory lock named
`.SKILL-NAME.install-lock` beside the physical target directory. Install,
upgrade, and uninstall refuse a locked target before reading its ownership
state. The owner retains the lock through replacement, discovery, receipt
writing, rollback, and final cleanup. Different targets can proceed independently.
Dry-run remains read-only and does not acquire a lock; its plan is a snapshot,
not a reservation. Older installer versions do not honor this protocol and
must not run concurrently with these versions against the same target.

Normal success and handled failure release the lock. Abrupt termination can
leave a lock plus stage/backup directories. Locks are never stolen based on age
or a process ID. If a lock persists, stop all installers for that target,
inspect the target, receipt and backup/stage siblings, and restore a consistent
installation before manually removing the empty lock directory and retrying.
Do not remove a live lock or discard a backup needed for recovery.

## Discovery output contracts

Copilot uses `copilot skill list --json` and requires an exact `name` with
boolean `enabled: true`, following the
[Copilot command reference](https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-command-reference#managing-skills-non-interactively).
Gemini uses `gemini skills list` and parses the named, enabled records emitted by
[Gemini's list command](https://github.com/google-gemini/gemini-cli/blob/main/packages/cli/src/commands/skills/list.ts),
including its description and location fields and optional ANSI styling.
These contracts were checked on 2026-09-14; the shared test fixtures model them
and are not captures from a user's installed CLI.

Names appearing only in descriptions, locations or diagnostics never prove
discovery. Disabled skills count as missing. Unsupported or malformed output
fails discovery and rolls back installation, as do subprocess failures.
Older Copilot versions without JSON listing need upgrading; there is no
substring-based compatibility fallback. Failures preserve command error
details instead of assuming output streams always exist.
