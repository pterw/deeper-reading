# Deeper-Reading v0.2.0 Mutation Report

Date: 2026-09-11

## Method

Each mutation begins from a valid baseline and changes one required state, byte-bound evidence edge, workflow transition, extraction property, or installer-security boundary. A mutation passes only when the package rejects the illegal state for the **intended predicate**; generic nonzero failure is not sufficient.

This is deterministic mutation/adversarial contract testing. It is not presented as independent-agent behavioral pressure testing.

## Focused v0.2 security/evidence gate — 51 tests

The focused gate is:

```text
tests/test_mutations.py                         22
tests/installer/test_install_mutations.py      17
tests/test_evidence_builder.py                 12
                                                --
                                                51
```

All 51 are included in the full 261-test release universe.

## Installer containment mutations

Receipt data is untrusted. New mutations prove rejection of:

| Mutation | Required rejection |
|---|---|
| absolute managed path | install-root containment violation |
| `../` parent traversal | install-root containment violation |
| Windows drive spelling (`C:/...`, `C:\\...`) | install-root containment violation |
| UNC-like path (`\\\\server\\share\\...`) | install-root containment violation |
| symlink-resolved escape | resolved containment violation |

The symlink case verifies the external victim file remains unchanged.

The existing installer mutation suite continues to cover canonical-root integrity, deleted/modified payload, receipt identity, document profile, staging/backup leftovers, and missing receipt state.

`force=True` does not weaken containment.

## HTML extraction-loss mutation

A generic-container fixture includes visible text in:

```text
main -> div
main -> section -> span
main tail text
```

Every expected phrase must occur exactly once in canonical extracted text. This catches the v0.1.0 failure mode where the HTML extractor could return success while silently dropping visible `div`/`section` prose.

`script`, `style`, `noscript`, and `template` remain excluded by extractor tests.

## Evidence schema-v2 mutations

Schema v2 adds deterministic atom IDs while keeping schema v1 valid.

New mutations prove rejection of:

| Mutation | Required rejection |
|---|---|
| forged `atom_id` | deterministic identity mismatch |
| duplicate `atom_id` | duplicate identity violation |
| wrong explicit byte span | exact source bytes do not match text |
| repeated quote without explicit span | ambiguity with candidate byte starts |
| partial explicit span | both byte boundaries required |

The repeated-quote case is the direct hardening of the DeepSeek prototype's `bytes.find()` behavior: production code cannot silently choose the first identical occurrence.

## Malformed-ledger mutations

New cases mutate source/preflight/evidence mapping contracts and event entries into invalid JSON shapes.

Expected behavior is deterministic verifier rejection such as:

```text
source must be an object
preflight must be an object
evidence must be an object
events[1] must be an object
```

No uncaught `AttributeError`/`TypeError` traceback is accepted as a valid failure mode.

The historical missing-vs-malformed chunking distinction is preserved after a pre-freeze regression caught the initial hardening implementation collapsing the two diagnostics.

## Reproduced-extraction timeout mutation

The verifier's source-reproduction subprocess is forced to raise `subprocess.TimeoutExpired`.

Expected and observed contract:

```text
reproduced extraction timed out after 60s
```

The timeout is a verification violation rather than an unbounded process.

## Human-report drift mutation

`TRAVERSAL_REPORT.md` remains derived evidence, not authority.

A valid grouped report is edited after generation. Verification rejects the altered report because it no longer reproduces byte-identically from the canonical manifest + evidence ledger.

Grouping the report by canonical chunk therefore improves human auditability without creating a second truth source.

## Existing workflow mutations retained

The release continues to reject:

- missing required preflight/reference evidence;
- missing written traversal plan;
- sibling/downstream traversal before failure diagnosis;
- repair/rechunk before diagnosis;
- continued repair after architecture stop without exhausted-path redesign;
- alternative design before `paths_exhausted` + `disclosure`;
- unresolved failed nodes at Done;
- early Done before final verification;
- later material events that stale a prior verification pass;
- missing/duplicate/unknown/reordered `chunk_verified` events;
- missing evidence for emitted chunks;
- forged smaller chunk universes defeated by fresh source re-extraction.

## DeepSeek first-run corpus

The real first-run corpus is now a golden regression fixture:

```text
70 canonical chunks
70 evidence verdicts
192 assertions
```

The production builder rebinding test must reproduce every known-good v1 text/span pair while emitting schema-v2 atom IDs.

The six run-local prototype scripts are preserved for provenance under the fixture tree but production code is forbidden from importing them. They are evidence of the path that discovered the useful machinery, not trusted runtime code.

## Full-release relationship

Mutation tests are a hostile boundary gate, not a replacement for full verification.

The source candidate and the extracted distribution each collect **261 tests**, and the full collected universe is required to pass before release completion. The final frozen archive SHA-256 is recorded in companion `FINAL_VERIFICATION.md` after all packaged bytes stop changing.

## Historical anti-skimming/process mutation baseline retained

The original **process mutation suite — 11/11 GREEN** remains part of the release history and current regression universe.

Its anti-skimming threat models remain explicit:

- **12 emitted / 4 evidenced:** when a 12-chunk canonical source is mutated so only 4 evidence entries remain, the verifier reports the eight missing chunks and refuses Done.
- **Skipped middle:** deleting a middle chunk verdict is rejected even when later chunks remain evidenced.
- **Early Done:** completion before the required final verification sequence is rejected.
- **Forged smaller manifest:** rewriting the manifest, hashes, coverage, and evidence ledger into a self-consistent smaller universe is still defeated by fresh **source re-extraction** against the original source bytes.

These historical cases are now joined by the v0.2 receipt-containment, extraction-loss, atom-identity, ambiguity, malformed-shape, timeout, and grouped-report mutations above.
