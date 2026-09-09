# Standalone Multi-Runtime Installer Remediation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the currently verified `chunking-document-workflows` Agent Skill into a standalone, cross-runtime distribution that installs the same canonical root skill into supported agents, resolves Superpowers and document dependencies honestly, verifies installation, and never weakens the existing document workflow.

**Architecture:** Keep `SKILL.md` at `<package-root>/SKILL.md` as the canonical Agent Skill entrypoint. Add a stdlib-only installer subsystem beneath `installer/`, a manifest that distinguishes source/distribution files from the installed runtime payload, runtime adapters for supported hosts, and explicit runtime/document capability profiles. The installer installs this skill; Superpowers remains a separately sourced prerequisite, and OAI-native document skills remain live dependencies only where actually available.

**Tech Stack:** Python 3 standard library, JSON, pathlib, shutil, subprocess with argument arrays, pytest for development tests, Agent Skills open standard.

**Spec:** `CURRENT_PACKAGE_AUDIT.md` plus the design/constraints embedded in this plan.

## Global Constraints

- `<package-root>/SKILL.md` is canonical and must never move beneath `skill/`, `src/`, `payload/`, or an installer wrapper.
- The installed target must end with `<skills-root>/chunking-document-workflows/SKILL.md`.
- Preserve the existing 36-test document-workflow baseline.
- Do not vendor or copy Superpowers into this skill.
- Do not represent a portable public OpenAI PDF/DOC skill as identical to the internal `/home/oai/skills` trees.
- Never silently downgrade source fidelity or document capability.
- Installer implementation is Python-standard-library only.
- Never invoke subprocesses with `shell=True`.
- Never require administrator/root privileges.
- Installation must be transactional: stage -> validate -> atomic replace -> verify -> receipt; rollback on failure.
- Every runtime-specific command/path must be verified from the target's current CLI/help or official adapter contract rather than guessed.
- `--dry-run` must perform zero filesystem mutations.
- Existing user files not owned by the manifest must never be deleted during upgrade/uninstall.
- Installation success is a machine-verifiable terminal state, not a narrative claim.

---

# Target Package Tree

```text
chunking-document-workflows/
├── SKILL.md                         # canonical Agent Skill entrypoint
├── VERSION                          # distribution version
├── MANIFEST.json                    # payload, hashes, profiles, supported targets
├── references/
│   ├── anti-patterns.md
│   ├── control-flow.md
│   ├── definition-of-done.md
│   ├── deliverable.md
│   ├── dependencies.md
│   ├── docx.md
│   ├── evidence.md
│   ├── failure-recovery.md
│   ├── html.md
│   ├── pdf.md
│   ├── prerequisites.md
│   ├── runtime-profiles.md          # NEW
│   └── source-acquisition.md
├── scripts/
│   └── verify_run.py
├── installer/
│   ├── install.py                   # canonical standalone entrypoint
│   ├── install.ps1                  # thin Windows wrapper
│   ├── install.sh                   # thin POSIX wrapper
│   ├── USAGE.md
│   ├── core.py                      # staging, copy, hash, rollback, receipts
│   ├── manifest.py                  # manifest parser/validator
│   ├── prerequisites.py             # Superpowers/document dependency resolution
│   └── adapters/
│       ├── __init__.py
│       ├── base.py
│       ├── generic_agents.py
│       ├── copilot.py
│       ├── codex.py
│       ├── gemini.py
│       └── claude.py
├── tests/
│   ├── test_contradictions.py
│   ├── test_mutations.py
│   ├── test_verify_run.py
│   ├── test_workflow_contract.py
│   └── installer/
│       ├── test_manifest.py
│       ├── test_paths.py
│       ├── test_install_transaction.py
│       ├── test_prerequisites.py
│       ├── test_runtime_adapters.py
│       ├── test_install_mutations.py
│       └── test_distribution_contract.py
└── docs/
    └── superpowers/
        └── plans/
            └── ...
```

## Installed Runtime Payload

`MANIFEST.json` must define an explicit whitelist. The default installed skill contains only:

```text
chunking-document-workflows/
├── SKILL.md
├── VERSION
├── references/
│   └── ...
└── scripts/
    └── verify_run.py
```

The following stay in the standalone distribution but are not copied into the runtime skill:

```text
installer/
tests/
docs/
MANIFEST.json   # installer metadata; may remain distribution-only
```

