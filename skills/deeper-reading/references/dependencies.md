# Document Dependency Resolution

Detailed document behavior belongs to the resolved document profile, not to copied instructions in this custom skill. Resolve `oai-native` or `standalone` through `references/runtime-profiles.md` before format execution.

## Shared CLI/tool prerequisites

Before first use of a helper:

1. identify the governing task guide;
2. read it in full;
3. run the helper's current top-level `--help`;
4. if it has subcommands, run the selected subcommand's `--help`;
5. only then execute the real operation.

Never infer syntax from earlier conversations or from similarly named helpers.

## standalone basic extraction

HTML, Markdown and DOCX use the Python standard library. PDF text extraction
requires an optional backend: `pypdf`, `PyMuPDF`, `pdfplumber`, or an existing
`pdftotext` executable, in that detection order. A bundled command does not
mean a bundled PDF parser. Users who choose a Python backend can install one
with `python -m pip install pypdf`; `PyMuPDF` and `pdfplumber` are the other
Python backends. An already installed pdftotext needs no additional Python
package. No dependency is installed automatically.

The implemented PDF adapters expose text only. Library support for geometry
does not establish layout QA; none of these extraction paths proves OCR.

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

Under `standalone`, the bundled extractors govern basic text chunk generation; any approved external dependency governs only the advanced capabilities it explicitly declares.

This custom skill governs exhaustive traversal, anti-skimming coverage, failure boundaries, and process order. Format-specific providers govern visual/layout/OCR mechanics within their declared capability profiles.

## standalone external capability resolution

On external Agent Skills hosts, start with the bundled extraction core. If the task requires an advanced capability the bundled core does not provide, resolve the optional external provider declared by the installer/runtime profile, record source + revision/version + content hash, inspect its current guidance, and fail closed before execution when that required capability is absent.
