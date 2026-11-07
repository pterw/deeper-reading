## What changed and why

## How it was tested

Commands run and their results:

## Checklist

- [ ] `python -m pytest -q -rs` exits 0
- [ ] `npm test` exits 0 (if `installer/`, `package.json` or `tests/node/` changed)
- [ ] `python tools/release_check.py` exits 0
- [ ] A behaviour change comes with a test that fails without it
- [ ] A change to a published contract keeps old inputs working, or the CHANGELOG line names the break
- [ ] A change to `installer/*.py` or `installer/adapters/*.py` also changes the matching `installer/node/*.js`
- [ ] A change to what ships updates `MANIFEST.json`, `package.json` `files` and `installer/distribution.py`
