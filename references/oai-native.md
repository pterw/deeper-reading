# oai-native Guidance

Read this file only when the runtime profile is or becomes `oai-native` (see [runtime-profiles](runtime-profiles.md)), before reading any `/home/oai/skills` tree. Under `standalone` nothing here applies.

The evidence-contract invariant is stated in [runtime-profiles](runtime-profiles.md#oai-native); the format references [pdf](pdf.md) and [docx](docx.md) still govern the traversal.

## Current local skill roots to discover

At task time, inspect `/home/oai/skills` rather than assuming this list is complete.

Known document roots in this environment include:

- `/home/oai/skills/pdfs`
- `/home/oai/skills/docx`
- `/home/oai/skills/slides`
- `/home/oai/skills/spreadsheets`

HTML currently has no dedicated OAI skill root here, so HTML-specific guidance lives in `references/html.md`.

## Mandatory full-read rule

When an OAI skill root is selected for the task:

1. Read its root `SKILL.md`.
2. Recursively inventory every `*.md` file under that selected skill root.
3. Read **every Markdown file in that selected tree in full before execution**.
4. Do not skip examples, troubleshooting, niche task guides, OOXML notes, or other Markdown because they appear unrelated at first glance.
5. If tool output truncates a file, split that file into bounded line ranges and continue until every line has been read.
6. Cached summaries, remembered instructions, search snippets, and headings-only reads do not count.

This rule is intentionally stricter than normal progressive disclosure.

## Authority

If this custom skill conflicts with the current OAI format skill on format-specific visual/layout mechanics, follow the live OAI skill unless the user's explicit instruction overrides it.

## DOCX

Use `/home/oai/skills/docx` for visual/layout mechanics, and read its entire Markdown tree in full before DOCX execution.

## PDF

Read the live PDF guidance (`/home/oai/skills/pdfs`) before using native helpers. A PDF with no text layer needs OCR, which the bundled extractor does not provide.

Keep the native render-first visual loop:

```text
render bounded source range
  -> inspect every rendered page
  -> structural inspection
  -> compare text extraction with the source render
  -> record format/visual QA evidence
```

The optional native branch supplements the canonical chunk ledger; it never substitutes for it.

### Conditional native branches

Use the live PDF guidance to decide when to invoke OCR, preflight/normalization, renderer parity, forms, coordinate extraction, conversion, or batch utilities. Do not invoke expensive or lossy branches by default.
