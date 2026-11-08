# Plan P: shipped prose trim and payload (last PR of the train)

Train: A, B, C, D, M (release 0.2.4), E, P (R17). P branches from E's head. Rows were read at d75018c
(`C:/ssw/t1`); layer 2 did not verify them and A-E have moved files. **Every task's first acceptance
check re-checks its rows at P's base.** A row that no longer holds is dropped and reported as
`DROPPED <id>: <why>`; the rest of the task goes ahead. Line numbers are d75018c's. A mutation check
means: edit the file in the checkout, run the test, `git checkout -- <file>`. Before a cut, grep
`tests/` for the file name and the cut phrases.

## 1. Goal and rows closed

Delete copies of facts another file owns, load `oai-native`-only text only under that profile, and ship
only what the skill needs. Each cut shows that the surviving owner loads at or before the phase that
needs the instruction (the "Phase" line of each task). Closes: P1-04, P1-06, P1-07, P1-08, P1-09,
P1-10, P1-11, P1-12, K3, K4, T3-14.

## 2. Not in scope

- E1-E6 (tests, report-file pins, escape spellings, discovery argv, the P1-02 test pin) -> PR E.
- E7 / T2-16 (shared extractor main()) -> backlog (R18).
- D1-07, D1-08, D1-11, D1-13, D1-14 (README, USAGE, CONTRIBUTING prose): unverified, not named for P by
  R17, and D edits those files (T6, T11, T12). Not taken; the controller may assign them.
- P1-01, P1-02, K1, K2 -> D. Media text in format references -> M. P1-03, P1-05, P1-13..P1-15: not named.
- B and C hand-offs to "PR E" (T1-07..T1-16, T2-17, C1-08, `load_verify` pins, core.test.js receipt keys): tests.

## 3. Frozen interfaces

