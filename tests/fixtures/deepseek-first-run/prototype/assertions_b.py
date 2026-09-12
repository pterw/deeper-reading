"""Atomic extractive assertions, chunks 25-48 (see assertions_a.py for the rule)."""

ASSERTIONS_B = {
    25: [
        "| File | Note |",
        "| `implementation_plan.md` (this file) | A working plan, not a governed document.",
        "`docs/superpowers/plans/gemini_implementation_plan_unverified.md` is already untracked in this worktree and is a prior, unverified attempt at the WP-7 extension;",
    ],
    26: [
        "## [Functions]",
    ],
    27: [
        "### Modified -- Phase 1",
    ],
    28: [
        "| Function | File | Change |",
        "| group expander click handler (anonymous, lines 89-125) | `static/js/unmatched.js` |",
        "| group back-to-top click handler (lines 127-131) | `static/js/unmatched.js` |",
        "| `syncResultsScale()` | `static/js/unmatched.js` | Unchanged; it already applies the Results scale variables the panel layout depends on.",
    ],
    29: [
        "### Modified -- Phase 3",
    ],
    30: [
        "| `revealPage()` | `static/js/page_motion.js` | Drop the `is-ready` class write; keep the `is-leaving` removal, which is the only class any stylesheet reads. |",
        "| `followLink()` | `static/js/page_motion.js` | Read the exit duration from its single owner instead of the hardcoded `140`. |",
        "| `updateZeroFills()`, `zeroFill()` | `static/js/heatmap.js` | Unchanged signatures.",
        "| `applyTheme(isDark)` | `static/js/theme.js` | **Phase 4**: stop writing `.dark-mode` on `<body>`; keep the `data-theme` attribute write. |",
    ],
    31: [
        "### New -- server side",
        "None. Task 1 of the WP-7 extension already added",
        "`fetch_top_albums_async`; this plan adds no production Python.",
    ],
    32: [
        "### New -- gate helpers",
    ],
    33: [
        "| unmatched group-row helper (working name) | `scripts/dev/frontend_gate.py` | Count visible rows inside a `.unmatched-group`",
        "| font-weight sweep helper (working name) | `scripts/dev/frontend_gate.py` | Assert no element on a migrated page computes to weight 500 or 600, in both themes.",
        "| heatmap theme-fill helper (working name) | `scripts/dev/frontend_gate.py` | Read a zero-count cell's `fill` before and after a theme toggle.",
    ],
    34: [
        "## [Classes]",
        "No Python class is added, removed, renamed or moved. `scrobblescope/` is",
        "**CSS class changes.**",
    ],
    35: [
        "| Class | File | Change |",
        "| `.unmatched-groups` | `templates/unmatched.html` | Unchanged. The responsive grid branch and `items-start` are the owner-ruled layout and are preserved. |",
        "| `.site-header__theme-choice--light`, `.site-header__theme-choice--dark` | `static/css/shell.css` | Lose `font-weight: 500` in their active states; gain `var(--ss-shadow-chip)` as the active-state shadow. |",
        "| `.hm-preview` | `static/css/heatmap.css` | Loses the dead `var(--ss-shadow-card, none)` declaration; keeps its existing border and surface. |",
    ],
    36: [
        "**Container-class contract this change depends on.** An SVG presentation",
        "is exactly how F-B21-21 shipped.",
    ],
    37: [
        "## [Dependencies]",
        "**No dependency changes.** This plan adds none, removes none, and changes no",
        "- `playwright==1.62.0` is already pinned and already drives",
    ],
    38: [
        "## [Testing]",
    ],
    39: [
        "### Test-quality constraints",
        "1. **Prove each guard fails when the fix is reverted, and say so.** State the",
        "3. **Cover every state a reader can reach, not the one that loads.** The",
    ],
    40: [
        "### New and modified Python tests",
    ],
    41: [
        "| File | Test work |",
        "| `tests/test_unmatched.py` | Already covers the partition contract from Task 1. No change expected; re-run to prove the Phase 1 edits did not disturb it. |",
        "| `tests/test_design_snapshot.py` | No change. `designsystemaudit.md` is already in `REPOSITORY_OWNED_PATHS`",
        "| `tests/scripts/dev/` (existing gate-helper modules) | Add unit coverage for each new gate helper. A helper that cannot fail is not a guard. |",
    ],
    42: [
        "### Browser gate coverage (`scripts/dev/frontend_gate.py`, Chromium + Firefox)",
    ],
    43: [
        "| Zero-count heatmap cell `fill` changes on theme toggle to the new theme's empty colour | 4 | The `.dark-mode` retirement trap. Nothing watches this today. |",
        "| The Bootstrap grep returns nothing | 5 | WP-8's deterministic criterion 1. |",
    ],
    44: [
        "### Validation sequence per phase",
        "Run in order and do not advance on a failure:",
    ],
    45: [
        "python scripts/dev/tailwind_build.py",
        "node --check static/js/unmatched.js",
        "python scripts/doc_state_sync.py --check",
    ],
    46: [
        "Then confirm `git diff --exit-code -- static/css/tailwind.css` is clean. Per",
        "**Documentation validation.** `doc_state_sync.py --check` must exit 0 with no",
        "is active and are not failures.",
    ],
    47: [
        "## Phase 1 design annex -- the unmatched report (frontend-design pass)",
        "It introduces no new colour, no new typeface and",
    ],
    48: [
        "### Brief",
        "An archival field-notebook report.",
    ],
}