If later runtime verification requires manifest metadata, generate a minimal hidden `.install-receipt.json` in the installed root instead of copying development metadata wholesale.

---

### Task 1: Freeze the Existing Skill as a Regression Contract

**Files:**
- Modify: `tests/installer/test_distribution_contract.py`
- Read only: existing `SKILL.md`, `references/`, `scripts/verify_run.py`, current tests

**Interfaces:**
- Consumes: current frozen package.
- Produces: tests that prove installer work cannot relocate or semantically replace the existing skill.

- [ ] **Step 1: Write failing root-contract tests**

```python
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def test_canonical_skill_is_at_package_root():
    assert (ROOT / "SKILL.md").is_file()
    assert not (ROOT / "skill" / "SKILL.md").exists()
    assert not (ROOT / "payload" / "SKILL.md").exists()

def test_existing_workflow_verifier_remains_runtime_payload():
    assert (ROOT / "scripts" / "verify_run.py").is_file()
```

- [ ] **Step 2: Run the new test and existing 36-test baseline**

Run:

```text
python -m pytest -q
```

Expected before installer scaffolding: new installer test path may fail because it does not exist; existing 36 tests remain green.

- [ ] **Step 3: Record baseline in `CURRENT_PACKAGE_AUDIT.md`**

Record exact current result: `36 passed`.

- [ ] **Step 4: Commit only test/audit baseline changes if working in Git**

---

### Task 2: Define Distribution Manifest and Version Contract

**Files:**
- Create: `VERSION`
- Create: `MANIFEST.json`
- Create: `installer/manifest.py`
- Create: `tests/installer/test_manifest.py`

**Interfaces:**
- Produces:
  - `load_manifest(path) -> Manifest`
  - `validate_manifest(manifest, package_root) -> list[str]`
  - explicit runtime payload whitelist
  - prerequisite/runtime profile declarations

- [ ] **Step 1: Write failing manifest tests**

Test that:

```python
manifest["skill"]["name"] == "chunking-document-workflows"
manifest["skill"]["entrypoint"] == "SKILL.md"
"SKILL.md" in manifest["payload"]
"references" in manifest["payload"]
"scripts/verify_run.py" in manifest["payload"]
"tests" not in manifest["payload"]
"installer" not in manifest["payload"]
```

Also require semantic fields:

```python
manifest["prerequisites"]["superpowers"]["vendored"] is False
set(manifest["document_profiles"]) == {"oai-native", "portable-openai"}
```

- [ ] **Step 2: Verify RED**

Expected: FAIL because `VERSION`, `MANIFEST.json`, and parser do not exist.

- [ ] **Step 3: Implement minimal manifest parser with dataclasses**

Use only `json`, `dataclasses`, `pathlib`.

Reject:
- missing canonical `SKILL.md`;
- `..` path traversal;
- absolute payload paths;
- duplicated payload entries;
- files outside package root;
- manifest skill name not matching `SKILL.md` frontmatter name.

- [ ] **Step 4: Create initial manifest**

Required logical shape:

```json
{
  "schema_version": 1,
  "skill": {
    "name": "chunking-document-workflows",
    "entrypoint": "SKILL.md"
  },
  "payload": [
    "SKILL.md",
    "VERSION",
    "references",
    "scripts/verify_run.py"
  ],
  "prerequisites": {
    "superpowers": {
      "vendored": false,
      "required": true
    }
  },
  "document_profiles": {
    "oai-native": {},
    "portable-openai": {}
  },
  "targets": [
    "generic-agents",
    "copilot",
    "codex",
    "gemini",
    "claude"
  ]
}
```

- [ ] **Step 5: Run manifest tests to GREEN**

- [ ] **Step 6: Re-run all prior tests**

---

### Task 3: Introduce Runtime Profiles Without Rewriting Workflow Semantics

**Files:**
- Create: `references/runtime-profiles.md`
- Modify: `SKILL.md`
- Modify: `references/prerequisites.md`
- Modify: `references/dependencies.md`
- Modify: `references/pdf.md`
- Modify: `references/docx.md`
- Modify: `tests/test_contradictions.py`
- Create: `tests/installer/test_runtime_adapters.py`

**Interfaces:**
- Produces `runtime_profile` and `document_profile` semantics.
- Preserves current ChatGPT/OAI behavior as `oai-native`.

