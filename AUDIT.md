# Hard-Standalone Package Audit

Date: 2026-09-08

## Audit target

Current implementation root: `hard-standalone-work/`

The byte authority entering the final sprint was the Task-6 installer-sovereignty checkpoint. Task 7 reconstructed and verified process mutations; Task 8 restored anti-skimming package surfaces; Task 9 established the pre-freeze regression checkpoint at **189/189 GREEN** in bounded test batches.

The final release-evidence contract adds four documentation tests on top of that regression universe. Frozen-archive verification must therefore rerun the complete current test tree from extracted bytes before completion is claimed.

## Product invariant

The product is **exhaustive traversal**, not chunking.

Chunking is the mechanical ruler that prevents the first-plausible-match exit. The canonical extractor manifest defines the chunk universe. Every emitted chunk requires exactly one atomic extractive `evidence` verdict or explicit `non_match`, plus one ordered `chunk_verified` event, before Done is reachable.

A high-level summary, a useful early fact, or a partial needle-in-a-haystack match is never completion evidence.

Final verification re-extracts the original source with the bundled extractor and requires the reproduced canonical chunk universe to match. A forged smaller manifest therefore cannot shrink the traversal obligation.

## Sovereign runtime

`standalone` is canonical/default.

There is **no required Superpowers runtime prerequisite** and no external process framework is needed for normal operation. Package-owned orchestration lives under `skills/`.

`oai-native` is optional enhancement only. It may add rendering/OCR/layout QA when those native capabilities exist; it cannot replace, shrink, or waive the standalone extraction/evidence contract.

The remaining `Superpowers` strings in `scripts/verify_run.py` and `installer/manifest.py` are rejection guards for legacy manifests/preflight keys, not runtime dependencies.

## Canonical source/distribution tree

```text
deeper-reading/
├── SKILL.md
├── README.md
├── VERSION
├── MANIFEST.json
├── AUDIT.md
├── MUTATION_REPORT.md
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
│   ├── lengthy-markdown.md
│   ├── pdf.md
│   ├── prerequisites.md
│   ├── run-workspace.md
│   ├── runtime-profiles.md
│   └── source-acquisition.md
├── scripts/
│   ├── chunk_common.py
│   ├── extract_docx.py
│   ├── extract_html.py
│   ├── extract_markdown.py
│   ├── extract_pdf.py
│   ├── traversal_report.py
│   └── verify_run.py
├── skills/
│   ├── debugging-document-workflows/SKILL.md
│   ├── executing-document-traversal/SKILL.md
│   ├── exhaustive-document-traversal/SKILL.md
│   ├── planning-document-traversal/SKILL.md
│   ├── recovering-document-workflows/SKILL.md
│   └── verifying-exhaustive-traversal/SKILL.md
├── installer/
├── tests/
└── docs/
```

The canonical skill remains root `SKILL.md`; it is not relocated beneath `.skills/`, `payload/`, `src/`, or another wrapper.


Canonical package-owned process-skill paths include:

```text
skills/exhaustive-document-traversal/SKILL.md
skills/planning-document-traversal/SKILL.md
skills/executing-document-traversal/SKILL.md
skills/debugging-document-workflows/SKILL.md
skills/recovering-document-workflows/SKILL.md
skills/verifying-exhaustive-traversal/SKILL.md
```

## Installed runtime payload

`MANIFEST.json` explicitly installs:

```text
SKILL.md
README.md
VERSION
skills/
references/
scripts/
```

This means a supposedly standalone installation cannot omit the six process skills or portable extraction tools it references.

Bundled document capability includes:

```text
scripts/extract_pdf.py
scripts/extract_docx.py
scripts/extract_html.py
scripts/extract_markdown.py
```

`references/lengthy-markdown.md` defines heading-aware Markdown traversal while fenced code blocks and tables remain atomic.

## Evidence and deliverables

Machine proof lives in the run root:

```text
<run-root>/
├── plan.md
├── run.json
├── evidence/
│   ├── chunk-manifest.json
│   ├── chunk-evidence.json
│   ├── skill-preflight.md
│   ├── source-manifest.md
│   ├── failure-ledger.md
│   ├── verification-log.txt
│   └── format-qa.md
└── deliverables/
    └── TRAVERSAL_REPORT.md
```

`chunk-evidence.json` is extractive, not abstractive. Assertions contain exact chunk byte spans. `TRAVERSAL_REPORT.md` is the deterministic human-readable mapping from every chunk ID to locator, outcome, and verified assertion/reason.

## Failure/recovery invariant

A failed node cannot be followed by sibling/fallback/downstream traversal or repair before `failure_diagnosed`.

After three failed fixes, or earlier when evidence proves the path non-viable, `architecture_stop` blocks further repair. The only redesign route is:

```text
architecture_stop
-> paths_exhausted
-> disclosure
-> alternative_designed
-> plan_revised
```

Final `verification_passed` must occur after the last material event.

## Test evidence before freeze

Bounded pre-freeze evidence covers **189/189** tests:

- installer domain: 63/63;
- non-ledger top-level domain: 107/107;
- anti-skimming ledger: 19/19.

Notable sub-gates:

- Task-7 process mutations: 11/11;
- portable extractors: 4/4;
- anti-skimming documentation/package surfaces: 24/24;
- contradiction guards: 6/6;
- run-root containment: 9/9;
- traversal report: 5/5;
- native verifier: 18/18.

The broad all-at-once command exceeded the execution time budget; each unresolved tail was re-chunked rather than rerunning the entire suite.

## Installer smoke

Current sovereign `doctor` reports:

```text
can_install: true
document_profile: standalone
document_status: ready
mutation_performed: false
```

Readiness evidence is the four bundled extractors.

A real isolated project-scope generic Agent Skills transaction completed:

```text
install
-> verify PASS
-> uninstall
-> target absent
```

Fresh install verification reported every installation predicate true and zero violations.

## Remaining gate

The source tree is not the frozen deliverable.

Completion still requires:

1. build the distribution ZIP from current bytes;
2. extract into a clean scratch directory;
3. rerun the full current suite and extraction smokes only from extracted bytes;
4. invoke verification-before-completion;
5. emit `FINAL_VERIFICATION.md` with the frozen archive SHA-256.

Until those predicates pass, the distribution is not Done.
