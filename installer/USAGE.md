# Standalone Installer Usage

The canonical skill entrypoint is `../skills/deeper-reading/SKILL.md`. The installer copies the manifest-owned runtime payload into a supported Agent Skills root; it does not wrap, rename, or relocate the canonical skill inside the distribution.

The normal runtime is sovereign and **standalone**: the package includes its own process modules plus bundled extractors for PDF, DOCX, HTML, and Markdown. No external process framework is required.

## Node CLI

Node.js 20 or newer can install, inspect, verify, and uninstall the skill without a Python installer runtime. Installing the npm package does not install the skill:

```text
npm install -g deeper-reading
```

Use an explicit command for every Agent Skills mutation. After a global install the command is `deeper-reading`:

```text
deeper-reading doctor --target auto --scope user --json
deeper-reading install --target auto --scope user --json
deeper-reading verify --target auto --scope user --json
deeper-reading uninstall --target auto --scope user --json
```

Without a global install, run the same commands through `npx`:

```text
npx deeper-reading doctor --target auto --scope user --json
```

`install --dry-run` computes the transaction without writing it. `uninstall --force` permits removal of modified receipt-owned files; unowned files remain preserved. For project scope, pass `--scope project --project-dir PATH`; omitted `--project-dir` defaults to the current directory. `--document-profile` accepts `standalone` or `oai-native`. `--json` emits structured output.

### Exit codes

Both installers (Node and Python) behave the same way:

- `doctor` is read-only and exits 0 whenever it can report. It does not exit non-zero for an unready target: read readiness from `can_install` in the output (`false` when the document profile is not ready, for example `--document-profile oai-native` outside an OAI-native harness).
- `install`, `verify` and `uninstall` exit 2 when the operation is blocked or failed (including `passed: false` from `verify`) and 0 otherwise.

The Node installer does not require Python. The installed extraction and verification scripts require Python 3.10 through 3.13, and `doctor` reports installer readiness separately from Python runtime readiness. No npm lifecycle hook writes into an Agent Skills directory. The Python commands below remain supported.

## Inspect first

```text
python installer/install.py doctor --target generic-agents --json
```

`doctor` is read-only and exits 0 whenever it can report. It reports the resolved target root, runtime detection, document-profile status, and whether installation can proceed in `can_install`.

## Install

```text
python installer/install.py install --target generic-agents --scope user --document-profile standalone --json
```

Use `--dry-run` to calculate the transaction without writing files. Use `--scope project --project-dir PATH` for project-local installation.

Targets: `auto`, `generic-agents`, `copilot`, `codex`, `gemini`, `claude`. `auto` picks the first of `copilot`, `gemini`, `codex`, `claude` whose command is found on `PATH`, else `generic-agents`. Only absolute `PATH` entries are searched: the current directory and relative entries (such as `bin` or `node_modules/.bin`) are skipped, so a host reachable only through one of them needs `--target`.

Document profiles:

- `standalone` — canonical/default. Basic text traversal is supplied by the bundled extractors in the skill's `scripts/` folder (`skills/deeper-reading/scripts/` in a checkout, `scripts/` in the installed skill):
  - `scripts/extract_pdf.py`
  - `scripts/extract_docx.py`
  - `scripts/extract_html.py`
  - `scripts/extract_markdown.py`
- `oai-native` — optional enhancement only when native OpenAI PDF/DOCX rendering, OCR, or richer layout tooling actually exists. It may add QA capability but cannot weaken or replace the standalone anti-skimming evidence contract.

The installed runtime payload also includes the package-owned planning, execution, debugging, recovery, and verification modules as `modules/<name>.md` files in the skill root.

## Skill roots

The skill is installed at `<base>/skills/deeper-reading`, where `<base>` depends on the target and scope. User scope is under the home directory (`~` below; on Windows it is `%USERPROFILE%`); project scope is under `--project-dir`. Both installers use the same table.

| Target | User scope | Project scope |
| --- | --- | --- |
| `generic-agents` | `~/.agents/skills/deeper-reading` | `<project>/.agents/skills/deeper-reading` |
| `codex` | `~/.agents/skills/deeper-reading` | `<project>/.agents/skills/deeper-reading` |
| `copilot` | `~/.copilot/skills/deeper-reading` | `<project>/.github/skills/deeper-reading` |
| `gemini` | `~/.gemini/skills/deeper-reading` | `<project>/.gemini/skills/deeper-reading` |
| `claude` | `~/.claude/skills/deeper-reading` | `<project>/.claude/skills/deeper-reading` |

`generic-agents` and `codex` share one root. `auto` resolves to one of the targets above before the root is chosen.

### Ownership checks

`install` (including `--dry-run`), `verify` and `uninstall` check the resolved folder and its receipt, and refuse in both installers (exit 2, nothing changed) in these cases. `doctor` is not checked. With `--json`, the payload carries `state: "failed"` and the `code`; `verify` also carries `passed: false`.

| Code | When |
| --- | --- |
| `installer.owner.mismatch` | The receipt belongs to another target or scope than the request. |
| `installer.project.escape` | Project scope, and the resolved folder is outside the resolved project, for example a `.claude` that is a link out of the project. `install` checks this even with no receipt, before writing anything. It is also given when a link on the way to the folder leads nowhere (the folder it points to does not exist); create that folder, or remove the link. At user scope the same refusal exits 2 with that advice and no code. Use `--scope user` or a real folder in the project; if `.claude` or `.claude/skills` is a link out, remove that link itself and not its contents. To remove an existing install there, delete it by hand first. |
| `installer.receipt.owner_invalid` | The receipt's `target` is missing or unknown, or its `scope` is not `user` or `project`. Delete the skill folder `deeper-reading`; if it is a link, remove the link itself and not its contents; never delete only the shared `.agents` folder; then run `install`. |
| `installer.receipt.missing` | `install` or `uninstall` found the folder without a receipt, for example after `npx skills add`. The message gives the recovery; see the README. `verify` fails there without this code. |

For `install` and `uninstall` (not `verify` or `--dry-run`), the check repeats inside the target lock, so if another target takes the folder after the first check, the operation is refused with the same code. A linked skills folder is the usual cause of `installer.owner.mismatch`. If `~/.claude/skills` is a link to `~/.agents/skills`, both targets resolve to one folder, so the target that did not install it is refused. The message names the owning target and the working command: `--target <owner>`, plus `--scope <owner scope>` when the scope differs. `generic-agents` and `codex` share a root by design and are not refused for it. `--project-dir` is ignored for user scope.

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
