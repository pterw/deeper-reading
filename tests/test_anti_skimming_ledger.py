import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / 'scripts' / 'verify_run.py'


def load_module():
    spec = importlib.util.spec_from_file_location('verify_run_anti_skimming', MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write_json(path: Path, value: dict) -> str:
    path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')
    return _sha(path.read_bytes())


def valid_run(tmp_path: Path, *, fmt: str = 'html', chunk_count: int = 3) -> dict:
    ext = 'md' if fmt == 'markdown' else 'html'
    source_dir = tmp_path / 'source'
    source_dir.mkdir(parents=True, exist_ok=True)
    source = source_dir / f'source.{ext}'
    if fmt == 'markdown':
        source_text = ''.join(
            f'# Section {i}\n\nchunk-{i}-text\n\n' for i in range(1, chunk_count + 1)
        )
        script = ROOT / 'scripts' / 'extract_markdown.py'
    else:
        source_text = ''.join(
            f'<h1>Section {i}</h1><p>chunk-{i}-text</p>' for i in range(1, chunk_count + 1)
        )
        script = ROOT / 'scripts' / 'extract_html.py'
    source.write_text(source_text, encoding='utf-8')
    source_sha = _sha(source.read_bytes())

    manifest_path = tmp_path / 'evidence' / 'chunk-manifest.json'
    result = subprocess.run(
        [sys.executable, str(script), str(source), '--run-root', str(tmp_path), '--max-bytes', '100'],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    manifest = _read_json(manifest_path)
    assert len(manifest['chunks']) == chunk_count
    manifest_sha = _sha(manifest_path.read_bytes())

    entries = []
    for chunk in manifest['chunks']:
        proof = f'chunk-{chunk["ordinal"]}-text'
        raw = chunk['content'].encode('utf-8')
        start = raw.find(proof.encode('utf-8'))
        assert start >= 0
        entries.append({
            'chunk_id': chunk['id'],
            'ordinal': chunk['ordinal'],
            'chunk_sha256': chunk['content_sha256'],
            'outcome': 'evidence',
            'assertions': [{
                'text': proof,
                'chunk_byte_start': start,
                'chunk_byte_end': start + len(proof.encode('utf-8')),
            }],
            'constraints': [],
        })
    ledger = {
        'schema_version': 1,
        'manifest_sha256': manifest_sha,
        'source_sha256': source_sha,
        'entries': entries,
    }
    _write_json(tmp_path / 'evidence' / 'chunk-evidence.json', ledger)
    report = subprocess.run(
        [sys.executable, str(ROOT / 'scripts' / 'traversal_report.py'), '--run-root', str(tmp_path)],
        capture_output=True, text=True, check=False,
    )
    assert report.returncode == 0, report.stdout + report.stderr

    (tmp_path / 'plan.md').write_text('evidence\n', encoding='utf-8')
    for name in [
        'skill-preflight.md', 'source-manifest.md', 'failure-ledger.md',
        'verification-log.txt', 'format-qa.md',
    ]:
        path = tmp_path / 'evidence' / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('evidence\n', encoding='utf-8')

    ids = [c['id'] for c in manifest['chunks']]
    return {
        '_ledger_path': str(tmp_path / 'run.json'),
        'source': {
            'uri': manifest['source']['uri'],
            'local_path': str(source.resolve()),
            'sha256': source_sha,
            'format': fmt,
            'authority': 'primary',
            'identity_verified': True,
        },
        'fidelity': {'preserved': True, 'substitutions': []},
        'preflight': {
            'skill_read': True,
            'required_references_read': True,
            'helper_help_read': True,
            'runtime_profile_resolved': True,
            'traversal_plan_ready': True,
        },
        'plan': {'path': 'plan.md', 'nodes': ['read-document']},
        'events': [
            {'type': 'plan_written'},
            {'type': 'execution_started'},
            {'type': 'node_started', 'node': 'read-document'},
            *[{'type': 'chunk_verified', 'chunk_id': chunk['id'], 'chunk_sha256': chunk['content_sha256'], 'evidence': 'evidence/chunk-evidence.json'} for chunk in manifest['chunks']],
            {'type': 'node_passed', 'node': 'read-document', 'evidence': 'evidence/chunk-evidence.json'},
            {'type': 'verification_started'},
            {'type': 'verification_passed', 'evidence': 'evidence/verification-log.txt'},
            {'type': 'done'},
        ],
        'chunking': {
            'manifest': 'evidence/chunk-manifest.json',
            'manifest_sha256': manifest_sha,
            'evidence_ledger': 'evidence/chunk-evidence.json',
            'traversal_report': 'deliverables/TRAVERSAL_REPORT.md',
        },
        'coverage': {'required': ids.copy(), 'completed': ids.copy()},
        'qa': {'required': ['html-structure'], 'passed': ['html-structure']},
        'deliverable': {'requested': 'answer', 'provided': True, 'paths': [], 'traversal_report': 'deliverables/TRAVERSAL_REPORT.md'},
        'evidence': {
            'plan_status': 'plan.md',
            'skill_preflight': 'evidence/skill-preflight.md',
            'source_manifest': 'evidence/source-manifest.md',
            'chunk_ledger': 'evidence/chunk-evidence.json',
            'failure_ledger': 'evidence/failure-ledger.md',
            'verification_log': 'evidence/verification-log.txt',
            'format_qa': 'evidence/format-qa.md',
            'traversal_report': 'deliverables/TRAVERSAL_REPORT.md',
        },
    }

def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding='utf-8'))