- [ ] **Step 1: Write RED contradiction tests**

Require:

```python
assert "oai-native" in runtime_profiles
assert "portable-openai" in runtime_profiles
assert "@Superpowers:superpowers" not in universal_portable_rules
assert "/home/oai/skills" not in universal_portable_rules
```

But also require native profile preservation:

```python
assert "@Superpowers:superpowers" in native_profile
assert "/home/oai/skills/pdfs" in native_profile
assert "/home/oai/skills/docx" in native_profile
```

- [ ] **Step 2: Verify RED**

- [ ] **Step 3: Refactor compatibility language**

Root `SKILL.md` should describe capabilities rather than claim every runtime has ChatGPT-only paths.

The quick path remains semantically identical:

```text
discover current Superpowers capabilities
-> classify source/task
-> resolve document profile
-> plan
-> execute bounded nodes
-> debug before traversal
-> brainstorm only at exhausted/architectural gate
-> fresh verification
-> DoD
```

- [ ] **Step 4: Define `oai-native`**

Exact native behavior remains:

- ChatGPT plugin discovery uses `@Superpowers:superpowers`.
- PDF uses live `/home/oai/skills/pdfs`.
- DOCX uses live `/home/oai/skills/docx`.
- existing full-tree read rule remains.

- [ ] **Step 5: Define `portable-openai`**

Portable behavior:

- Superpowers is discovered through the host's installed plugin/extension skill set.
- Public OpenAI PDF/document Agent Skills are resolved separately by source/version.
- the run ledger records which portable dependency was used.
- capabilities not present in the portable dependency cause a pre-execution hard stop.
- no text claims portable dependencies are identical to internal OAI skills.

- [ ] **Step 6: GREEN existing contradiction tests plus new profile tests**

- [ ] **Step 7: Re-run full suite**

---

### Task 4: Build Target Adapter Interface

**Files:**
- Create: `installer/adapters/base.py`
- Create: `installer/adapters/generic_agents.py`
- Create: `installer/adapters/copilot.py`
- Create: `installer/adapters/codex.py`
- Create: `installer/adapters/gemini.py`
- Create: `installer/adapters/claude.py`
- Create: `tests/installer/test_paths.py`
- Expand: `tests/installer/test_runtime_adapters.py`

**Interfaces:**

```python
class RuntimeAdapter(Protocol):
    name: str
    def detect(self) -> bool: ...
    def resolve_skill_root(self, scope: str, project_dir: Path | None) -> Path: ...
    def superpowers_status(self) -> PrerequisiteStatus: ...
    def document_profile_status(self) -> PrerequisiteStatus: ...
    def discovery_verify(self, skill_name: str) -> VerificationResult: ...
```

- [ ] **Step 1: Write path tests before adapters**

Required canonical targets include:

```text
generic personal: ~/.agents/skills/chunking-document-workflows/
generic project:  <project>/.agents/skills/chunking-document-workflows/

Copilot personal: adapter chooses a documented Copilot-compatible personal root
Copilot project:  adapter chooses a documented project root

Gemini personal: adapter chooses ~/.gemini/skills or ~/.agents/skills
Gemini project:  adapter chooses .gemini/skills or .agents/skills

Claude personal: ~/.claude/skills/chunking-document-workflows/

Codex personal: current documented Agent Skills root, verified at implementation time
```

Every final target must satisfy:

```python
target.name == "chunking-document-workflows"
(target / "SKILL.md").is_file()
```

- [ ] **Step 2: Verify RED**

- [ ] **Step 3: Implement `generic_agents` first**

This is the lowest-common-denominator direct-copy adapter.

- [ ] **Step 4: Implement Copilot adapter**

Prefer official host skill management where available.

Current public contract to preserve during implementation:

- personal skills can live under Copilot/Agent Skills roots;
- project skills can live under supported project skill roots;
- Copilot CLI exposes skill list/add/remove management.

Run current `copilot ... --help` before finalizing command syntax.

- [ ] **Step 5: Implement Gemini adapter**

Use current `gemini skills` capabilities when available; direct path resolution remains a verified fallback.

Run `gemini skills --help` before finalizing syntax.

- [ ] **Step 6: Implement Codex and Claude adapters**

Do not infer undocumented plugin commands.

