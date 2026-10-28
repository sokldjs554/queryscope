"""Recompute the recorded v4 evaluation without network or model calls.

This derived analysis preserves every primary response and verdict. Citation
checks deliberately inspect raw evidence even when schema validation fails.
"""
from collections import Counter
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import statistics
import subprocess

from searchclinic.corpus.evalset import EvalQuery
from searchclinic.evaluation.llm_campaign import campaign_bundle, campaign_engine
from searchclinic.evaluation.runtime_campaign import assess_runtime_generation
from searchclinic.rag.explanation import source_quote, validate_explanation
from searchclinic.rag.knowledge import KnowledgeDoc
from searchclinic.rag.runtime_contract import validate_runtime_explanation

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
BASE = ROOT / 'docs/verification'
SOURCE_COMMIT = '6febc3eddde6a00bbb8454d29d482ee0049d4bbd'
PATHS = {
    'v3_primary': BASE / 'queryscope-v3/actual-api-v1/results.json',
    'v3_secondary': BASE / 'queryscope-v3/actual-api-audit-v1/audit.json',
    'old_response_runtime_audit': BASE / 'queryscope-v4/run-v1/audit.json',
    'prepared': BASE / 'queryscope-v4/live-prepared-v1/requests.json',
    'approval': BASE / 'queryscope-v4/live-approval.json',
    'v4_actual': BASE / 'queryscope-v4/actual-api-v1/results.json',
}


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def json_sha(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode('utf-8')).hexdigest()


def pair(row):
    return row['case_id'], row['condition']


def counts(rows, cases):
    assessments = [r['assessment'] for r in rows]
    abstain = [r for r in rows if cases[r['case_id']]['expected_action'] == 'abstain_no_patch']
    eligible = [r for r in rows if cases[r['case_id']]['expected_family']]
    return {
        'planned_or_attempted': len(rows),
        'api_errors': sum(r['generation_status'] == 'api_error' for r in rows),
        **{k: sum(a['validated_status'] == k for a in assessments) for k in ['supported', 'abstain', 'invalid']},
        'abstention_contract_eligible': len(abstain),
        'abstention_contract_pass': sum(r['assessment']['validated_status'] == 'abstain' and
            r['model_answer']['status'] == 'abstain' and not r['model_answer']['patches'] for r in abstain),
        'wrong_patch_on_abstain_required': sum(bool(r['model_answer']['patches']) for r in abstain),
        'literal_family_match': sum(r['model_answer']['family'] == cases[r['case_id']]['expected_family'] for r in eligible),
        'family_label_eligible': len(eligible), 'semantic_human_review': 'pending',
    }


def summary(rows, cases):
    return {'all': counts(rows, cases), **{condition: counts(
        [r for r in rows if r['condition'] == condition], cases) for condition in ['hint', 'no_hint']}}


def citation_checks(row):
    sources = {doc['id']: doc for doc in row['context']['documents']}
    checks = []
    for item in row['model_answer']['evidence']:
        result = dict(item)
        if item['doc_id'] not in sources:
            result['status'] = 'unknown_evidence_source'
        else:
            try:
                matched, recovered = source_quote(item['quote'], sources[item['doc_id']]['body'])
                result.update(status='verified', matched_source=matched, display_format_recovered=recovered)
            except ValueError:
                result['status'] = 'text_mismatch'
        checks.append(result)
    return checks


def citation_counts(rows):
    checked = [(row, citation_checks(row)) for row in rows]
    statuses = Counter(c['status'] for _, checks in checked for c in checks)
    return {'raw_citations': sum(statuses.values()), 'statuses': dict(statuses),
        'responses_with_unknown_source': sum(any(c['status'] == 'unknown_evidence_source' for c in checks) for _, checks in checked),
        'responses_with_text_mismatch': sum(any(c['status'] == 'text_mismatch' for c in checks) for _, checks in checked),
        'responses_with_any_citation_error': sum(any(c['status'] != 'verified' for c in checks) for _, checks in checked)}


