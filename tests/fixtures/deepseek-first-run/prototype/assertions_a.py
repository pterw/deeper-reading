"""Atomic extractive assertions, chunks 1-24.

Every string below is copied verbatim from its canonical chunk's emitted
content. build_evidence.py locates each string inside that chunk's bytes and
fails loudly when one does not match, so no assertion can be authored from
memory without being caught.

Assertions deliberately avoid double quotes and backslashes: the source spells
some table-cell pipes as escaped pipes, and a quote inside a Python literal
risks an encoding mistake that would silently change the assertion.
"""

ASSERTIONS_A = {
    1: [
        "# Implementation Plan",
        "**Scope of this document:** make the repository, its plans and its design",
        "Derived 2026-09-11 from branch `test` at `3f59380`.",
        "**Source read order used:** `AGENTS.md` (full), `docs/design/designsystemaudit.md`",
        "claim names.",
    ],
    2: [
        "## Progress -- where this plan stands, and where to pick it up",
        "**Owner of this status: this section. Do not restate it in [Implementation",
        "**State: Phase 1 complete and committed. Phases 2-5 not started. Three work",
        "items are uncommitted.** Nothing is pushed.",
    ],
    3: [
        "| Phase | State | Evidence |",
        "| 0 Baseline | **Done** | guard exit 0; `pytest -q` 990 at open, 1020 now; docsync exit 0 |",
        "| 1 WP-7 refinement | **Done, committed** | `57d1474`; frontend gate 26 checks in 47 runs, chromium + firefox |",
        "| 2 Document reconciliation | **Not started** | the two live conflicts are listed below |",
        "| 5 WP-8 close-out | **Not started** | needs the mandated frontend/a11y audit |",
    ],
    4: [
        "### Commits landed during this plan",
    ],
    5: [
        "| Commit | Subject |",
        "| `72615ed` | `feat(unmatched): Align report with Results and cap album fetch` -- the prior session's work, committed as a checkpoint |",
        "| `c2f14fa` | `chore(agents): Record the issue tracker and domain docs for agent skills` |",
        "| `57d1474` | `fix(ui): Refine the unmatched report disclosure` -- this plan's Phase 1 |",
    ],
    6: [
        "### Uncommitted work at handoff, in the order it should be committed",
        "1. **Staged, all four gates observed green on it:** the F-B21-51 slice-1 gate",
        "archive. 480 insertions, 140 deletions.",
        "2. **Unstaged:** the architecture-diagram rebuild -- `docs/ARCHITECTURE.md` and",
        "3. **Unstaged:** this plan's move into `docs/superpowers/plans/` and the",
    ],
    7: [
        "### Where to pick up",
        "1. Commit the staged set. Its PLAYBOOK entry and every gate result are recorded.",
        "3. Commit this plan's move. Decide the fate of",
        "4. Start **Phase 2** with the conflict that actively misleads: the approved spec",
    ],
    8: [
        "### What Phase 1 actually did, and how it diverged from the plan",
        "1. **The layout was not rebuilt.** The plan's Phase 1 step 5 said to restructure",
        "3. **The step size was chosen, not specified.** The owner allowed",
        "It entered with `72615ed`, not with Phase 1.",
    ],
    9: [
        "### Open owner decisions carried into the handoff",
        "2. The unmatched expander step (20 vs 25) -- 25 is live.",
        "4. Whether the theme gains a third",
        "5. The F-B21-20 staging-order contract.",
    ],
    10: [
        "## [Overview]",
        "Four facts shape the whole plan:",
        "**One audit instruction is a trap, and one is mechanically wrong.**",
        "Ordering chosen by the owner: **WP-7 refinement first, then document",
        "**The audit's repo-side list is already WP-8's shape.** The audit says so",
    ],
    11: [
        "| Audit states | Measured 2026-09-11 | Consequence |",
        "| `--index-scale` has 102 consumers | **111** `var(--index-scale` occurrences in `static/css/index.css` alone |",
        "| Incidental defect 3, `--shell-accent-ink`,",
        "The value is not live. Resolve it by deletion with `global.css`, not by re-pointing it.",
    ],
    12: [
        "## [Types]",
        "No new or changed Python type definitions. Task 1 of the WP-7 extension already",
        "**Already landed, treated as fixed interfaces (do not change):**",
        "`partition_albums_by_threshold(albums, min_plays, min_tracks) -> tuple[dict, dict]`",
        "**Retired names that must not survive in a prescriptive document:**",
        "- `--text-body` and `--text-muted` **as colours**: `--text-body: 1rem` is",
    ],
    13: [
        "## [Files]",
    ],
    14: [
        "### Phase 1 -- finish the WP-7 extension (uncommitted work in this worktree)",
    ],
    15: [
        "| File | Change |",
        "| `templates/unmatched.html` | Keep the side-by-side `.unmatched-groups` grid",
        "Extract the expander's collapse branch (lines 91-106) into one named function",
        "| `static/css/tailwind.css` | Regenerated output, only if a utility class changes. Produced by `scripts/dev/tailwind_build.py`; never hand-edited. |",
        "| `tests/test_routes.py` | Assert the rendered group order, the `below_threshold` section's title and copy, and the threshold metric text for an item failing both minimums. |",
        "| `.claude/SESSION_CONTEXT.md` | Section 1 batch-status row and test count. |",
    ],
    16: [
        "### Phase 2 -- document reconciliation to the audit",
    ],
    17: [
        "| `DESIGN.md` | Correct the four claims the audit names (Modal Shadow row,",
        "| `docs/design/RECONCILIATION.md` | Correct the stale geometry row in section 7 (D-15: the gap is 2px, not 3px)",
        "| `docs/AGENT_DOC_MAP.md` | Section 3's Design row names only `docs/design/README.md`.",
        "| `docs/design/designsystemaudit.md` | **Do not edit.** It is a dated, self-correcting record whose later sections supersede its earlier ones.",
    ],
    18: [
        "### Phase 3 -- the audit's incidental code defects",
    ],
    19: [
        "| `static/css/shell.css` | Lines 575 and 610: `font-weight: 500` -> `400`",
        "| `static/css/heatmap.css` | Line 189: remove `box-shadow: var(--ss-shadow-card, none);`",
        "| `static/js/page_motion.js` | Line 10: remove `document.body.classList.add('is-ready')`",
        "| `tests/test_template_shell.py` | Pin the token table as it now stands",
    ],
    20: [
        "### Phase 4 -- WP-8 core: retire the legacy layer",
    ],
    21: [
        "| `static/js/heatmap.js` | `initDarkModeObserver()` (lines 1375-1385): observe `document.documentElement`",
        "| `static/css/global.css` | **Delete** (486 lines; no page loads it). |",
        "Keep the `0 0 453 74` viewBox and the bar feet at 63.50",
        "| `FINDINGS.md` | Close F-B21-23 (the asset contract now holds)",
    ],
    22: [
        "### Phase 5 -- WP-8 sweep and close-out",
    ],
    23: [
        "| `BATCH21_DEFINITION.md` | WP-8 gains the audit-derived item list and the `.dark-mode` observer trap in writing",
        "| `AGENT_NOTES.md` | Repoint the linting gap entry at that disposition, so the gap closes by a decision rather than by silence. |",
        "Batch 21 does not close without it.",
    ],
    24: [
        "### Root artifact",
    ],
}