For direct skill installation, use the current documented skill root.

If Superpowers installation is only exposed interactively on that host, adapter returns `needs-user-action` rather than pretending automation succeeded.

- [ ] **Step 7: GREEN adapter/path tests**

---

### Task 5: Implement Superpowers Prerequisite Provider

**Files:**
- Create: `installer/prerequisites.py`
- Create: `tests/installer/test_prerequisites.py`

**Interfaces:**

```python
@dataclass
class PrerequisiteStatus:
    state: Literal["ready", "missing", "needs-user-action", "unsupported"]
    evidence: list[str]
    action: list[str]
```

- [ ] **Step 1: Write RED tests for each state**

Test:
- already installed;
- missing but automatable;
- missing and interactive/manual;
- installation command fails;
- user declines installation;
- version/discovery check fails after install.

- [ ] **Step 2: Implement Superpowers provider**

Rules:

- never vendor Superpowers;
- use each runtime's official mechanism;
- Copilot may use its plugin marketplace commands;
- Gemini may use its extension installation mechanism;
- Codex/Claude adapters may require an interactive/manual action if no supported noninteractive installer exists;
- after any installation attempt, verify discovery before marking `ready`.

- [ ] **Step 3: Ensure command execution uses argument arrays**

Forbidden:

```python
subprocess.run(command, shell=True)
```

Required pattern:

```python
subprocess.run(args, check=False, capture_output=True, text=True)
```

- [ ] **Step 4: GREEN prerequisite tests**

---

### Task 6: Resolve Portable OpenAI Document Dependencies

**Files:**
- Modify: `installer/prerequisites.py`
- Modify: `MANIFEST.json`
- Create/modify: `references/runtime-profiles.md`
- Create: `tests/installer/test_document_profiles.py`

**Interfaces:**
- Produces a resolved document profile with source identity and version.

- [ ] **Step 1: Write RED tests**

Cases:

1. native OAI skills exist -> choose `oai-native`;
2. external runtime with supported public OpenAI PDF/doc skills -> choose `portable-openai`;
3. external runtime without required dependency -> stop before document execution;
4. requested operation requires unsupported native-only capability -> stop;
5. dependency source/hash/version mismatch -> stop.

- [ ] **Step 2: Define dependency source metadata in manifest**

Do not use floating, unverifiable downloaded content for a completed installation.

Manifest/provider must record:

```text
provider
repository/source
skill name
resolved revision/version
content hash
capability profile
```

- [ ] **Step 3: Implement resolver**

The resolver may network-fetch prerequisites, but must:

- use HTTPS;
- verify the expected source;
- stage before installation;
- calculate hashes;
- record resolved revision;
- never modify the Python/Node runtime merely because an optional document helper is missing.

- [ ] **Step 4: GREEN dependency-profile tests**

---

### Task 7: Implement Transactional Installer Core

**Files:**
- Create: `installer/core.py`
- Create: `installer/install.py`
- Create: `tests/installer/test_install_transaction.py`

**Interfaces:**

Canonical CLI:

```text
python installer/install.py install
python installer/install.py verify
python installer/install.py doctor
python installer/install.py uninstall
```

Options:

```text
--target auto|generic-agents|copilot|codex|gemini|claude
--scope user|project
--project-dir PATH
--document-profile auto|oai-native|portable-openai
--superpowers check|install|skip
--dry-run
--json
```

`skip` must not allow final DoD if Superpowers is required and unavailable; it only skips installation attempt and returns unresolved prerequisite status.

- [ ] **Step 1: Write RED transactional tests**

Test:
- fresh install;
- upgrade over managed install;
- failure during staging;
- failure after backup;
- failure during target replace;
- verification failure after replace;
- rollback restores prior version;
- dry-run changes nothing;
- existing unrelated files are preserved;
- target `SKILL.md` is never nested one level too deep.

- [ ] **Step 2: Implement staging**

Use a temporary sibling directory on the same filesystem as the target.

- [ ] **Step 3: Validate staged payload**

Before replace:

- canonical `SKILL.md`;
- manifest payload completeness;
- frontmatter name;
- referenced runtime files;
- file hashes.

- [ ] **Step 4: Atomic replace**

Sequence:

```text
preflight
-> stage
-> validate stage
-> backup prior managed install if present
-> replace
-> verify installed files
-> host discovery verification when available
-> write receipt
-> remove backup
```

