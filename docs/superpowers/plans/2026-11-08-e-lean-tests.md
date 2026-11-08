# Plan E: lean test suite (tests only)

Stack position: after M (0.2.4 is released), before P. Branch cut from the previous PR's head. Rows
were read at d75018c (`C:/ssw/t1`); A, B, C, D and M move files, and layer 2 confirmed only T4-9 of
E's rows (R17's category list is the authority for the rest). So **every task's first acceptance
check is a re-check of its rows at E's base**. A row that no longer holds is dropped and written up in
the task report as `DROPPED <id>: <why>`; the rest of the task goes ahead (not a NEEDS_CONTEXT case).
No task here changes a shipped byte (no MANIFEST, scripts, references or skills edit), so no payload gate
is needed beyond one final run.

## 1. Goal and rows closed

Remove duplicate, vacuous, wording-pin and report-file-pin tests so the suite is smaller and every
test names a behaviour a regression would break. Behaviour tests and required-instruction pins stay.
Rows: T3-1,2,3,5,6,7,8,9,10,11,12,13,15,16,17; T4-1,3,4,9,13; T2-05,06,07,08,11,12; K5;
T1-07, T1-08 (listed pairs), T1-10, T1-16 (handed over by plan B, task E7).

## 2. Not in scope

- P (shipped prose and payload): P1-04,06..12 (failure ladder, PDF provenance, run-workspace route, oai-native,
  DOCX text, substitution copies), K3, K4, T3-14 (README out of payload, CONTRIBUTING out of the ZIP).
  The old E8-E13 are P's. Review points on phase-load coverage (E12/E11) and the `/home/oai/skills`
  pin belong to P; see Handoff to P (section 7).
- T2-16 (shared extractor `main()`, old E7): out of the train (R18); backlog. Nothing here edits scripts/.
- T3-4, T2-09, T2-10, T2-14, K7: verifier tests and codes, PR B. T2-01..04, T2-18: PR A. T2-13,15,17,19:
  not named for E. T4 rows other than 1,3,4,9,13: PR C. K1, K2, K6, media: PR D/M.
- From plan B's hand-offs, not taken: T1-09 (Finding/catalogue tests; O10 owns the catalogue test),
  T1-11, T1-17 (B5 adds the rows), T1-12 and T1-13 (fixture rewrite, ~77 call sites: backlog),
  T1-14, T1-15, T1-06/C1-08 (cut of `validate_run`; CHANGELOG promises it; owner call), T2-17,
  `load_verify` and the report-heading pins. From plan C: the receipt key list in core.test.js
  (C leaves it; not taken). From plan D: D1-07,08,11,13,14 (prose) and the P1-02 pin decision go to P.
- Release, version, CHANGELOG body. E has no product change, so no CHANGELOG line (R13/R17: confirm,
  section 7). Stale "261 tests" in AUDIT.md:11 (a dated history sentence).

## 3. Frozen interfaces

- Survivor owners (one test owns each pin; other files drop it):
  Superpowers absence -> `tests/test_hard_standalone_release_contract.py::test_package_text_has_no_external_process_framework`
  (covers SKILL.md, README.md, installer/USAGE.md, references/*.md, skills/*/SKILL.md; B7 has removed the
  legacy `using_superpowers_read` keys, so scripts/verify_run.py joins only if the re-check shows none left);
  manifest contract -> `tests/installer/test_manifest.py::test_manifest_contract` (D adds the link-resolver test there);
  document-profile status -> `tests/installer/test_prerequisites.py`;
  required routes -> `tests/test_phase_gated_loading.py` (route lists stay: AGENTS.md:213);
  required instructions -> the E2 table (below).
- E2 table (R21): one parametrized test in `tests/test_anti_skimming_docs.py`, rows
  `(instruction, file, loading_module)`. It asserts the instruction is in `file`, and that
  `loading_module`'s `SKILL.md` links `file` (the phase that loads it). An instruction is something an agent
  executes (a state or event name, a finding code, a path, a command, a numeric rule), never a bag of
  common words and never a single incidental sentence. P edits rows, not the test body, when it moves prose.
- Pins that stay unchanged: "one recovery branch at a time"; "fourth fix"; "twelve emitted chunks require
  twelve"; "forged smaller manifest"; "document profile" in docx.md and pdf.md; `heading1`/`heading6` in docx.md;
  `evidence/chunk-manifest.json` and `deliverables/TRAVERSAL_REPORT.md` in evidence.md and deliverable.md.
