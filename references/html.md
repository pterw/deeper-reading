# HTML Source Workflow

HTML is a first-class source format.

An official publisher, laboratory, project, proceedings, or author publication page can be the authoritative publication even when an arXiv mirror or downloadable PDF also exists.

## Establish authority

Before reading:

1. verify exact title, authors, publication/version date, and host;
2. determine whether the HTML is the complete primary publication or a summary/landing page;
3. distinguish companion commentary from the full paper;
4. record the canonical source used.

Do not prefer arXiv merely because its URL pattern is familiar.


## Bundled portable extraction

For basic exhaustive traversal, use the bundled `scripts/extract_html.py` to emit the authoritative chunk manifest. Run `--help` before first use, then perform one bounded extraction operation. The manifest defines the complete chunk universe: every chunk must receive atomic extractive evidence (or explicit non-match), one `chunk_verified` event, and a row in deterministic `TRAVERSAL_REPORT.md` before Done.

The bundled extractor is text/structure oriented: it preserves heading context, tables, and preformatted blocks while excluding script/style content. Visual figure interpretation remains a separate QA responsibility when the source contains meaning that cannot be proven from DOM text alone.

## Chunk by document structure

Use the HTML's own hierarchy:

```text
paper
  -> section
    -> subsection
      -> figure/table/appendix unit
```

Read one bounded structural unit at a time.

If a section is too large:
- split by subsection;
- if still too large, split around figures/tables or paragraph groups;
- preserve heading/anchor provenance.

Do not retry the entire page unchanged after a size failure.

## What is authoritative

For prose:
- source DOM/text under the correct heading is authoritative.

For figures/tables:
- inspect the actual figure/table and its caption/context;
- do not infer visual content from extracted alt text alone when the visual matters.

For equations:
- preserve the source equation context; do not flatten mathematical structure into prose and treat the paraphrase as source evidence.

## Do not manufacture a document

Do not convert primary HTML into:
- a summary DOCX;
- a review PDF;
- a paraphrased "working copy";

and then use that derivative as proof of reading.

A faithful conversion is a separate task and must preserve source content. A summary is downstream analysis.

## Ingress failures

Browser/web access, shell networking, direct downloads, and connectors are separate ingress planes.

If one fails:
1. stop that operation;
2. invoke systematic debugging;
3. isolate whether the failure is source discovery, browser fetch, shell DNS, download size, authentication, or another boundary;
4. retry only the smallest diagnosed unit or use a documented semantics-preserving ingress path.

If the only remaining path changes source authority or fidelity, follow `references/failure-recovery.md`.