Any failed post-replace step:

```text
restore backup
-> report exact failed predicate
-> exit nonzero
```

- [ ] **Step 5: GREEN transactional tests**

---

### Task 8: Add Install Receipt and Installation Definition of Done

**Files:**
- Modify: `installer/core.py`
- Create: `tests/installer/test_install_dod.py`
- Create: `installer/USAGE.md`

**Interfaces:**

Installed receipt:

```text
<installed-skill-root>/.install-receipt.json
```

Required fields:

```json
{
  "skill": "chunking-document-workflows",
  "version": "...",
  "target": "...",
  "scope": "...",
  "installed_root": "...",
  "runtime_profile": "...",
  "document_profile": "...",
  "superpowers": {
    "state": "ready",
    "evidence": []
  },
  "payload_hashes": {},
  "installed_at": "..."
}
```

- [ ] **Step 1: Write RED DoD tests**

Installation PASS requires every predicate:

```text
canonical_root
manifest_complete
payload_hashes_match
superpowers_ready
document_profile_resolved
host_discovery_verified_or_explicitly_not_available
no_staging_leftovers
no_backup_leftovers
receipt_written
```

- [ ] **Step 2: Implement `verify` command**

`verify` reads the installed bytes fresh and returns nonzero on any required predicate failure.

- [ ] **Step 3: Implement `doctor` command**

`doctor` must be read-only and report:
- detected runtimes;
- candidate roots;
- prerequisite states;
- document profiles;
- conflicts/duplicate skill names;
- whether install is possible.

- [ ] **Step 4: GREEN installation DoD tests**

---

### Task 9: Implement Safe Uninstall and Upgrade Ownership

**Files:**
- Modify: `installer/install.py`
- Modify: `installer/core.py`
- Create: `tests/installer/test_uninstall.py`

**Interfaces:**

Uninstall removes only files owned by the receipt/manifest.

- [ ] **Step 1: Write RED ownership tests**

Create an installed skill with:
- manifest-owned files;
- a user-created note;
- a modified owned file.

Expected:
- default uninstall refuses destructive removal of modified owned files unless explicitly confirmed/forced;
- user-created file is never silently deleted;
- Superpowers and public OpenAI dependency skills are not removed automatically just because this skill is removed.

- [ ] **Step 2: Implement uninstall**

- [ ] **Step 3: GREEN uninstall tests**

---

### Task 10: Add Cross-Platform Thin Wrappers

**Files:**
- Create: `installer/install.sh`
- Create: `installer/install.ps1`
- Create: `tests/installer/test_wrappers.py`

**Interfaces:**
- wrappers only locate Python and delegate to `installer/install.py`;
- no installer logic duplicated in shell/PowerShell.

- [ ] **Step 1: Write static wrapper tests**

Require no network/install logic in wrappers.

- [ ] **Step 2: Implement wrappers**

POSIX wrapper:

```sh
exec "${PYTHON:-python3}" "$(dirname "$0")/install.py" "$@"
```

PowerShell wrapper delegates to `py -3` or `python` without reconstructing arguments unsafely.

- [ ] **Step 3: GREEN wrapper tests**

---

### Task 11: Mutation-Test Illegal Installer Workflows

**Files:**
- Create: `tests/installer/test_install_mutations.py`

**Interfaces:**
- starts from one valid installation transaction;
- mutates one transition/predicate at a time.

- [ ] **Step 1: Require an unmutated baseline PASS**

- [ ] **Step 2: Add mutations**

At minimum:

```text
M1  relocate SKILL.md beneath payload/
M2  skip manifest validation
M3  copy only part of references/
M4  mark Superpowers ready without discovery evidence
M5  use /home/oai/skills on external runtime without native profile
M6  label portable PDF skill as oai-native
M7  skip payload hash verification
M8  claim host discovery success after command failure
M9  leave staging directory after PASS
M10 leave backup after PASS
M11 fail after replace but skip rollback
M12 uninstall an unowned user file
M13 dry-run mutates filesystem
M14 target one runtime but write into another runtime's private path
```

Every mutation must be rejected by a specific predicate.

- [ ] **Step 3: Produce mutation matrix**

For each mutation record:
- mutated edge/predicate;
- expected failure;
- observed verifier error;
- PASS if rejected.

---

