"""Atomic extractive assertions, chunks 49-70 (see assertions_a.py for the rule)."""

ASSERTIONS_C = {
    49: [
        "### Colour",
        "No new hexes; every value is a shipped token.",
    ],
    50: [
        "| Role | Token |",
        "| Section surface | `--results-surface` (the Results midpoint) |",
        "| The single primary action | `--color-primary` fill |",
    ],
    51: [
        "### Type",
        "Roles only, from the shipped system.",
    ],
    52: [
        "| Element | Role |",
        "| Page `h1` | `--font-serif` (Instrument Serif) |",
        "| Section album count | `--font-figure` (Gotham) |",
    ],
    53: [
        "### Layout",
        "Reason panels sit **side by side**, sorted by reason, in the fixed order",
        "The owner ruled this layout explicitly",
        "collapses to a single column.",
    ],
    54: [
        "Desktop, 90rem measure -- panels share a top offset, keep natural height",
        "Mobile (below 1024px): one column, full width, no horizontal page scroll.",
    ],
    55: [
        "Alignment: left for prose and identity; right for every numeric column, so the",
        "One consequence of side-by-side that a stacked layout would not have: each",
    ],
    56: [
        "### Principles",
        "1. **The structure is the information.** Albums are grouped by *why* they were",
        "4. **Disabled is not hidden.** The fold hides rows but never removes them; the",
    ],
    57: [
        "### Self-critique -- generic defaults rejected",
    ],
    58: [
        "| Generic default | Replacement, and why |",
        "| Panels stretched to equal height | Panels keep their natural height (`items-start`). Stretching a short panel leaves dead space that reads as a rendering fault. |",
        "| `truncate` on the reason detail | Let it wrap. The panel is narrower side-by-side, and truncation would hide the text that explains the exclusion. |",
    ],
    59: [
        "### What this annex changes in Phase 1",
        "The layout is **not** one of them: side-by-side panels stay. Phase 1 changes",
    ],
    60: [
        "## [Implementation Order]",
        "**Step status is not tracked here. The Progress section above owns it** -- one",
    ],
    61: [
        "### Phase 0 -- baseline (no edits)",
        "2. Confirm the pre-work baseline: `pytest -q` (expect 990 passed),",
    ],
    62: [
        "### Phase 1 -- finish the WP-7 extension",
        "6. Extract the collapse path in `static/js/unmatched.js` into one function,",
        "    Commit: `fix(ui): Align unmatched report with Results`",
    ],
    63: [
        "### Phase 2 -- document reconciliation",
        "    Commit: `docs(design): Reconcile the design record with the shipped system`",
    ],
    64: [
        "### Phase 3 -- the audit's incidental code defects",
        "    Commit: `fix(ui): Remove dead and non-resolving style declarations`",
    ],
    65: [
        "### Phase 4 -- WP-8 core: retire the legacy layer",
        "    Commit: `refactor(ui): Retire the legacy Bootstrap layer and the dual theme write`",
    ],
    66: [
        "### Phase 5 -- sweep and close-out",
        "27. Run the mandated frontend and accessibility audit over the migrated",
        "    Commit: `chore(close-out): Batch 21 complete; archive definition and purge log`",
    ],
    67: [
        "## Audit disposition -- what this plan does with each audit item",
        "Not every audit item is actionable here, and saying so is part of the work.",
    ],
    68: [
        "| Audit item | Disposition |",
        "| D-1, D-2 (token families, `--text-body` collision) | Recorded in `DESIGN.md` and declared in `.docsync.toml`. The external project rewrite is out of repository scope. |",
        "| The seven unread root tooling files, and `app.py` / `scrobblescope/` | **Out of scope and explicitly not claimed.**",
    ],
    69: [
        "## Assumptions, limitations, and open owner decisions",
        "**Assumptions.**",
        "**Limitations.**",
        "3. **The unmatched expander step: 20 or 25?** The owner said",
    ],
    70: [
        "## Verification of this plan document",
        "(`templates/unmatched.html:174`) and the back-to-top handler",
        "- No production file, test, or governed document was edited while producing",
        "this plan. The only file created is `implementation_plan.md`.",
    ],
}
