# DeepSeek first-run provenance fixture

This directory preserves the first real `deeper-reading` run used to validate the workflow against a long Markdown implementation plan. The original run-local prototype scripts are not kept.

Fixture invariants:

- 70 canonical chunks
- 70 evidence verdicts
- 192 assertions
- schema-v1 known-good evidence is rebound by the production schema-v2 builder

Original SHA-256 values:

- `chunk-manifest.json`: `0aaf43caa29213a9f475c919fc22261e65caeaba4c6d8675e85b314c292dc6ea`
- `chunk-evidence-v1.json`: `276282b6841983b8acd4566c1df09d2ba5ae81bfa84a971dbe9a74a1c330aa96`

`draft-evidence.json` is derived deterministically from the known-good v1 ledger. Unique quotes omit byte spans; repeated quotes would retain their exact v1 span.
