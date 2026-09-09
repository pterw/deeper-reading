# Source Acquisition

Source discovery and source ingress are different nodes.

## Find the source of record

For academic/publication work, search the publication ecosystem rather than assuming one host:

1. publisher or proceedings;
2. official research-lab/project publication;
3. author or institutional publication;
4. journal/conference archive;
5. preprint mirror such as arXiv.

The exact order can vary by field, but authority must be established explicitly.

Verify:
- title;
- authors;
- version/date when material;
- whether the page/file is complete;
- whether it is primary, mirrored, or commentary.

## Separate ingress planes

These statements are not equivalent:

```text
source exists
shell can resolve host
browser can open page
direct downloader can fetch file
PDF reader accepts file size
connector can ingest asset
```

A failure in one plane proves only that plane failed.

## One acquisition operation at a time

Examples of separate nodes:
- locate canonical publication;
- open HTML;
- locate PDF link;
- download PDF;
- inspect local file existence/size;
- pass asset to a connector.

Do not wrap all of these into one command or one undiagnosable tool call.

## Failure handling

On an acquisition failure:
1. stop downstream parsing/rendering;
2. invoke systematic debugging;
3. identify the failed plane;
4. use **one recovery branch at a time** when the diagnosis supports it;
5. verify that branch before trying another;
6. iterate documented semantics-preserving branches one-by-one until resolved or the recovery tree reaches its stop condition;
7. do not silently change from primary to secondary source.

If the user's requirement specifically needs original PDF pages and no original PDF can be acquired after documented paths are exhausted, disclose that exact limitation and brainstorm alternatives rather than fabricating a substitute.