def _rewrite_ledger(tmp_path: Path, run: dict, mutate) -> None:
    path = tmp_path / 'evidence' / 'chunk-evidence.json'
    ledger = _read_json(path)
    mutate(ledger)
    _write_json(path, ledger)


def test_complete_extractor_evidence_ledger_passes(tmp_path):
    module = load_module()
    assert module.validate_run(valid_run(tmp_path)) == []


def test_chunking_contract_is_mandatory(tmp_path):
    module = load_module()
    run = valid_run(tmp_path)
    run.pop('chunking')
    errors = module.validate_run(run)
    assert any('chunking contract is required' in e for e in errors)


def test_missing_evidence_for_one_emitted_chunk_rejects_premature_done(tmp_path):
    module = load_module()
    run = valid_run(tmp_path)
    _rewrite_ledger(tmp_path, run, lambda ledger: ledger['entries'].pop())
    errors = module.validate_run(run)
    assert any('missing evidence for emitted chunk' in e for e in errors)


def test_duplicate_chunk_evidence_is_rejected(tmp_path):
    module = load_module()
    run = valid_run(tmp_path)
    def mutate(ledger):
        ledger['entries'].append(copy.deepcopy(ledger['entries'][0]))
    _rewrite_ledger(tmp_path, run, mutate)
    errors = module.validate_run(run)
    assert any('duplicate evidence for chunk' in e for e in errors)


def test_evidence_for_nonexistent_chunk_is_rejected(tmp_path):
    module = load_module()
    run = valid_run(tmp_path)
    def mutate(ledger):
        ledger['entries'].append({
            'chunk_id': 'ghost-chunk', 'ordinal': 99, 'chunk_sha256': '0' * 64,
            'outcome': 'non_match', 'reason': 'not in manifest',
        })
    _rewrite_ledger(tmp_path, run, mutate)
    errors = module.validate_run(run)
    assert any('evidence references unknown chunk' in e for e in errors)


def test_evidence_outcome_must_contain_facts_constraints_or_non_match_reason(tmp_path):
    module = load_module()
    run = valid_run(tmp_path)
    def mutate(ledger):
        ledger['entries'][0] = {
            'chunk_id': ledger['entries'][0]['chunk_id'],
            'ordinal': 1,
            'chunk_sha256': ledger['entries'][0]['chunk_sha256'],
            'outcome': 'evidence',
            'assertions': [],
            'constraints': [],
        }
    _rewrite_ledger(tmp_path, run, mutate)
    errors = module.validate_run(run)
    assert any('must record assertions/constraints or explicit non_match' in e for e in errors)


def test_non_match_requires_reason(tmp_path):
    module = load_module()
    run = valid_run(tmp_path)
    def mutate(ledger):
        entry = ledger['entries'][0]
        entry.clear()
        entry.update({
            'chunk_id': run['coverage']['required'][0],
            'ordinal': 1,
            'chunk_sha256': _read_json(tmp_path / 'evidence' / 'chunk-manifest.json')['chunks'][0]['content_sha256'],
            'outcome': 'non_match',
            'reason': '',
        })
    _rewrite_ledger(tmp_path, run, mutate)
    errors = module.validate_run(run)
    assert any('non_match requires a reason' in e for e in errors)


def test_forged_smaller_coverage_cannot_shrink_manifest_universe(tmp_path):
    module = load_module()
    run = valid_run(tmp_path)
    run['coverage']['required'] = run['coverage']['required'][:1]
    run['coverage']['completed'] = run['coverage']['completed'][:1]
    errors = module.validate_run(run)
    assert any('coverage.required must exactly mirror manifest chunk ids' in e for e in errors)


def test_manifest_hash_is_bound_to_run(tmp_path):
    module = load_module()
    run = valid_run(tmp_path)
    run['chunking']['manifest_sha256'] = '0' * 64
    errors = module.validate_run(run)
    assert any('chunking.manifest_sha256 does not match manifest bytes' in e for e in errors)


def test_manifest_source_hash_is_bound_to_run_and_source_file(tmp_path):
    module = load_module()
    run = valid_run(tmp_path)
    run['source']['sha256'] = '1' * 64
    errors = module.validate_run(run)
    assert any('source sha256' in e for e in errors)


