# PDF fixture provenance

These are project-owned synthetic documents, generated on 2026-09-14 by
`build_fixture.py`. The text source generator uses only the standard library;
it writes a tiny PDF, not an extraction backend. pypdf 5.3.0 produced the
encrypted variant. No reportlab dependency is needed to run these tests.

- Three pages, in order: Alpha text and a text table; an empty page; Omega text.
- Expected chunks at `--max-bytes 12000`: three, with page locators `[1]`, `[2]`, `[3]`.
- Both pypdf 5.3.0 and pdftotext 24.08.0 were exercised. Their text whitespace
  differs; each backend must reproduce its own manifest exactly.
- The encrypted sample uses the public test password `fixture-password` and
  RC4-128 solely to test the password boundary. It is not a security example.
- Encryption can produce different bytes when regenerated; update and review
  the hashes deliberately. Tests never regenerate either source file.

SHA-256:

| File | Digest |
| --- | --- |
| `source/sample.pdf` | `6d9ed293afe5fd6779bafef0f54c812e68737570c2afadca3dab67b2581eacca` |
| `source/sample-encrypted.pdf` | `a09bcf5e8b8299701984bb20cb235e4ec2a77f54e1c6bc76184e22ce99c3162a` |

`provenance.json` holds the machine-checked copies of these expectations.
