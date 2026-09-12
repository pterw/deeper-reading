# DeepSeek first-run provenance fixture

This directory preserves the first real `deeper-reading` run used to validate the workflow against a long Markdown implementation plan. The prototype Python files are provenance only: production code must not import or execute them as trusted runtime modules.

Fixture invariants:

- 70 canonical chunks
- 70 evidence verdicts
- 192 assertions
- schema-v1 known-good evidence is rebound by the production schema-v2 builder

Original SHA-256 values:

- `chunk-manifest.json`: `0aaf43caa29213a9f475c919fc22261e65caeaba4c6d8675e85b314c292dc6ea`
- `chunk-evidence-v1.json`: `276282b6841983b8acd4566c1df09d2ba5ae81bfa84a971dbe9a74a1c330aa96`
- `prototype/assertions_a.py`: `0bd726ecf8e53eb95befc57654f7b0db1ba2223b20d4c7a6277665670b449c79`
- `prototype/assertions_b.py`: `09b4caf455b9ab5a3453fd22106e0ab7fc2fa91b753a6ea17c582f609ae2e0e2`
- `prototype/assertions_c.py`: `6ca0311fb4d86dd0b87b5a124ce24e10de8c7f0379eab26b8ec9f4fdb39f1d14`
- `prototype/build_evidence.py`: `d89ec4ba16ec51539b7b86818b7e9aa1bc9aa96cd35d78b68b7ee0ef59e4a30d`
- `prototype/build_run.py`: `37d79f955b8a05b96cc4db8ce1ff9553f06b84592ba88898c4c78266b07f7204`
- `prototype/dump_chunks.py`: `19dae2d4ce8246d4955b6c2c57538b2e5ffac9ace40a50f77e06ff4efef72a73`

`draft-evidence.json` is derived deterministically from the known-good v1 ledger. Unique quotes omit byte spans; repeated quotes would retain their exact v1 span. No prototype script is executed to create trusted expected output.
