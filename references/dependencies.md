# Document Dependency Resolution

Detailed document behavior belongs to the resolved document profile, not to copied instructions in this custom skill. Resolve `oai-native` or `standalone` through `references/runtime-profiles.md` before format execution.

## oai-native: current local skill roots to discover

At task time, inspect `/home/oai/skills` rather than assuming this list is complete.

Known document roots in this environment include:

- `/home/oai/skills/pdfs`
- `/home/oai/skills/docx`
- `/home/oai/skills/slides`
- `/home/oai/skills/spreadsheets`

HTML currently has no dedicated OAI skill root here, so HTML-specific guidance lives in `references/html.md`.

## oai-native mandatory full-read rule

When an OAI skill root is selected for the task:

1. Read its root `SKILL.md`.
2. Recursively inventory every `*.md` file under that selected skill root.
3. Read **every Markdown file in that selected tree in full before execution**.
4. Do not skip examples, troubleshooting, niche task guides, OOXML notes, or other Markdown because they appear unrelated at first glance.
5. If tool output truncates a file, split that file into bounded line ranges and continue until every line has been read.
6. Cached summaries, remembered instructions, search snippets, and headings-only reads do not count.

This rule is intentionally stricter than normal progressive disclosure.

## Shared CLI/tool prerequisites

Before first use of a helper:

1. identify the governing task guide;
2. read it in full;
3. run the helper's current top-level `--help`;
4. if it has subcommands, run the selected subcommand's `--help`;
5. only then execute the real operation.

Never infer syntax from earlier conversations or from similarly named helpers.

## standalone basic extraction

Basic portable text extraction is bundled with this skill in `scripts/extract_html.py`, `scripts/extract_markdown.py`, `scripts/extract_docx.py`, and `scripts/extract_pdf.py`. Do not require an external document skill merely to perform basic exhaustive text extraction and chunk-manifest generation.

External document skills are **advanced capability providers** for operations such as visual rendering, OCR, forms, conversion, or other format-specific QA not supplied by the bundled core. Resolve them only when the requested task actually requires those capabilities.

## Dependency installation

Do not install a package merely because it exists in a skill pack.

Before `pip install`, `npm install`, or runtime surgery:

1. prove the selected operation requires the dependency;
2. read the documented fallback path;
3. inspect the existing environment;
4. prefer an already-supported fallback that preserves correctness.

A missing optional dependency is not a reason to rebuild an unrelated runtime.

## Authority

Under `oai-native`, if this custom skill conflicts with the current OAI format skill on format-specific visual/layout mechanics, follow the live OAI skill unless the user's explicit instruction overrides it. Under `standalone`, the bundled extractors govern basic text chunk generation; any approved external dependency governs only the advanced capabilities it explicitly declares.

This custom skill governs exhaustive traversal, anti-skimming coverage, failure boundaries, and process order. Format-specific providers govern visual/layout/OCR mechanics within their declared capability profiles.

## standalone external capability resolution

On external Agent Skills hosts, do not use `/home/oai/skills` paths. Start with the bundled extraction core. If the task requires an advanced capability the bundled core does not provide, resolve the optional external provider declared by the installer/runtime profile, record source + revision/version + content hash, inspect its current guidance, and fail closed before execution when that required capability is absent.