### Task 12: Real Runtime Smoke Matrix

**Files:**
- Create: `docs/installer-smoke-report.md` during implementation evidence
- Tests may use temp homes when actual CLIs are unavailable.

**Interfaces:**
- verifies installer behavior against real available runtimes without inventing unavailable hosts.

- [ ] **Step 1: Run `doctor --json` on the current machine**

- [ ] **Step 2: For each actually installed target CLI, read current `--help`**

One command per operation.

- [ ] **Step 3: Run user-scope or isolated temp-home smoke installation**

At least one real runtime must complete:

```text
install
-> host/list discovery check
-> verify
-> invoke/list skill where automatable
-> uninstall
-> verify absent
```

- [ ] **Step 4: For unavailable runtimes, run adapter contract tests only**

Never report an unavailable runtime as live-tested.

---

### Task 13: Distribution Packaging

**Files:**
- Modify/create packaging test only; do not introduce a second nested skill root.

**Interfaces:**
- produces standalone source/distribution ZIP;
- optionally produces a pure runtime payload archive.

- [ ] **Step 1: Write packaging RED tests**

Distribution archive must contain:

```text
chunking-document-workflows/SKILL.md
chunking-document-workflows/installer/install.py
chunking-document-workflows/MANIFEST.json
```

It must not contain:

```text
chunking-document-workflows/chunking-document-workflows/SKILL.md
```

- [ ] **Step 2: Build distribution ZIP from exact verified bytes**

- [ ] **Step 3: Extract into a clean directory**

- [ ] **Step 4: Run all tests from extracted bytes**

- [ ] **Step 5: Run installer `verify` against a clean staged install**

- [ ] **Step 6: Hash final archive**

No file changes after this hash.

---

### Task 14: Final Verification Before Completion

**Files:**
- Produce final audit/evidence report.

- [ ] **Step 1: Invoke `superpowers:verification-before-completion`**

- [ ] **Step 2: Run complete existing + installer test suite fresh**

Required:
- existing 36 baseline tests still green;
- all new installer tests green;
- mutation baseline green;
- all illegal mutations rejected.

- [ ] **Step 3: Validate canonical root**

Fresh extraction must prove:

```text
<package-root>/SKILL.md
```

- [ ] **Step 4: Validate all supported target adapters**

Each target is classified as:
- live-tested;
- contract-tested;
- needs-user-action;
- unsupported.

Never collapse those states into one "supported" claim.

- [ ] **Step 5: Verify distribution hash**

- [ ] **Step 6: Completion claim only after all required predicates are green**

---

# Installer Definition of Done

The standalone-installer remediation is DONE only when:

```text
existing_document_workflow_tests_green
AND canonical_SKILL_md_at_package_root
AND manifest_valid
AND distribution_payload_explicit
AND install_transaction_atomic
AND rollback_tested
AND dry_run_non_mutating
AND superpowers_prerequisite_truthfully_resolved
AND document_profile_truthfully_resolved
AND no_native_OAI_path_used_on_non_native_runtime
AND installed_SKILL_md_at_target_root
AND installed_payload_hashes_match
AND host_discovery_verified_when_host_exposes_it
AND install_receipt_valid
AND uninstall_preserves_unowned_files
AND mutation_baseline_passes
AND every_illegal_mutation_is_rejected
AND frozen_distribution_retests_green
AND final_archive_hash_recorded
```

# Non-Goals

This remediation does **not**:

- reimplement Superpowers;
- copy Superpowers skills into this package;
- copy private/internal OAI skill trees into this package;
- claim public portable document skills are identical to internal OAI skills;
- redesign the document state machine that is already 36/36 green;
- create a universal privileged package manager;
- silently install system dependencies or alter Python/Node runtimes.

# Execution Order

```text
CURRENT 36/36 GREEN BASELINE
  ↓
manifest/version contract
  ↓
runtime/document profile abstraction
  ↓
target adapters
  ↓
Superpowers prerequisite provider
  ↓
portable OpenAI document dependency resolver
  ↓
transactional installer
  ↓
installation DoD + receipt
  ↓
uninstall/upgrade ownership
  ↓
shell/PowerShell wrappers
  ↓
mutation tests
  ↓
real-runtime smoke matrix
  ↓
frozen distribution extraction/retest
  ↓
verification-before-completion
  ↓
GREEN
```
