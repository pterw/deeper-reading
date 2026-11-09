# Source Manifest

| Field | Value |
|---|---|
| URI | `file:///C:/ssw/dr-live-deepseek2/source/anti-skimming-plan.md` |
| Local path (bound copy) | `source/anti-skimming-plan.md` (relative to the run root) |
| Original input path | `C:/ssw/dr-live-deepseek2/source/anti-skimming-plan.md` |
| Format | `markdown` |
| Authority | `primary` — the file the user named as the source document |
| Size | 6814 bytes |
| SHA-256 | `b4d4182e1c88f8856da49184ed3e29899cec597098d8b0ef6bd4c23416647840` |
| Version / date | none stated in the document; no version or date line exists |
| Identity verified | yes — the bound copy hashes to the same SHA-256 as the original input |

## Identity check

The run root holds a byte-identical copy at `source/anti-skimming-plan.md`. The copy exists
because the verifier re-extracts `source.local_path` and the run root is the proof boundary;
the copy is a faithful byte copy, not a conversion or a derivative.

```
sha256(original input)  = b4d4182e1c88f8856da49184ed3e29899cec597098d8b0ef6bd4c23416647840
sha256(bound copy)      = b4d4182e1c88f8856da49184ed3e29899cec597098d8b0ef6bd4c23416647840
```

## Completeness

The document is a single Markdown file with no external parts, no images, no SVG and no
diagrams. The extractor recorded no `media` list, so there is no media to disposition.
The document ends with the fenced `text` block of its `## Definition of Done` section; the
extractor emitted 14 chunks covering the whole normalized text stream (6695 bytes,
`extracted_text_sha256` `ce06e5ec12fbdf205555202c8552633993957e6e8134d258a3be68d37ef98691`).
