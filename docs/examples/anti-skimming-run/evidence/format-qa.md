# Format QA

Format: `markdown`. Required check: `markdown-structure`.

## markdown-structure

| Check | Result | Evidence |
|---|---|---|
| Heading hierarchy is preserved | pass | Chunk 1 carries the level-1 heading; chunks 2-13 carry level-2 headings; `heading_path` on every chunk records the full path. |
| Fenced code blocks are atomic | pass | The `text` block under `## Definition of Done` is emitted as its own chunk (`markdown-000014-d535414423b8`) with `atomic_kind: fenced_code`; it was not split. |
| Tables are atomic | pass | The source has no Markdown tables; nothing to split. |
| No text is lost between blocks | pass | `extracted_text_bytes` 6695 with contiguous spans; the verifier's re-extraction reproduced the manifest exactly. |
| Media | not applicable | The manifest has no `media` key: the source has no images, SVG or diagrams. |
| Encoding | pass | UTF-8 throughout; em dashes in task headings survive as U+2014. |

## Scope statement

This is text-structure QA only. The source is Markdown, so no visual rendering, OCR,
layout or form check applies, and none is claimed.