- Escape-spelling data (E4, written against C6's head): a fixture `tests/fixtures/receipt-escape-spellings.json`
  is created only if the E4 re-check finds the same guard-only list in both runtimes. It holds exactly C6's
  non-victim literals: `../outside.txt`, `C:foo`, `Z:/dr-no-such/x`, `//dr-no-such-host/share/x`. The
  tmp-victim spellings stay built at runtime. No real-location literal returns:
  `git grep -nE "C:[/\\\\]outside|/tmp/outside|server.share" tests/` stays empty.
- Mutation procedure (every task): "mutation" means edit the file in the work tree, run the named test, see it
  fail, restore with `git checkout -- <file>`; record command and output in the report.

## 4. Tasks

Waves are file-disjoint. Same-file tasks sit in later waves (`After`). Python tasks run ruff.

### E1 Consolidate package-contract tests (T3-1,2,3,5,6,7,9,10,16; K5)
Wave 1 | Mode code | After - | Touches: tests/test_hard_standalone_release_contract.py,
tests/test_task6_installer_sovereignty.py (delete), tests/test_portable_payload.py (delete),
tests/test_workflow_contract.py, tests/installer/test_manifest.py,
tests/installer/test_portability_contradictions.py, tests/installer/test_runtime_profiles.py,
tests/test_hard_standalone_docs.py, tests/installer/test_cli.py
- One case-insensitive "superpowers" test over the survivor list in section 3 (add the skills/*/SKILL.md glob and
  installer/USAGE.md, which carries the `--superpowers` guard now in test_release_evidence.py). Delete the other seven copies.
- Delete: the two `inspect.signature(install_skill)` tests; the manifest tests in release_contract, task6 and
  portable_payload; the `getsource(verify_installation)` test; the three file-exists tests in test_workflow_contract.py;
  test_portable_payload.py. Drop the `verify_run.py not in payload` line (K5) from test_manifest_contract. In
  test_hard_standalone_docs.py delete the tests that repeat anti_skimming or installer/test_runtime_profiles (root mission,
  runtime-profile headings, process-skill names); keep the `index("standalone") < index("oai-native")` test.
- Move the one behaviour out of task6: `parse_args(["install","--dry-run"]).document_profile == "standalone"` to
  tests/installer/test_cli.py. The real-root "standalone ready" case is added by E3.
- Accept: (1) re-check: `grep -n "def test_" ` on each touched file lists the test names this task deletes (named in its
  report); the two source-parsing tests B7 edits in release_contract are left alone;
  (2) `python -m pytest -q tests/test_hard_standalone_release_contract.py tests/installer/test_manifest.py tests/installer/test_cli.py tests/test_hard_standalone_docs.py` passes;
  (3) mutation: add "Superpowers" to references/control-flow.md, then to skills/planning-document-traversal/SKILL.md, then to
  installer/USAGE.md; the survivor test fails for each; (4) `grep -rn "task6" tests/` is empty.

### E2 Report-file pins and word bags become one instruction table (T3-11,12,13,15,17)
Wave 2 | Mode serial (human read of the AGENTS.md hunk) | After E1 | Touches: tests/test_release_evidence.py (delete),
tests/test_anti_skimming_docs.py, tests/test_contradictions.py, tests/test_phase_gated_loading.py,
tests/installer/test_manifest.py, AGENTS.md
- Delete test_release_evidence.py (AUDIT.md, MUTATION_REPORT.md, smoke report and USAGE.md word pins). Its USAGE.md
  `--superpowers` guard is already in E1's survivor test; test_wrappers.py:23 keeps pinning USAGE.md. AGENTS.md: line 28 stops
  saying AUDIT.md and MUTATION_REPORT.md are "pinned by contract tests" (USAGE.md stays pinned, by test_wrappers.py); the list at
  lines 161-165 drops AUDIT.md and MUTATION_REPORT.md. Written generally ("pinned where a test names them"), not as a closed list.
- test_anti_skimming_docs.py: replace every common-word bag (lines ~17-22, 37-38, 49-61, 90-95) and the two near-identical
  dependencies/runtime-profiles tests with the section 3 table. Per bag: keep the instruction an agent executes as a row, or cut the
  assertion. Keep the README pins (85-95, 127-142) until P decides their fate (README stays shipped in E).
- test_contradictions.py: tighten `"three" in text or "3" in text` to "fourth fix" only.
- Link resolver: extend D's T5 test in tests/installer/test_manifest.py (every relative link in the payload `.md` files resolves) to
  cover SKILL.md and skills/*/SKILL.md if D's roots miss them. Add no second link test. test_phase_gated_loading.py keeps its route
  lists, routing-table test and negative ownership checks, and is not otherwise edited.
- Accept: (1) re-check: `grep -rn "189/189\|11/11" tests/` shows the pins; `grep -rln "test_documented_run_shape\|media" tests/*.py`
  lists D/M's prose-reading tests, which are left as they are; (2) pytest on the touched test files passes; (3) mutation: for each table
  row, remove its instruction from the file (edit, run, restore): that row fails and no other does; also move one link target: the
  link test fails; (4) `git diff AGENTS.md` shows only the two lines, and the controller reads it before merge.

### E3 Installer test duplicates (T4-1, T4-4, T3-8, T4-9, T4-13)
Wave 1 | Mode code | After - | Touches: tests/installer/test_install_dod.py (delete),
tests/installer/test_document_profiles.py (delete), tests/installer/test_install_mutations.py,
tests/installer/test_prerequisites.py, tests/installer/test_distribution_archive.py, tests/node/discovery.test.js
- test_install_dod.py is covered by test_install_mutations.py (baseline :40, document-profile-missing :63, hash tamper :84, stage
  leftover :103), except that the baseline there asserts only `passed`: first add the `all(predicates.values())` and
  `violations == []` assertions to that baseline, then delete the file.
- test_document_profiles.py has five tests; four duplicate test_prerequisites.py. Move
  `test_oai_native_fails_closed_when_internal_root_missing` into test_prerequisites.py, add one
  `document_profile_status("standalone", package_root=ROOT)` ready case, then delete the file.
- T4-9: the tarball-exclusion test builds its package inside `tmp_path`, not the repo root.
- T4-13, conditional on C2: if at C's head the discovery fixture table already records and asserts `(command, args)` for the `failed`
  cases, this half is `DROPPED T4-13: done by C2`. Otherwise record argv in the table's mock and assert it after `discoveryVerify`
  returns. Do not re-add spawnSync patching C2 removed.
- Accept: (1) re-check: the five-vs-four test names above, and `grep -n "argv\|args" tests/node/discovery.test.js` decides T4-13;
  (2) `python -m pytest -q tests/installer/test_prerequisites.py tests/installer/test_install_mutations.py tests/installer/test_distribution_archive.py`
  passes and `git status --short` shows no `*.tgz` in the repo root afterwards; (3) `npm test` passes; (4) mutation: break the `failed`
  fixture's expected argv (if T4-13 applied): that case fails; delete a predicate-setting line in a temp install: the new baseline assertion fails.

### E4 Share the receipt escape spellings that remain after C6 (T4-3, reduced)
Wave 1 | Mode code | After - (E branch contains C6) | Touches: tests/fixtures/receipt-escape-spellings.json (new, only if needed),
tests/installer/test_install_mutations.py, tests/installer/test_uninstall.py, tests/installer/test_upgrade_ownership.py,
tests/node/core.test.js, tests/node/manifest.test.js
- C6 already retargets the absolute spellings at the tmp victim and keeps `../outside.txt`, `C:foo` and one drive and one UNC
  literal in a guard-only parametrized test per runtime. E4 does only what is left: Python runs the full matrix once
  (test_install_mutations.py); uninstall and upgrade keep one spelling plus their symlink test; Node `managedPath` runs the matrix
  and core.test.js uninstall keeps one spelling. Create the JSON fixture and read it from both runtimes only if C6 left the same
  list typed out in both languages. Leave test_concurrent_transactions.py alone (None, empty, lower-case drives).
- Accept: (1) re-check: `grep -rn "C:foo\|dr-no-such" tests/` lists the copies; if each runtime already has one matrix and the
  others one spelling, `DROPPED T4-3: done by C6` and the task ends; (2) pytest on the three Python files passes; (3) `npm test` passes and
  the C6 grep in section 3 is empty; (4) mutation: make `_managed_path` accept `C:foo`: the matrix test and the one-spelling
  uninstall test both fail; same for `managedPath` in installer/node/manifest.js.

### E5 Extractor and PDF test duplicates (T2-05,06,07,08)
Wave 1 | Mode code | After - | Touches: tests/test_extractors.py, tests/test_pdf_provenance.py
- One parametrized heading_path test over (markdown, html, docx) with each writer helper; merge the three HTML tests into the
  mixed.html one (keep the manifest-integrity and skip-tag assertions). A, D and M add cases to these tests: extend their cases,
  never replace them.
- test_pdf_provenance.py: drop `test_pdf_fixture_hashes` and the unused `tmp_path`; keep the timeout bound and the `secret-value`
  assertion (it guards that the password never reaches the error text, as the test name says). The CLI PDF test in test_extractors.py shrinks
  to exit code plus manifest integrity (the backend test owns page facts).
- Accept: (1) re-check: the three heading tests still differ only by helper; (2) pytest on both files passes, SKIPPED reasons
  unchanged (skip budget); (3) mutation: make extract_html drop `h3` from the heading stack: the parametrized test fails for html only.

### E6 Derived fixture counts and prototype removal (T2-11, T2-12)
Wave 1 | Mode code | After - | Touches: tests/test_evidence_builder.py, tests/test_traversal_report.py,
tests/fixtures/deepseek-first-run/prototype/ (delete), tests/fixtures/deepseek-first-run/README.md, AUDIT.md, MUTATION_REPORT.md
- Replace the literal 70 and 192 with counts computed from the fixture ledger (entries, atoms); drop the redundant count assertions
  (~168-169) and the test names that carry the constants. B6 edits test_traversal_report.py: rebase on it, change only these counts.
- Delete `test_deepseek_prototype_is_fixture_only_not_runtime` and `prototype/` (read by nothing), remove its hash lines from the
  fixture README, and fix the one sentence each in AUDIT.md (~112) and MUTATION_REPORT.md (~139) saying the scripts are preserved.
  These two files are release evidence, no longer pinned after E2; they are not shipped.
- Accept: (1) re-check: `grep -rn "prototype" --include=*.py --include=*.js .` outside the test and the fixture README is empty;
  (2) pytest on the two test files passes; (3) `python -m ruff check .` passes; (4) mutation: drop one atom from the ledger: the
  derived-count test fails.

### E7 Verifier-suite duplicates handed over by plan B (T1-07, T1-08 pairs, T1-10, T1-16)
Wave 2 | Mode code | After E1 | Touches: tests/test_verify_run_parity.py, tests/test_mutations.py,
tests/test_native_verifier_protocol.py, tests/test_anti_skimming_ledger.py
- This is not the old E7 (extractor main, R18). Take only equal-body duplicates, keeping the copy in test_verify_run.py: the
  four "valid run has no violations" tests become the parity baseline test (renamed, keeps the predicates and `violations == []`
  assertions); delete the mutation or native copy of each pair listed in the T1-08 row (done-before-verification, preflight,
  sibling-after-failure, stale final verification, event-entry-object, reproduced timeout, forged and duplicate atom_id) where the
  surviving copy asserts the same code; delete `test_build_dod_no_longer_parses_prose` (T1-10, source-text pin; B7 may have changed
  `build_dod`); delete the two T1-16 tests that repeat test_extractors.py. Tests whose fixtures differ are kept. B's tables and
  B5's rows are never deleted.
- Accept: (1) re-check: each pair still has equal bodies at E's base (list pairs in the report; a changed pair is `DROPPED`);
  (2) pytest on the four touched files plus test_verify_run.py and test_verification_findings.py passes; (3) mutation: for each
  deleted pair, remove the verifier check it covers (edit scripts/verify_run.py, restore): the surviving copy fails;
  (4) `python -m ruff check .` passes.

## 5. Dispatch

| Wave | Tasks | Agents |
|---|---|---|
| 1 | E1, E3, E4, E5, E6 | 5 |
| 2 | E2, E7 | 2 |

Peak 5. Landing order: E1, E3, E4, E5, E6, E2, E7, a gate run after each landing; each task re-runs its re-check on the landed base
first. Commit subjects:
E1 `test: keep one test per package-contract behaviour` | E2 `test: replace report-file pins and word bags with an instruction table` |
E3 `test(installer): drop duplicate install and profile-status tests` | E4 `test(installer): share the receipt escape spellings that remain` |
E5 `test: parametrize heading tests and drop fixture-only checks` | E6 `test: derive fixture counts and drop the unused prototype` |
E7 `test(verify): drop duplicate verifier tests`

## 6. Gates (AGENTS.md block, scoped)

- pytest: every task. ruff: E1, E2, E3, E4, E5, E6, E7. `npm test`: E3, E4, and once at the PR head.
- pack-smoke, installer-doctor, distribution: no shipped path changes (E touches tests, AGENTS.md, AUDIT.md, MUTATION_REPORT.md);
  run once at the PR head as the final PR gate. release-labels: not run (no VERSION, package.json, CHANGELOG or tools change).
- Final PR gate: the full AGENTS.md list before the push. Skip budget: no new skip, no changed skip reason.

## 7. Risks, open questions and handoff

- CHANGELOG: R17 says E and P lines go in `## Unreleased`; E changes no product behaviour (tests, one rule file, two history
  documents), so this plan adds no line. If the controller wants one ("tests trimmed"), it fires release-labels; say so at dispatch.
- Owner read at PR time: the AGENTS.md hunk in E2 (a rule file). E2 is serial for that reason.
- Overlap order: C6 before E4, C2 before E3, D T5 before E2, B7 before E1 and E7, B6 before E6, M's prose-reading tests before E2.
  Tests A, B, D and M add to files E edits are extended, never replaced.
- Tests that pin prose P will cut (runtime-profiles, dependencies, docx, pdf) are table rows after E2, so P edits a row, not logic.
- Handoff to P: (a) a test that an upgrade removes the previously installed README.md (R20; K3 is otherwise untested); (b) the
  phase-load check for each cut (html.md and pdf.md substitution text is read at extraction, deliverable.md "Prohibited
  substitutions" is loaded only by planning-document-traversal: keep the cut or route it; failure-recovery.md is routed only from the
  debugging and recovering modules, so shrunk copies must name those modules); (c) the oai-native pin: per R19 retarget
  tests/installer/test_runtime_profiles.py to the standalone route and keep the concrete `/home/oai/skills` path in the oai-native
  reference; (d) D's LICENSE payload row (T5) existed to fix README's `(LICENSE)` link; README leaves the payload in P, so the
  controller decides whether LICENSE still ships; (e) D's link test must tolerate README leaving the payload; (f) README pins in
  test_anti_skimming_docs.py (85-95, 127-142) and the README target in core.test.js belong to P's K3 task.

## Implementation notes (controller, from review-E-2; binding on E7)

- T1-16 is three tests: only the HTML one repeats tests/test_extractors.py (E5 merges its
  survivor into the mixed.html test); the other two repeat
  tests/test_evidence_builder.py:102 and :79. Remove each only after naming its survivor.
- T1-07: keep the copy in tests/test_verify_run.py (do not delete line 22; it is not in
  E7's Touches) and keep tests/test_anti_skimming_ledger.py:159 (its fixture differs; the
  plan's own rule keeps it). tests/test_traversal_report.py:109 still covers a valid
  multi-chunk run.
- The Minors in review-E-2 apply as written.

## Drift notes (controller, R56 from review-E-drift.md; binding)

Base is main 011d55a: A, B, C, D, M, the follow-ups and the 0.2.4 release are merged, and the branch is cut
from origin/main. These notes override the task text above where they differ.

- D1 E1: the survivor keeps its current name, `test_runtime_payload_does_not_require_external_process_framework`
  (tests/test_hard_standalone_release_contract.py:19); no rename. scripts/verify_run.py stays in its scanned list
  (it has no "superpowers" since B7). B7 left one source-parsing test there,
  `test_verifier_uses_package_native_process_vocabulary` (:46); leave it.
- D2 E1 Touches also include tests/test_package_owned_process_skills.py: delete its two superpowers asserts
  (:27-28), which the survivor covers once it scans skills/*/SKILL.md case-insensitively. Leave the rest of that
  file alone (its `CASES` word bag is backlog, not E1 scope). The copies E1 removes: test_hard_standalone_docs.py
  :33, :53; test_portability_contradictions.py :14, :21; test_runtime_profiles.py :21;
  test_package_owned_process_skills.py :27-28; and the copies in the files E1 deletes.
- D3 E1: the moved CLI check is
  `installer.install.build_parser().parse_args(["install", "--dry-run"]).document_profile == "standalone"`.
  Accept (4) is `git grep -n task6 tests/` (empty), not `grep -r` (stale .pyc files match).
- D4 Mutation procedure, every task (replaces the `git checkout -- <file>` clause in section 3): save the file
  with `cp <file> WORKSPACE/scratch-<TASK>/<name>.orig`; apply the edit with a small script (never `sed -i`;
  mutate.py does not run pytest); run the named test and quote the failure; `cp` the saved bytes back; quote the
  test passing; confirm `git diff --stat -- <file>` equals its value before the mutation. Never `git checkout`
  or `git restore` a work-tree file. A mutation is never part of the patch.
- D5 Waves: E3 and E4 both edit tests/installer/test_install_mutations.py, so E4 moves to wave 2, After E3.
  Wave 1: E1, E3, E5, E6. Wave 2: E2, E4, E7. Landing order: E1, E3, E5, E6, E2, E4, E7.
- D6 E3: `DROPPED T4-13: argv for copilot and gemini is asserted by tests/node/discovery.test.js:50-58; the
  fixture table's mock (withResult, :16) asserts nothing, so no assertion is swallowed`. tests/node/discovery.test.js
  leaves E3's Touches and E3 runs no `npm test`. E3's real-root ready case,
  `document_profile_status("standalone", package_root=ROOT)`, is required: it replaces the check E1 deletes
  with test_task6_installer_sovereignty.py.
- D7 E3 Accept (2): `*.tgz` is gitignored (.gitignore:22), so after pytest check `ls *.tgz` in the repo root is
  empty, not `git status --short`. The test builds its package under tmp_path.
- D8 E4 applies (not `DROPPED T4-3`). At 011d55a the six-spelling matrix is typed in test_install_mutations.py:141,
  test_uninstall.py:53 and test_upgrade_ownership.py:77; Node has the matrix at core.test.js:127-148, a guard loop
  at :116-125 and a separate `managedPath` list at manifest.test.js:68. Python keeps the full matrix once
  (test_install_mutations.py); uninstall and upgrade keep the `absolute` (tmp victim) spelling plus their symlink
  test. No JSON fixture: the spellings stay typed in each runtime. Accept (4) adds a second mutation: make
  `_managed_path` (and `managedPath`) accept an absolute path; the kept uninstall and upgrade tests fail.
- D9 E5: the merged HTML test keeps `--max-bytes 80`, so `assert_manifest_integrity` spans several chunks. The
  heading tests are test_extractors.py:124, :166, :359; the three HTML tests to merge are :134, :153, :176;
  `test_pdf_fixture_hashes` is test_pdf_provenance.py:31; the CLI PDF test is test_extractors.py:522.
- D10 E6: Accept (1) is `git grep -n prototype -- '*.py' '*.js'`. Also edit
  tests/fixtures/deepseek-first-run/README.md:3 and :23, which describe the deleted prototype. Run
  tests/test_release_evidence.py after the AUDIT.md and MUTATION_REPORT.md edits (E6 lands before E2 deletes it).
  Accept (4) mutates the producer (make `render_traversal_report` skip one `- bytes` line, or the builder drop one
  assertion), not the fixture ledger, whose change would move both sides of the comparison. The counts are at
  test_evidence_builder.py:168-169 (redundant with :155; drop them) and test_traversal_report.py:151-153 (derive them).
- D11 E7: a pair is equal when the mutation and the asserted needle are the same; incidental keys (`evidence` on
  `node_passed`, `uri` in the timeout manifest) do not count, and the survivor in tests/test_verify_run.py is the
  superset. Accept (3) proves it. Keep tests/test_native_verifier_protocol.py:94-117 (R38 legacy-acceptance tests).
  Delete its baseline `test_valid_run_baseline_passes_with_native_preflight` (:88) only after naming
  test_verify_run.py:25 as its survivor. "line 22" in the implementation notes is now test_verify_run.py:25.
  tests/test_anti_skimming_ledger.py needs no edit.
- D12 E2: D's link test (tests/installer/test_manifest.py:69) already covers SKILL.md and skills/*/SKILL.md (its
  roots are every payload `.md`), so E2 adds no link test and drops test_manifest.py from its Touches; the "move one
  link target" mutation still applies. The only D/M prose-reading test is tests/test_documented_run_shape.py (left
  alone). Accept (1) is `git grep -nE "189/189|11/11" tests/`. Bags in test_anti_skimming_docs.py are at :17-22,
  :36-40, :49-61, :90-95; README pins at :84-95, :127 and :140-141 stay (R39). Table rows on SKILL.md and README.md
  have no loading module (`None`), and their link check is skipped.
- D13 Section 7: R25 governs (Supersedes R17's CHANGELOG clause for E). E adds no CHANGELOG line, and no
  `## Unreleased` exists (CHANGELOG.md:3 is `## 0.2.4 - 2026-11-08`). release-labels is not run locally (CI still
  runs it). pack-smoke runs at the PR head because E4 edits tests/node/. AUDIT.md:163 and completed plans under
  docs/superpowers/plans/ stay as history. Handoff (d) is decided by R28: LICENSE stays in the payload.
