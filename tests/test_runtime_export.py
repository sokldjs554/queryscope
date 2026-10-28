"""Static exports preserve every outcome and never generate a model response."""
import copy
import json
from pathlib import Path
import subprocess
import sys

import pytest


def fixture_reports():
    cases = [{'id': f'T{i:02}', 'query': f'질의{i}', 'category': 'candidate_failure',
              'family_hypothesis': 'synonym_gap'} for i in range(1, 25)]
    rows = []
    for case in cases:
        for condition in ['no_hint', 'hint']:
            context = {'query': case['query'], 'problem': '실제 입력', 'analysis': {'tokens': []},
                       'search': {'total': 0, 'results': []},
                       'documents': [{'id': 'KX', 'title': '원칙', 'body': '원문에서 추적 가능한 인용입니다.', 'source': 'test'}]}
            answer = {'status': 'supported', 'family': 'synonym_gap', 'summary': case['query'] + ' 원응답',
                      'evidence': [{'doc_id': 'KX', 'quote': '원문에서 추적 가능한 인용입니다.'}], 'patches': []}
            assessment = {'validated_status': 'supported', 'validation_error': None,
                          'patch_effect': {'status': 'not_run'}}
            rows.append({'case_id': case['id'], 'condition': condition,
                         'comparison_group': 'paired_v3' if int(case['id'][1:]) <= 12 else 'additional_development',
                         'context': context, 'generation_status': 'completed', 'model_answer': answer,
                         'generation': {'response_id': f"resp_{case['id']}_{condition}", 'model': 'fixed-model'},
                         'http_response': {'estimated_usd': .001, 'usage': {'input_tokens': 100}, 'http_status': 200},
                         'assessment': assessment})
    previous = {'rows': copy.deepcopy(rows[:24]), 'summary': {}}
    report = {'mode': 'actual_api', 'suite': 'queryscope-v4-runtime', 'complete': True,
              'model': 'fixed-model', 'attempts': 48, 'responses': 48, 'errors': 0,
              'estimated_usd': .048, 'reserved_usd': .6, 'cost_estimate_complete': True,
              'raw_responses_received': 48, 'provenance_errors': 0,
              'prepared_sha256': 'prepared', 'canonical_campaign_sha256': 'campaign',
              'semantic_review': 'pending_independent_human_review', 'rows': rows}
    return report, previous, cases


def test_all48_are_grouped_and_old24_remain_distinct():
    from searchclinic.evaluation.runtime_export import project_runtime_results
    report, previous, cases = fixture_reports()
    before = copy.deepcopy((report, previous))
    data = project_runtime_results(report, previous, cases)
    assert len(data['pairs']) == 24
    assert data['groups']['paired_v3']['all']['rows'] == 24
    assert data['groups']['additional_development']['all']['rows'] == 24
    assert len([r for p in data['pairs'] for r in p['conditions'].values() if r['previous']]) == 24
    assert data['pairs'][0]['conditions']['no_hint']['answer'] == report['rows'][0]['model_answer']
    assert data['pairs'][0]['conditions']['no_hint']['previous']['answer'] == previous['rows'][0]['model_answer']
    assert (report, previous) == before


def test_api_error_retains_slot_and_missing_cost_is_not_zero_or_complete():
    from searchclinic.evaluation.runtime_export import project_runtime_results
    report, previous, cases = fixture_reports()
    row = report['rows'][-1]
    row.update(generation_status='api_error', model_answer=None, error='transport_failed')
    for key in ['assessment', 'generation', 'http_response']:
        row.pop(key)
    report.update(responses=47, errors=1, raw_responses_received=47,
                  estimated_usd=.047, cost_estimate_complete=False)
    data = project_runtime_results(report, previous, cases)
    exported = data['pairs'][-1]['conditions']['hint']
    assert exported['answer'] is None and exported['error'] == 'transport_failed'
    assert exported['estimated_usd'] is None
    assert data['groups']['additional_development']['all']['api_errors'] == 1
    assert data['cost']['estimate_complete'] is False
    assert data['cost']['known_estimate_usd'] == .047
    assert data['cost']['captured_http_responses'] == 47


def test_citation_trace_and_every_gate_scope_survive_projection():
    from searchclinic.evaluation.runtime_export import project_runtime_results
    report, previous, cases = fixture_reports()
    row = report['rows'][0]
    row['model_answer']['evidence'] += [{'doc_id': 'PRODUCT', 'quote': '상품은 운영 지식 출처가 아닙니다.'},
                                      {'doc_id': 'KX', 'quote': '원문과 다른 문장입니다.'}]
    row['assessment']['patch_effect'] = {'status': 'measured', 'gate': {'accepted': False, 'reason': 'regression'},
        'development_16': {'summary': {'decreases': [{'query': '회귀', 'before': 1, 'after': 0}]}},
        'original_36': {'summary': {'decreases': []}}}
    data = project_runtime_results(report, previous, cases)
    exported = data['pairs'][0]['conditions']['no_hint']
    assert [q['status'] for q in exported['citation_checks']] == ['verified', 'unknown_evidence_source', 'text_mismatch']
    assert exported['assessment']['patch_effect'] == row['assessment']['patch_effect']
    assert data['groups']['paired_v3']['all']['gate_rejected'] == 1


@pytest.mark.parametrize('change', ['incomplete', 'duplicate', 'missing', 'group'])
def test_incomplete_or_misgrouped_results_fail_closed(change):
    from searchclinic.evaluation.runtime_export import project_runtime_results
    report, previous, cases = fixture_reports()
    if change == 'incomplete': report['complete'] = False
    if change == 'duplicate': report['rows'][-1] = report['rows'][0]
    if change == 'missing': report['rows'].pop()
    if change == 'group': report['rows'][0]['comparison_group'] = 'additional_development'
    with pytest.raises(ValueError): project_runtime_results(report, previous, cases)


def test_free_export_cli_preserves_sources_and_rejects_overwrite(tmp_path):
    report, previous, cases = fixture_reports()
    paths = [tmp_path / name for name in ['results.json', 'previous.json', 'cases.json']]
    for path, data in zip(paths, [report, previous, cases]): path.write_text(json.dumps(data), encoding='utf-8')
    before = [p.read_bytes() for p in paths]
    output = tmp_path / 'export.json'
    script = Path(__file__).resolve().parents[1] / 'scripts/export_generation_v4.py'
    args = [sys.executable, str(script), '--input', str(paths[0]), '--previous', str(paths[1]),
            '--cases', str(paths[2]), '--output', str(output)]
    result = subprocess.run(args, text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
    assert json.loads(output.read_text(encoding='utf-8'))['new_api_calls'] == 0
    assert [p.read_bytes() for p in paths] == before
    assert subprocess.run(args[:-1] + [str(paths[0])], capture_output=True).returncode != 0
    assert [p.read_bytes() for p in paths] == before


def test_raw_quote_failures_are_counted_even_when_schema_blocks_first():
    from searchclinic.evaluation.runtime_export import project_runtime_results
    report, previous, cases = fixture_reports()
    report['rows'][0]['assessment'].update(validated_status='invalid', validation_error='output_schema')
    report['rows'][0]['model_answer']['evidence'][0]['quote'] = '元の引用と異なる文言です。'
    data = project_runtime_results(report, previous, cases)
    summary = data['citation_summary']
    assert summary['quotes_checked'] == 48
    assert summary['verified_quotes'] == 47
    assert summary['untraceable_quotes'] == 1
    assert summary['responses_with_untraceable_quotes'] == 1
    assert summary['first_citation_blocked_responses'] == 0
