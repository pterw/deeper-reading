# Traversal Report

## Run summary

- Source: `/golden/source`
- Format: `html`
- Source SHA-256: `d9644aaad2127232a17ebf0d46bdf36f4344b8f68a40c6cd9150d737a41dd52f`
- Canonical chunks: 2
- Evidence verdicts: 2
- Non-match verdicts: 0
- Assertions: 2
- Constraints: 0

## Chunk index

| # | Chunk | Location | Kinds | Outcome | Atoms |
|---:|---|---|---|---|---:|
| 1 | `html-000001-420a9fb11d94` | `A` | `heading+text` | `evidence` | 1 |
| 2 | `html-000002-2c769b58d2bd` | `B` | `heading+text` | `evidence` | 1 |

## Chunk details

### 01 · `html-000001-420a9fb11d94` — A

- Outcome: `evidence`
- Byte span: `0..15`
- Kinds: `heading+text`
- Locator: `A`

**Assertions**

- bytes `2..14` — Alpha proof.

<details><summary>Full locator</summary>

`{"blocks":[{"heading_path":["A"],"kind":"heading","level":1},{"heading_path":["A"],"kind":"text"}],"heading_path":["A"]}`

</details>

### 02 · `html-000002-2c769b58d2bd` — B

- Outcome: `evidence`
- Byte span: `15..30`
- Kinds: `heading+text`
- Locator: `B`

**Assertions**

- bytes `2..14` — Beta caveat.

<details><summary>Full locator</summary>

`{"blocks":[{"heading_path":["B"],"kind":"heading","level":1},{"heading_path":["B"],"kind":"text"}],"heading_path":["B"]}`

</details>
