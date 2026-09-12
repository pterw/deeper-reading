# DOCX Workflow

## Required document profile

Resolve the document profile first. Under `oai-native`, use `/home/oai/skills/docx` for visual/layout mechanics. Under `standalone`, basic text extraction is provided by the bundled `scripts/extract_docx.py`; optional external providers are only for advanced capabilities the bundled core does not provide.

Before DOCX execution:
1. resolve the document profile through `references/runtime-profiles.md`;
2. follow `references/dependencies.md`;
3. under `oai-native`, read the entire `/home/oai/skills/docx` Markdown tree in full;
4. under `standalone`, run `python scripts/extract_docx.py --help` before first use;
5. resolve/read an external DOCX provider only when the task requires rendering, conversion, tracked-change/comment manipulation, or another advanced capability;
6. read the current help for every helper before first use.

The bundled extractor defines the anti-skimming text chunk universe. The resolved DOCX provider is authoritative only for additional mechanics within its declared capability profile.

## Anti-skimming extraction manifest

Use `scripts/extract_docx.py` to traverse the OOXML story parts and emit the authoritative chunk manifest. The portable extractor reads the main document plus supported headers, footers, footnotes, endnotes, and comments without depending on `/home/oai/skills`. Every emitted chunk requires exactly one atomic extractive evidence verdict (or explicit non-match), one `chunk_verified` event, and inclusion in deterministic `TRAVERSAL_REPORT.md` before Done.

Within parsed story parts, paragraph styles named `Heading1` through `Heading6` (including the equivalent `Heading 1` through `Heading 6` spelling accepted by the parser) update the six-level `heading_path`. This does not claim support for arbitrary custom Word styles that merely look like headings.

Text extraction does **not** prove layout, field rendering, tracked-change display, comments UI, or other Word-native presentation. Those remain separate visual/structural QA predicates when required.

## Reading and verification

A DOCX is not proven correct by text/XML extraction alone.

For reading/review:
```text
render DOCX
  -> inspect page PNGs
  -> use structural checks for features rendering cannot prove
```

For authoring/editing:
```text
author/edit
  -> render
  -> inspect every page required by the live skill
  -> fix
  -> re-render
```

Comments, fields, tracked changes, content controls, and other Word-native structures may require structural checks in addition to visual inspection.

## DOCX is not a reading workaround

Do not create a DOCX from your own prose because the source PDF/HTML is difficult to ingest.

A derivative DOCX is not the source.

Use DOCX only when:
- the user requested DOCX;
- the deliverable is Word-like;
- the live PDF skill routes text-heavy authoring through DOCX;
- a faithful editable conversion is genuinely part of the task.

## PDF deliverable via DOCX

If the live skills route a text-heavy authored deliverable through DOCX:
1. author/edit DOCX;
2. render and inspect;
3. correct defects;
4. convert using the current PDF conversion guidance;
5. run the live PDF verification workflow on the converted PDF.

Do not use this authoring path for source-paper reading unless the user explicitly asks for a faithful conversion.