def effects(rows):
    measured = [r for r in rows if r['assessment']['patch_effect']['status'] == 'measured']
    accepted = [r for r in measured if r['assessment']['patch_effect']['gate']['accepted']]
    return {'measured': len(measured), 'accepted_responses': len(accepted),
        'rejected_responses': len(measured) - len(accepted),
        'accepted_unique_queries': sorted({r['context']['query'] for r in accepted}),
        'scope': 'each candidate independently; never a combined configuration',
        'regression_decreases': {scope: [dict(case_id=r['case_id'], condition=r['condition'], **change)
            for r in measured for change in r['assessment']['patch_effect'].get(scope, {}).get('summary', {}).get('decreases', [])]
            if all(scope in r['assessment']['patch_effect'] for r in measured) else None
            for scope in ['development_16', 'original_36']}}


def main():
    source_hashes = {name: sha(path) for name, path in PATHS.items()}
    data = {name: read(path) for name, path in PATHS.items()}
    old, prior, prepared, approval, current = [data[k] for k in
        ['v3_primary', 'old_response_runtime_audit', 'prepared', 'approval', 'v4_actual']]
    assert data['v3_secondary']['source_sha256'] == prior['source_sha256'] == source_hashes['v3_primary']
    assert current['source_sha256'] == source_hashes['old_response_runtime_audit']
    assert current['prepared_sha256'] == approval['prepared_sha256'] == source_hashes['prepared']
    assert current['approval_sha256'] == source_hashes['approval']
    canonical = json_sha({'suite': prepared['suite'], 'model': prepared['model'],
        'source_sha256': prepared['source_sha256'],
        'ordered_payload_sha256': [r['payload_sha256'] for r in prepared['requests']]})
    assert current['canonical_campaign_sha256'] == prepared['canonical_campaign_sha256'] == approval['canonical_campaign_sha256'] == canonical
    assert current['complete'] and current['attempts'] == current['responses'] == 48
    assert current['errors'] == current['provenance_errors'] == 0
    assert current['raw_responses_received'] == 48 and current['cost_estimate_complete']
    assert [pair(r) for r in current['rows']] == [pair(r) for r in prepared['requests']]
    assert len({pair(r) for r in current['rows']}) == 48
    assert len({pair(r) for r in old['rows']}) == 24
    bundle = campaign_bundle('queryscope-v3')
    assert prepared['frozen_manifest'] == bundle['manifest']
    cases = {c['id']: c for c in bundle['cases']}
    engine = campaign_engine(bundle)
    evalset = [EvalQuery(c['query'], c['qrels']) for c in bundle['cases'] if c['qrels']]
    folder = PATHS['v4_actual'].parent
    old_ids = {r['generation']['response_id'] for r in old['rows']}
    seen, total_cost, usage, latencies = set(), Decimal('0'), Counter(), []
    for index, (row, request) in enumerate(zip(current['rows'], prepared['requests']), 1):
        assert row['context'] == request['context']
        assert json_sha(row['context']) == row['context_sha256'] == request['context_sha256']
        assert json_sha(request['payload']) == row['payload_sha256'] == request['payload_sha256']
        assert len(json.dumps(request['payload'], ensure_ascii=False).encode('utf-8')) == request['payload_bytes'] <= 11000
        receipt = row['http_response']; raw_path = folder / receipt['body_path']
        assert read(raw_path.with_suffix('.receipt.json')) == receipt
        assert receipt['number'] == index and pair(receipt) == pair(row)
        assert hashlib.sha256(json.dumps(request['payload'], ensure_ascii=False).encode('utf-8')).hexdigest() == receipt['request_body_sha256']
        assert sha(raw_path) == receipt['saved_body_sha256'] == receipt['received_body_sha256']
        assert receipt['secret_redacted'] is False and receipt['http_status'] == 200
        envelope = read(raw_path)
        assert envelope['status'] == receipt['upstream_status'] == 'completed'
        assert envelope['model'] == row['observed_model'] == row['requested_model'] == current['model'] == receipt['observed_model']
        response_id = envelope['id']
        assert response_id == row['generation']['response_id'] == receipt['response_id']
        assert response_id not in seen and response_id not in old_ids
        seen.add(response_id)
        parts = [part['text'] for item in envelope['output'] if item.get('type') == 'message'
                 for part in item.get('content', []) if part.get('type') == 'output_text']
        assert json.loads(''.join(parts)) == row['model_answer'] == row['generation']['raw']
        assert envelope['usage'] == receipt['usage'] == row['generation']['usage']
        tokens = envelope['usage']
        assert tokens['input_tokens'] + tokens['output_tokens'] == tokens['total_tokens']
        assert tokens['output_tokens'] <= 800
        cost = Decimal(tokens['input_tokens']) * Decimal('.00000075') + Decimal(tokens['output_tokens']) * Decimal('.0000045')
        assert cost == Decimal(str(receipt['estimated_usd'])) == Decimal(str(row['generation']['estimated_usd']))
        total_cost += cost
        usage.update({k: tokens[k] for k in ['input_tokens', 'output_tokens', 'total_tokens']})
        usage['cached_input_tokens'] += tokens['input_tokens_details']['cached_tokens']
        usage['reasoning_output_tokens'] += tokens['output_tokens_details']['reasoning_tokens']
        latencies.append(row['generation']['latency_ms'])
        assert row['generation_status'] == row['assessment_status'] == 'completed'
        recomputed = assess_runtime_generation(row['model_answer'], row['context'], cases[row['case_id']], engine, evalset)
        # Metric hit lists are tuples in memory and arrays in the saved JSON.
        # Compare their complete JSON representations without rewriting values.
        assert json_sha(recomputed) == json_sha(row['assessment']), pair(row)
    assert total_cost == Decimal(str(current['estimated_usd']))
    ledgers = [read(folder / f'campaign-state/budget-{i}.json') for i in range(2)]
    assert all(ledger == {'calls': 24, 'reserved_usd': .3} for ledger in ledgers)
    assert all(read(folder / f'budget-{i}-receipt.json') == ledgers[i] for i in range(2))
    assert sum(ledger['calls'] for ledger in ledgers) == current['attempts']
    assert sum(Decimal(str(ledger['reserved_usd'])) for ledger in ledgers) == Decimal(str(current['reserved_usd'])) == Decimal('.6')
    local_claim = read(folder / 'campaign-state/execution-claim.json')
    for key in ['canonical_campaign_sha256', 'prepared_sha256', 'approval_sha256', 'suite']:
        assert local_claim[key] == current[key]
    remote_claim = read(folder / 'campaign-state/remote-claim.json'); workflow = read(folder / 'workflow.json')
    assert remote_claim['canonical_campaign_sha256'] == canonical
    assert remote_claim['ref'] == 'refs/tags/queryscope-v4-runtime-paid-' + canonical
    assert remote_claim['commit'] == workflow['GITHUB_SHA']
    assert remote_claim['run_id'] == workflow['GITHUB_RUN_ID']
    assert remote_claim['run_attempt'] == workflow['GITHUB_RUN_ATTEMPT'] == '1'
    assert workflow['GITHUB_REPOSITORY'] == 'sokldjs554/queryscope'
    relative_folder = str(folder.relative_to(ROOT))
    git_files = subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', SOURCE_COMMIT, '--', relative_folder], cwd=ROOT, text=True).splitlines()
    local_files = sorted(str(path.relative_to(ROOT)) for path in folder.rglob('*') if path.is_file())
    assert sorted(git_files) == local_files and len(git_files) == 104
    for filename in git_files:
        assert subprocess.check_output(['git', 'show', f'{SOURCE_COMMIT}:{filename}'], cwd=ROOT) == (ROOT / filename).read_bytes()
    old_by_pair = {pair(r): r for r in old['rows']}
    prior_by_pair = {pair(r): r for r in prior['rows']}
    for row in old['rows']:
        docs = [KnowledgeDoc(d['id'], d['title'], d['body'], d['source']) for d in row['context']['documents']]
        legacy = validate_explanation(row['model_answer'], docs, row['context']['query'])
        runtime = validate_runtime_explanation(row['model_answer'], docs, row['context']['query'], engine)
        assert legacy == row['assessment']['validated']
        assert runtime == prior_by_pair[pair(row)]['runtime_answer']
    paired = [r for r in current['rows'] if pair(r) in old_by_pair]
    additional = [r for r in current['rows'] if pair(r) not in old_by_pair]
    assert len(paired) == len(additional) == 24
    assert all(r['comparison_group'] == 'paired_v3' for r in paired)
    assert all(r['comparison_group'] == 'additional_development' for r in additional)
    assert summary(current['rows'], cases) == current['summary']
    assert summary(paired, cases) == current['paired_summary']
    assert summary(additional, cases) == current['additional_summary']
    assert summary(old['rows'], cases) == old['summary']
    comparisons = []
    for index, row in enumerate(current['rows']):
        previous = old_by_pair.get(pair(row)); effect = row['assessment']['patch_effect']
        comparisons.append({
            'case_id': row['case_id'], 'condition': row['condition'], 'query': row['context']['query'],
            'comparison_group': row['comparison_group'], 'response_id': row['generation']['response_id'],
            'source_pointer': f'/rows/{index}', 'raw_status': row['model_answer']['status'],
            'raw_family': row['model_answer']['family'], 'raw_patches': row['model_answer']['patches'],
            'validated_status': row['assessment']['validated_status'],
            'validation_error': row['assessment']['validation_error'],
            'citation_checks': citation_checks(row),
            'appropriate_abstention_contract': row['assessment']['appropriate_abstention_contract'],
            'family_label_match': row['assessment']['family_label_match'],
            'gate': effect.get('gate'),
            'regressions': {k: effect.get(k, {}).get('summary', {}).get('decreases', []) for k in ['development_16', 'original_36']},
            'previous_primary_status': previous['assessment']['validated_status'] if previous else None,
            'previous_runtime_status': prior_by_pair[pair(row)]['runtime_status'] if previous else None,
            'previous_response_id': previous['generation']['response_id'] if previous else None,
            'previous_primary_effect': previous['assessment']['patch_effect'] if previous else None,
        })
    transitions = Counter(f"{old_by_pair[pair(r)]['assessment']['validated_status']} -> {r['assessment']['validated_status']}" for r in paired)
    report = {'method': 'free post-run evidence verification and descriptive development comparison; primary records unchanged',
        'new_model_calls_in_analysis': 0, 'source_commit': SOURCE_COMMIT, 'source_sha256': source_hashes,
        'script_sha256': sha(Path(__file__)),
        'verification': {'all_checks_passed': True, 'original_git_files_identical': 104,
            'prepared_rows_verified': 48, 'http_envelopes_verified': 48,
            'unique_new_response_ids': len(seen), 'fresh_assessments_equal_recorded': 48,
            'old_primary_and_runtime_validators_reproduced': 24, 'budget_ledgers_verified': 2,
            'source_inputs_unchanged': all(sha(PATHS[k]) == value for k, value in source_hashes.items())},
        'usage': dict(usage), 'estimated_usd': str(total_cost), 'reserved_usd': current['reserved_usd'],
        'cost_by_group_usd': {scope: str(sum((Decimal(str(r['generation']['estimated_usd'])) for r in rows), Decimal('0')))
            for scope, rows in [('paired', paired), ('additional', additional), ('previous_paired', old['rows'])]},
        'api_latency_ms': {'min': min(latencies), 'median': statistics.median(latencies),
            'mean': round(statistics.mean(latencies), 2), 'max': max(latencies)},
        'summary': current['summary'], 'paired_summary': current['paired_summary'],
        'additional_summary': current['additional_summary'], 'previous_primary_summary': old['summary'],
        'previous_runtime_summary': prior['summary'],
        'primary_status_transitions_paired': dict(transitions),
        'validation_errors': {scope: dict(Counter(r['assessment']['validation_error'] for r in rows if r['assessment']['validation_error']))
            for scope, rows in [('all', current['rows']), ('paired', paired), ('additional', additional)]},
        'citation_counts': {scope: citation_counts(rows) for scope, rows in
            [('all', current['rows']), ('paired', paired), ('additional', additional), ('previous_paired', old['rows'])]},
        'effects': {'all': effects(current['rows']), 'paired': effects(paired), 'additional': effects(additional),
            'previous_primary': effects(old['rows']), 'previous_runtime': prior['summary']},
        'human_review': 'pending_independent_human_review', 'rows': comparisons}
    (HERE / 'analysis.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({key: report[key] for key in ['verification', 'usage', 'estimated_usd', 'api_latency_ms', 'citation_counts', 'effects']}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
