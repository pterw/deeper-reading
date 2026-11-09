# Example run

`anti-skimming-run/` is a real run of the deeper-reading skill, done by another
model on a 14-chunk implementation plan from this repository's history. It is
committed as it was left, so you can check it.

## Check it

Copy the folder somewhere temporary, then run the verifier on the copy:

```
python skills/deeper-reading/scripts/verify_run.py <copy>/run.json
```

The verifier writes `dod.json` into the run folder, so never run it in place.
Do not convert the source's line endings: its SHA-256 is recorded in `run.json`
and the chunk manifest.

## What this proves, and what it does not

It proves coverage and byte fidelity: every chunk of the source was read and
logged once, and every quote matches the source exactly. It does not prove the
analysis is right.

## Notes on this run

- Its section 5 lists 24 narrowings, some of which repeat or stretch.
- It wrote its phase-receipt rows after their gates, without the note the skill
  asks for.

## The four live runs

| Model and effort | Harness | Result | Failed verifications | Notes |
| --- | --- | --- | --- | --- |
| DeepSeek V4.1 Flash, High | VS Code Copilot | passed | 1 (event order) | earlier skill text and prompt |
| GPT-6.1 Terra, High | Codex | stopped | none | earlier skill; a receipt rule left no honest way to finish, since fixed |
| GPT-6.1 Terra, High | Codex | passed | 2 (an unlisted `source.authority` value, an unrecovered failed node) | quotes verbatim, analysis thin |
| DeepSeek V4.1 Flash, Max | VS Code Copilot | passed | 1 (verification log written late) | this folder |