def test_chunk_content_hash_and_offsets_are_verified(tmp_path):
    module = load_module()
    run = valid_run(tmp_path)
    manifest_path = tmp_path / 'evidence' / 'chunk-manifest.json'
    manifest = _read_json(manifest_path)
    manifest['chunks'][1]['content_sha256'] = '2' * 64
    new_manifest_sha = _write_json(manifest_path, manifest)
    run['chunking']['manifest_sha256'] = new_manifest_sha
    ledger = _read_json(tmp_path / 'evidence' / 'chunk-evidence.json')
    ledger['manifest_sha256'] = new_manifest_sha
    _write_json(tmp_path / 'evidence' / 'chunk-evidence.json', ledger)
    errors = module.validate_run(run)
    assert any('manifest chunk content hash mismatch' in e for e in errors)


def test_markdown_is_a_supported_source_format(tmp_path):
    module = load_module()
    run = valid_run(tmp_path, fmt='markdown')
    errors = module.validate_run(run)
    assert not any('source.format must' in e for e in errors)


def test_dod_source_coverage_predicate_comes_from_chunk_evidence(tmp_path):
    module = load_module()
    run = valid_run(tmp_path)
    _rewrite_ledger(tmp_path, run, lambda ledger: ledger['entries'].pop())
    errors = module.validate_run(run)
    dod = module.build_dod(run, errors)
    assert dod['predicates']['source_coverage_complete'] is False


def test_twelve_emitted_four_evidenced_is_not_done(tmp_path):
    module = load_module()
    run = valid_run(tmp_path, chunk_count=12)
    def mutate(ledger):
        ledger['entries'] = ledger['entries'][:4]
    _rewrite_ledger(tmp_path, run, mutate)
    errors = module.validate_run(run)
    missing = [e for e in errors if 'missing evidence for emitted chunk' in e]
    assert len(missing) == 8
    dod = module.build_dod(run, errors)
    assert dod['passed'] is False
    assert dod['predicates']['source_coverage_complete'] is False


def test_skipped_middle_chunk_is_rejected_even_when_later_chunks_are_evidenced(tmp_path):
    module = load_module()
    run = valid_run(tmp_path, chunk_count=12)
    def mutate(ledger):
        del ledger['entries'][5]
    _rewrite_ledger(tmp_path, run, mutate)
    errors = module.validate_run(run)
    assert any('missing evidence for emitted chunk' in e for e in errors)


def test_early_done_before_final_verification_is_rejected(tmp_path):
    module = load_module()
    run = valid_run(tmp_path, chunk_count=12)
    run['events'] = [
        {'type': 'plan_written'},
        {'type': 'execution_started'},
        {'type': 'node_started', 'node': 'read-document'},
        {'type': 'node_passed', 'node': 'read-document'},
        {'type': 'done'},
    ]
    errors = module.validate_run(run)
    assert any('done requires prior verification_started' in e for e in errors)
    assert any('done requires prior verification_passed' in e for e in errors)


def test_self_consistent_forged_smaller_manifest_is_rejected_by_source_reproduction(tmp_path):
    module = load_module()
    run = valid_run(tmp_path, chunk_count=12)
    manifest_path = tmp_path / 'evidence' / 'chunk-manifest.json'
    manifest = _read_json(manifest_path)
    manifest['chunks'] = manifest['chunks'][:4]
    manifest['chunking']['chunk_count'] = 4
    stream = ''.join(chunk['content'] for chunk in manifest['chunks']).encode('utf-8')
    manifest['extracted_text_bytes'] = len(stream)
    manifest['extracted_text_sha256'] = _sha(stream)
    forged_manifest_sha = _write_json(manifest_path, manifest)
    run['chunking']['manifest_sha256'] = forged_manifest_sha
    ids = [chunk['id'] for chunk in manifest['chunks']]
    run['coverage'] = {'required': ids.copy(), 'completed': ids.copy()}
    ledger = _read_json(tmp_path / 'evidence' / 'chunk-evidence.json')
    ledger['manifest_sha256'] = forged_manifest_sha
    ledger['entries'] = ledger['entries'][:4]
    _write_json(tmp_path / 'evidence' / 'chunk-evidence.json', ledger)
    errors = module.validate_run(run)
    assert any('reproduced extraction' in e for e in errors)


def test_every_manifest_chunk_requires_discrete_chunk_verified_event(tmp_path):
    module = load_module()
    run = valid_run(tmp_path, chunk_count=12)
    run['events'] = [
        event for event in run['events']
        if event.get('type') != 'chunk_verified' or event.get('chunk_id') in run['coverage']['required'][:4]
    ]
    errors = module.validate_run(run)
    missing = [e for e in errors if 'missing chunk_verified event' in e]
    assert len(missing) == 8


def test_chunk_verified_events_must_follow_manifest_order(tmp_path):
    module = load_module()
    run = valid_run(tmp_path, chunk_count=3)
    positions = [i for i, event in enumerate(run['events']) if event.get('type') == 'chunk_verified']
    run['events'][positions[0]], run['events'][positions[1]] = run['events'][positions[1]], run['events'][positions[0]]
    errors = module.validate_run(run)
    assert any('chunk_verified events must follow manifest order' in e for e in errors)