F1. Fact owners after P: failure ladder (`architecture_stop -> paths_exhausted -> disclosure ->
alternative_designed -> plan_revised`) -> `references/failure-recovery.md`; run-root tree and the
`--run-root` commands -> `references/run-workspace.md`; report grouping and deliverable-side
"Prohibited substitutions" -> `references/deliverable.md`; source-side rule (section "Source/task
invariants") -> `references/control-flow.md` section 7, which stays (PT5); PDF `extraction` object and
`--password` limit -> `references/pdf.md`; oai-native only text -> `references/oai-native.md` (F2).

F2. `references/oai-native.md` (new), keeping the concrete `/home/oai/skills` path: the roots list
(dependencies.md 5-14), the full-read rule (16-29), the oai-native Authority sentence, the DOCX steps
(docx.md 5, 10), the PDF live-guidance step, render loop and conditional branches (pdf.md 11, 26-35,
50-52). Route: the "Source acquisition and extraction" block of
`skills/exhaustive-document-traversal/SKILL.md`, one conditional line (profile resolved to `oai-native`:
read it before the format route). Nothing else routes it. It ships through the existing `references`
entries of `MANIFEST.json`, `package.json` `files` and `RELEASE_DIRECTORIES`; no ship list is edited.

F3. Ship split: `README.md` leaves `MANIFEST.json` `payload` only (stays in `package.json` `files` and
`RELEASE_FILES`); `CONTRIBUTING.md` leaves `RELEASE_FILES` only. Nothing is added to any list.

F4. The R21 table is E's one parametrized instruction -> file test. P edits rows only, when an
instruction moves, and adds no second table. Presumed home `tests/test_phase_gated_loading.py`; the
dispatch reads E's head and writes the real path into each brief.

F5. Pins that keep passing unchanged: "one recovery branch at a time" (source-acquisition.md), "fourth
fix" (failure-recovery.md), "twelve emitted chunks require twelve" and "forged smaller manifest"
(control-flow.md section 3), "document profile" (docx.md, pdf.md), `heading1`/`heading6` (docx.md), the
manifest, ledger and report paths and `skill-preflight.md`/`format-qa.md` (evidence.md, deliverable.md
prose), `## standalone`/`## oai-native`/"optional enhancement"/"may NEVER alter" (runtime-profiles.md).

## 4. Tasks

Pins are tokens a gate or an agent consumes (paths, state names, routes). No new wording pins, no
phrase-removal mutation tests. Tasks are 5-10 minutes; PT4 is the largest (about 60 lines move across
four files plus the new one) and is not split because its files collide.

### PT1 One failure ladder (P1-04, P1-06; was E8)
Wave 1 | Mode code | After - | Touches: references/prerequisites.md, references/control-flow.md,
references/source-acquisition.md, references/html.md, tests/test_hard_standalone_docs.py
- prerequisites.md "Failure ordering" becomes one line naming `debugging-document-workflows` and
  `recovering-document-workflows`. control-flow.md sections 4-5 shrink to
  `node_failed -> STOP -> debugging-document-workflows -> failure_diagnosed` and
  `architecture_stop -> recovering-document-workflows`, each linking failure-recovery.md; sections 1-3,
  6, 7 stay. Reword "invoke systematic debugging" (html.md:76, source-acquisition.md:55) to "stop; load
  debugging-document-workflows; record failure_diagnosed"; "brainstorm alternatives" (:62) to "disclose,
  then follow the recovery protocol".
- Phase: both references load at activation, before any failure, and name both modules. The modules load
  failure-recovery.md when needed (debugging: "after a node fails"; recovering: "before alternative design";
  both routes pinned in test_phase_gated_loading). The root Quick path carries the same two routes.
- Pins: the control-flow five-state-name test in test_hard_standalone_docs.py is retargeted to
  failure-recovery.md and merged with its failure-recovery test. Its two negative asserts become one
  parametrized test over SKILL.md, skills/*/SKILL.md, references/*.md with exact needles
  `systematic-debugging`, `invoke systematic debugging`, `brainstorm alternatives` (not the stem:
  `already-brainstormed` is pinned; anti-patterns.md has a "Brainstorming too early" heading).
  Unchanged: test_contradictions, test_portability_contradictions (sections 1-2 stay).
- Accept: (1) re-check: `grep -n "systematic debugging\|brainstorm alternatives" references/` shows 3 lines;
  (2) after: grep empty; `grep -c paths_exhausted references/*.md` nonzero for failure-recovery.md only;
  both modules named in control-flow.md and prerequisites.md; (3) pytest on test_hard_standalone_docs.py,
  test_contradictions.py, test_anti_skimming_docs.py, test_package_owned_process_skills.py,
  tests/installer/test_portability_contradictions.py passes; (4) mutation: restore "invoke systematic
  debugging" in html.md; the parametrized test fails for html.md only.

### PT2 PDF provenance into the PDF reference (P1-07; was E9)
Wave 1 | Mode code | After - | Touches: references/runtime-profiles.md, references/pdf.md, the R21 table file
- Move the `extraction` object, "text backends cannot justify ocr-verified" and the `--password` limit
  to pdf.md; delete "PDF manifests made before 0.2.3" (CHANGELOG owns it). Re-read the section and
  `verify_run.py` at base: A (R10 empty-PDF message), B or C may have changed the rule; carry the current
  one. If D's run.json block shows `extraction`, link it instead of repeating.
- Phase: pdf.md loads at the PDF route, before `extract_pdf.py --help`, so before the record is copied into
  run.json and before `--password` is chosen. runtime-profiles.md loads at activation for every format,
  which is why the text leaves it. Add one R21 row: copy the extraction object -> pdf.md.
- Pins: none on the section; runtime-profiles keeps the F5 tokens and the "basic text traversal only" paragraph.
- Accept: (1) re-check: `grep -n extraction references/pdf.md` is empty today; (2) after, pdf.md has the
  object and `grep -n "PDF provenance" references/runtime-profiles.md` is empty; (3) pytest on
  test_anti_skimming_docs.py, test_hard_standalone_docs.py, tests/installer/test_runtime_profiles.py and the
  table file passes; (4) mutation: delete the object from pdf.md; the new row fails.

### PT3 Route run-workspace.md and keep one run-root tree (P1-11, P1-12; was E10)
Wave 2 | Mode code | After PT2 | Touches: skills/exhaustive-document-traversal/SKILL.md,
references/run-workspace.md, references/evidence.md, references/deliverable.md,
tests/test_phase_gated_loading.py, tests/test_anti_skimming_docs.py
- Route run-workspace.md from the "Source acquisition and extraction" block (the only file with the
  `--run-root` commands). One tree stays there; evidence.md and deliverable.md drop theirs and link to it,
  keeping the artifact paths in prose (F5). deliverable.md names `evidence/skill-preflight.md` and
  `evidence/format-qa.md` today only inside its tree, so its machine-bundle paragraph must name both
  (test_contradictions pins them). "Grouped by canonical chunk" stays in deliverable.md only;
  evidence.md keeps its run.json block (D's T3 text untouched).
- Phase: the first run file is emitted by the extractor with `--run-root`, in the block that now routes the
  file. evidence.md loads later (executing). deliverable.md loads at planning and needs only
  `<run-root>/deliverables/`, which stays in its prose.
- Pins: the run-workspace test in test_anti_skimming_docs.py keeps the path tokens for evidence.md and
  deliverable.md and retargets the tree check to run-workspace.md; test_contradictions bundle names unchanged;
  the exhaustive-module route list gains run-workspace.md; add an R21 row (extractor commands ->
  run-workspace.md). Re-grep at base: D's `tests/test_documented_run_shape.py` (reads fenced JSON blocks of
  evidence.md; the cut tree is a `text` fence, so it must stay green) and D/M media tests.
- Accept: (1) re-check: `grep -rn run-workspace SKILL.md skills references` shows two "See" links only;
  (2) after, the module links it and the D link-resolver test passes; (3) `grep -c "chunk-manifest.json"
  references/evidence.md` and `grep -c "deliverables/TRAVERSAL_REPORT.md"` on evidence.md and deliverable.md
  stay above 0; (4) pytest on the touched tests and test_documented_run_shape.py passes; mutation: drop the
  route line; the route test fails.

### PT4 oai-native text into its own reference (P1-08; was E11, R19)
Wave 3 | Mode code | After PT2, PT3 | Touches: references/oai-native.md (new), references/dependencies.md,
references/runtime-profiles.md, references/docx.md, references/pdf.md,
skills/exhaustive-document-traversal/SKILL.md, tests/installer/test_runtime_profiles.py,
tests/test_phase_gated_loading.py, tests/test_anti_skimming_docs.py (only if a pin moves)
- Create oai-native.md per F2 and cut the copies from dependencies.md (roots, full-read rule, oai-native
  Authority sentence), docx.md (profile sentence, step 3) and pdf.md (step 4, render loop, "Conditional
  native branches"). dependencies.md keeps shared CLI prerequisites, standalone basic extraction,
  installation and the standalone authority sentence; docx.md and pdf.md keep their "document profile"
  opening and a one-line pointer; runtime-profiles.md `## oai-native` keeps its text plus one pointer line.
  Reword the two standalone sentences that name the path as a ban (dependencies.md:81, docx.md:19) to
  name no host path. Re-read A's PDF no-text-layer message at base: pdf.md's OCR pointer must agree. Cut
  around D's T15 (dependencies.md) and M's media text (docx.md).
- Phase: the profile is resolved at activation (runtime-profiles.md; receipt `runtime_profile_resolved`).
  oai-native.md loads in the extraction block, before the format route and before any `/home/oai/skills`
  tree is read: the first phase that needs the roots and the full-read rule. Render loop and branches
  are QA-phase and load earlier than needed.
- Pins: in `tests/installer/test_runtime_profiles.py::test_native_profile_is_optional_enhancement_only`
  the "no /home/oai/skills in the oai-native section" assert is replaced by a parametrized assert:
  `/home/oai/skills` is absent from SKILL.md, skills/*/SKILL.md and every references/*.md except
  oai-native.md, and present in oai-native.md. "optional enhancement" and "may NEVER alter" stay. The
  "visual"/"ocr" (runtime-profiles) and dependencies-bag pins in test_anti_skimming_docs.py are checked by
  running them. Add the route to `test_exhaustive_module_owns_all_four_format_routes` and an R21 row
  (read the oai-native reference under that profile -> exhaustive module).
- Accept: (1) re-check: `grep -c oai-native references/*.md` (dependencies 10, runtime-profiles 4, pdf 4,
  docx 3 today); (2) after, `grep -rln "home/oai" SKILL.md skills references` lists oai-native.md only;
  (3) pytest on the four test files, test_hard_standalone_release_contract.py and D's link-resolver test
  (oai-native.md links back to runtime-profiles, pdf and docx) passes; installer-doctor,
  distribution, pack-smoke pass; (4) mutation: put `/home/oai/skills` back into dependencies.md; the
  parametrized assert fails.

### PT5 Cut DOCX authoring text and per-format substitution copies (P1-09, P1-10; was E12)
Wave 4 | Mode code | After PT1, PT3, PT4 | Touches: references/docx.md, references/html.md,
references/pdf.md, references/control-flow.md, the R21 table file
- docx.md: cut "PDF deliverable via DOCX" and the authoring half of "Reading and verification" (the loop
  `standalone` cannot run); keep the structural-limits sentence and lines 1-24. Cut html.md "Do not
  manufacture a document", docx.md "DOCX is not a reading workaround", pdf.md "Source integrity". Dedupe
  in-list repeats (pdf.md items 2/5, docx.md items 4/6, renumbered after PT4). Keep control-flow.md
  section 7 and add the one allowance the cut sections carried: a conversion is the source only when the
  user requested it or it is disclosed as the bound source. Compare `grep -c media` before and after.
- Phase: section 7 loads at activation in every run. The cut copies loaded at the format route, after
  planning (root table: plan, then acquire/extract), so never earlier than the owner. deliverable.md loads
  at planning, which a non-substantial run skips; that is why section 7, not deliverable.md, owns the
  source side. DoD `fidelity.preserved` stays (the verifier enforces it). Add an R21 row: do not substitute
  a derivative for the source -> references/control-flow.md.
- Pins: F5 tokens (`heading1`/`heading6`, `scripts/extract_docx.py`, section 3 phrases) stay; no test
  pins the cut headings.
- Accept: (1) re-check: `grep -rn "derivative\|manufacture\|Source integrity\|Prohibited" tests/*.py` is empty
  and `grep -n "^## " references/docx.md references/html.md references/pdf.md` shows the named headings;
  (2) after, the headings are gone, deliverable.md keeps "Prohibited substitutions", control-flow.md keeps
  section 7; (3) pytest on all prose test files passes; (4) installer-doctor, distribution, pack-smoke pass.

### PT6 Stop installing README.md into the skill directory (K3; was E13a, R20)
Wave 1 | Mode serial (MANIFEST.json, AGENTS.md: owner reads before merge) | After - | Touches: MANIFEST.json,
AGENTS.md, tests/installer/test_upgrade_ownership.py, tests/node/core.test.js, tests/installer/test_manifest.py
- Remove `README.md` from `payload` (F3). Edit AGENTS.md line 22 (payload list) only; E's AGENTS hunk is
  separate. Both installers read the same manifest.
- Tests: parametrize the prune test (Python `test_upgrade_removes_files_owned_by_old_manifest_but_not_new_manifest`,
  Node "upgrade removes files owned only by the old manifest") over `legacy-managed.txt` and `README.md`.
  The README case installs with README in the old payload, upgrades with the real manifest, and asserts
  README.md is gone and the installation verifies; re-adding README to the real manifest fails it.
  core.test.js "failure after replacement..." tampers README.md (line 186): switch to a payload file that
  PT1-PT5 keep (references/anti-patterns.md). Fix any file set in D's test_manifest.py link test naming README.
- Accept: (1) re-check: `grep -rn README SKILL.md skills references scripts` is empty and no payload file
  links README.md (if D added a reader, DROPPED K3); (2) `python installer/install.py doctor --target
  generic-agents --json` passes and an install into a temp HOME has no README.md; (3) pytest, `npm test`,
  pack-smoke pass and `package.json` `files` still lists README.md; (4) mutation: re-add README.md to the
  payload; both prune cases fail.

### PT7 Leave CONTRIBUTING.md out of the release ZIP (K4; was E13b)
Wave 1 | Mode code | After - | Touches: installer/distribution.py, tests/installer/test_distribution_archive.py
- Remove `CONTRIBUTING.md` from `RELEASE_FILES`. README links it by absolute GitHub URL (checked), so
  nothing in the ZIP breaks. Extend the archive name-set test (E3 builds it in `tmp_path`): README.md is
  listed, CONTRIBUTING.md is not.
- Accept: (1) re-check: `grep -n "README\|CONTRIBUTING" installer/distribution.py package.json`; (2) the
  distribution gate's ZIP lists README.md and not CONTRIBUTING.md; (3) pytest on the archive test, ruff,
  pack-smoke pass; (4) mutation: put it back; the name-set test fails.

### PT8 Drop the README wording pins (T3-14)
Wave 4 | Mode code | After PT3, PT4, PT6 | Touches: tests/test_anti_skimming_docs.py
- Cut the README human-explainer pins ("what is a chunk", "ooxml", "xlsx", "future", "receipt-owned",
  "install root", "schema v2", "atom_id"); no gate consumes them. Keep SKILL.md and references/ pins. E1's
  Superpowers survivor test keeps README (it still ships in npm and the ZIP) and installer/USAGE.md if E1
  listed it: verify, do not edit.
- Accept: (1) re-check: `grep -n README tests/test_anti_skimming_docs.py`; (2) pytest on that file and
  test_hard_standalone_release_contract.py passes; (3) mutation: put "Superpowers" into README.md; the
  survivor test still fails.

### PT9 Changelog
Wave 5 | Mode serial | After PT1-PT8 | Touches: CHANGELOG.md
- Under `## Unreleased` (open it if absent; R13), user-visible lines only: README.md is no longer
  installed into the skill directory and an upgrade removes it; CONTRIBUTING.md is not in the ZIP; the
  failure ladder, PDF provenance and run-root tree each have one owner; oai-native guidance lives in
  `references/oai-native.md`, read only under that profile; run-workspace.md is routed.
- Accept: `python tools/release_check.py` exits 0 (it looks up the VERSION heading; an Unreleased section
  above it is tolerated).

## 5. Dispatch

| Wave | Tasks | Agents |
|---|---|---|
| 1 | PT1, PT2, PT6, PT7 | 4 |
| 2 | PT3 | 1 |
| 3 | PT4 | 1 |
| 4 | PT5, PT8 | 2 |
| 5 | PT9 | 1 |

If the dispatch resolves the R21 table to a file a same-wave task touches (PT1 or PT8's test files), the
later task moves one wave. Peak 4. Landing order: PT1, PT2, PT6, PT7, PT3, PT4, PT5, PT8, PT9; a gate run after each landing. PT6 is on
the owner-reads list (R17, R20). Subjects: PT1 `docs: keep the failure ladder in failure-recovery` | PT2
`docs: move PDF provenance rules into the PDF reference` | PT3 `docs: route run-workspace and keep one
run-root tree` | PT4 `docs: move oai-native guidance into its own reference` | PT5 `docs: cut DOCX authoring
text and per-format substitution copies` | PT6 `fix(installer): stop installing README.md into the skill
directory` | PT7 `fix(installer): leave CONTRIBUTING.md out of the release ZIP` | PT8 `test: drop README
wording pins` | PT9 `docs: record the prose trim and payload change in the changelog`.

## 6. Gates (AGENTS.md block, scoped)

pytest: every task. ruff: PT1-PT8 (each edits a .py). `npm test`: PT6, PT7 (installer/ changed). pack-smoke, installer-doctor,
distribution: PT1-PT7 (payload paths, MANIFEST.json or RELEASE_FILES). release-labels: PT9. Before the
push, the full list.

## 7. Risks and questions for the controller

1. Consumed, not edited: D's T3 (evidence.md run.json block), T5 (LICENSE, the payload link test), T6
   (README), T14 and M (media text in format references and evidence.md), T15 (dependencies.md). P trims
   around them; PT3-PT5 compare media counts before and after.
2. R19 replaces E's fold design with one new shipped reference. Existing `references` entries cover it, so
   no ship list changes; the owner should still see a new shipped file in the PR.
3. PT5 keeps control-flow section 7 where the old E12 cut it: planning (the loader of deliverable.md) can be
   skipped for non-substantial runs, section 7 loads at activation. It costs about 10 lines of cut.
4. K3 removes a file from users' skill directories on upgrade (owner read, R20). D's T5 added LICENSE to the
   payload so README's `(LICENSE)` link resolved; with README out, that reason is gone. P leaves LICENSE
   in; the controller decides whether it still ships.
5. PT8 removes pins D's T6 told D to keep (they hold while D edits README). Drop PT8 if the owner wants
   README prose pinned.
6. Test names and the R21 table path come from E's head, not this plan; each pin change is written as "the
   row moves from file A to file B" and re-checked at base.

## Implementation notes (controller, from review-P; binding)

- R28: PT8 keeps every README pin that plan D's T6 names ("what is a chunk", "ooxml",
  "xlsx", "future", "receipt-owned", "install root", "schema v2", "atom_id") and removes
  only pins D does not name. Risks 5 is void.
- The R21 instruction table lives in tests/test_anti_skimming_docs.py (plan E); PT5 and
  PT8 both touch it, so PT8 runs one wave after PT5. PT1 adds its R21 row.
- PT6 Touches add tests/test_portable_payload.py. PT7 changes RELEASE_FILES in
  installer/distribution.py, a ship list: owner read before merge, like PT6.
- PT1 acceptance (2) is rewritten to what the code does (see review-P); the other Minors
  apply as written.

## Drift notes (controller, R58 from review-P-drift.md; binding)

These notes override the task text above where they differ. Numbers are main 14714cf's.

- P1 Base is main 14714cf (A, B, C, D, M, the follow-ups, 0.2.4 and E are merged); the plan is the first commit of a new branch from origin/main. "P branches from E's head" and "Rows were read at d75018c (C:/ssw/t1)" are replaced by this. Line numbers in the plan are d75018c's; the numbers in these notes are 14714cf's and win.
- P2 PT8 is `DROPPED T3-14`: the README pins that remain (tests/test_anti_skimming_docs.py:61-72 and :75-78) are all named by plan D's T6 (D plan lines 110-113); R28 leaves nothing to remove. Remove PT8 from Section 1 (T3-14), the wave table, Subjects, Gates ("PT1-PT7") and Risks 5; PT9 is After PT1-PT7. E1's survivor (tests/test_hard_standalone_release_contract.py:8-25) already scans README.md and installer/USAGE.md: nothing to verify or edit.
- P3 R21 table (resolves F4 and the open "R21 table file"): `INSTRUCTIONS` at tests/test_anti_skimming_docs.py:26-51, rows `(instruction, rel, module)`, test `test_required_instruction_is_stated_where_its_phase_loads_it` (:54). A row passes when `instruction` is in `rel` and, if `module` is not None, `](../../{rel})` is in `skills/{module}/SKILL.md`. P edits rows only, adds no second table, and adds module constants (`DEBUGGING = "debugging-document-workflows"`, `RECOVERING = "recovering-document-workflows"`) when a row needs them. Replace every `tests/test_phase_gated_loading.py` presumption in F4, PT2, PT3 and PT4 with this file. PT3 and PT4 add their routes as rows only; they do not extend `test_exhaustive_module_owns_all_four_format_routes` (tests/test_phase_gated_loading.py:45) and drop that file from Touches.
- P4 Waves: the table file is touched by PT1 (its R21 row), PT2, PT3, PT4 and PT5, so they are serial. Wave 1: PT1, PT6, PT7. Wave 2: PT2. Wave 3: PT3. Wave 4: PT4. Wave 5: PT5. Wave 6: PT9. Landing order: PT1, PT6, PT7, PT2, PT3, PT4, PT5, PT9. Peak 3. PT1 Touches add tests/test_anti_skimming_docs.py. PT4 Touches list the file without "only if a pin moves". PT5 After PT1, PT3, PT4 stays.
- P5 PT1: the retargeted merged test in tests/test_hard_standalone_docs.py replaces :19-24 and :26-29 (its negatives today are `systematic-debugging` and `brainstorming` on control-flow.md only); the new parametrized negative covers SKILL.md, skills/*/SKILL.md and references/*.md with the needles in the plan. Its R21 row is the failure-recovery.md ladder (for example the `**do not attempt a fourth fix**` line) with module DEBUGGING. Re-check (1) holds as written (3 lines: html.md:76, source-acquisition.md:55, :62).
- P6 PT2: Accept (1) becomes `grep -n '"extraction"' references/pdf.md` is empty today. D's run.json block carries no `extraction` key, so move the full object, not a link. Carry the rule from scripts/verify_run.py:416 and :1224-1262 (the `run.json` object must equal the manifest's; known backend; `format` pdf; `capabilities` equal the text adapter's; QA naming OCR is rejected). The section to cut is runtime-profiles.md:26-47 (keep :49). Retarget the existing row at tests/test_anti_skimming_docs.py:49 (`Text backends cannot justify an `ocr-verified` QA claim`) from RUNTIME to `references/pdf.md`, module EXHAUSTIVE, and add the "copy the extraction object" row. Mutation: delete the object from pdf.md; both rows fail.
- P7 PT3: replace "the only file with the `--run-root` commands" with "the only file loaded before extraction that states the run-root interface for all four formats" (lengthy-markdown.md:32 and evidence.md:151, :245-247 also carry commands and stay). Cut only the trees: evidence.md:9-30 (unlabelled `text` fence) and deliverable.md:34-50 (keep skill-preflight.md and format-qa.md named in prose; tests/test_contradictions.py:44-45 pin them). The `sh first-run` and `json run.json` fences in evidence.md stay (tests/test_documented_run_shape.py drives them). `test_run_workspace_namespaces_every_emitted_artifact` (tests/test_anti_skimming_docs.py:87-94) has no tree check: leave it unchanged. The route goes in the exhaustive module's extraction block before the format routes, as a markdown link `[run-workspace](../../references/run-workspace.md)`, with the R21 row. Accept (1) holds (deliverable.md:5, evidence.md:7).
- P8 PT4: Accept (1) becomes `grep -c oai-native references/*.md` = dependencies 4, docx 2, pdf 4, prerequisites 2, runtime-profiles 4 (prerequisites.md:26 and :74 stay untouched). F2 ranges: roots list dependencies.md:5-14, the HTML note :16 moves into oai-native.md with the roots list, full-read rule :18-29, the oai-native Authority sentence is the first sentence of :75 (keep the standalone sentence in dependencies.md). Keep dependencies.md:56 (`Do not require an external document skill merely to perform basic exhaustive text extraction`, row at tests/test_anti_skimming_docs.py:50) and runtime-profiles.md:20 (row :48). Pin: replace the assert at tests/installer/test_runtime_profiles.py:22 as the plan says; the "visual"/"ocr" and dependencies word-bag pins named in the plan no longer exist, so that clause is void. The route line must read "whenever the profile is or becomes oai-native (including after the extractor reports a PDF with no text layer), read oai-native.md before reading any /home/oai/skills tree", and pdf.md keeps one pointer so its OCR text agrees with scripts/chunk_common.py:284-286. The pointers in runtime-profiles.md, docx.md and pdf.md are pointers, not loads: F2's "Nothing else routes it" means no other file loads it.
- P9 PT5: docx.md "lines 1-24" is lines 1-25. Headings to cut: docx.md:27, :49, :61; html.md:59; pdf.md:54. Re-check (1) holds (`git grep -n -i "derivative|manufacture|Source integrity|Prohibited" -- tests` is empty). R21 row: "do not substitute a derivative for the source" in references/control-flow.md, module EXHAUSTIVE.
- P10 PT6: Touches = MANIFEST.json, AGENTS.md, tests/installer/test_upgrade_ownership.py, tests/node/core.test.js, tests/npm/npm-pack-smoke.test.js. Remove tests/installer/test_manifest.py (nothing names README) and the tests/test_portable_payload.py note (E1 deleted the file; no README payload pin remains). Edit AGENTS.md:22 only: drop `README.md` and name `LICENSE` so the list equals MANIFEST.json `payload`; E's AGENTS hunks are merged. Add `"README.md"` to the extras list at tests/npm/npm-pack-smoke.test.js:104 (README stays in package.json `files` and in the tarball). The Node tamper is core.test.js:198 (switch to references/anti-patterns.md). For the README case of the parametrized prune tests (Python :42-60, Node :157-179) the second install uses the original manifest bytes saved before the old payload entry was added; do not derive it with `remove`/`filter`. Mutation (4): re-add README.md to MANIFEST.json; the README case fails in both runtimes and `npm run test:pack-smoke` still passes.
- P11 PT7: Mode is owner-read like PT6. Extend `test_distribution_archive_has_one_canonical_skill_root` (tests/installer/test_distribution_archive.py:47-57): `deeper-reading/README.md` in `names`, `deeper-reading/CONTRIBUTING.md` not. Re-check (1): distribution.py:17-19 and package.json:13.
- P12 PR body (R28, R17, AGENTS.md:62-63): name the three owner-read items: `references/oai-native.md` (new shipped file), README.md leaving `MANIFEST.json` `payload` (PT6), CONTRIBUTING.md leaving `RELEASE_FILES` (PT7).
- P13 PT9: `## Unreleased` does not exist at 14714cf; open it above `## 0.2.4` (CHANGELOG.md:3). tools/release_check.py exits 0 with it (verified read-only on a scratch copy, with and without `--tag v0.2.4`). Keep only: README.md is no longer installed into the skill directory and an upgrade removes it; CONTRIBUTING.md is not in the release ZIP; oai-native guidance lives in `references/oai-native.md` and is read only under that profile; `references/run-workspace.md` is now read before extraction. Drop the failure-ladder, PDF-provenance and run-root-tree line (internal dedupe, not a product change). Add `### Compatibility`: a user who edited or deleted the installed README.md gets "modified managed files" on upgrade until the file is restored or the skill is reinstalled.
- P14 Mutation procedure (replaces the `git checkout -- <file>` clause in the header; same wording as plan E's D4): save the file with `cp <file> WORKSPACE/scratch-<TASK>/<name>.orig`; apply the edit with a small script (never `sed -i`; mutate.py does not run pytest); run the named test and quote the failure; `cp` the saved bytes back; quote the test passing; confirm `git diff --stat -- <file>` equals its value before the mutation. Never `git checkout` or `git restore` a work-tree file. A mutation is never part of the patch.
