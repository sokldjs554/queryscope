"""Free static projection of completed v4 responses; no provider or gate runs."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

from searchclinic.rag.explanation import source_quote


def _citations(answer, context):
    sources = {d['id']: d for d in context.get('documents', [])}
    checks = []
    for evidence in (answer or {}).get('evidence', []):
        check = {**evidence, 'status': 'unknown_evidence_source'}
        if evidence.get('doc_id') in sources:
            try:
                matched, changed = source_quote(evidence['quote'], sources[evidence['doc_id']]['body'])
                check.update(status='verified', matched_source=matched, display_format_recovered=changed)
            except (ValueError, TypeError, KeyError):
                check['status'] = 'text_mismatch'
        checks.append(check)
    return checks


def _row(original):
    context = original['context']
    generation = original.get('generation', {})
    capture = original.get('http_response', {})
    return {'case_id': original['case_id'], 'condition': original['condition'],
            'context': context, 'answer': original.get('model_answer'),
            'generation_status': original['generation_status'],
            'assessment_status': original.get('assessment_status'),
            'assessment': original.get('assessment'),
            'response_id': generation.get('response_id', capture.get('response_id')),
            'requested_model': original.get('requested_model'),
            'observed_model': original.get('observed_model', capture.get('observed_model', generation.get('model'))),
            'error': original.get('error') or original.get('provenance_error') or original.get('evaluation_error'),
            'citation_checks': _citations(original.get('model_answer'), context),
            'estimated_usd': capture.get('estimated_usd'), 'http_response': capture,
            'context_sha256': original.get('context_sha256'), 'payload_sha256': original.get('payload_sha256')}


def _counts(rows):
    assessments = [r['assessment'] for r in rows if r.get('assessment')]
    effects = [a['patch_effect'] for a in assessments if a.get('patch_effect', {}).get('status') == 'measured']
    return {'rows': len(rows), 'api_errors': sum(r['generation_status'] == 'api_error' for r in rows),
            'provenance_errors': sum(r['generation_status'] == 'provenance_error' for r in rows),
            'assessed': len(assessments),
            **{status: sum(a['validated_status'] == status for a in assessments)
               for status in ['supported', 'abstain', 'invalid']},
            'gate_measured': len(effects), 'gate_accepted': sum(e['gate']['accepted'] for e in effects),
            'gate_rejected': sum(not e['gate']['accepted'] for e in effects),
            'abstention_eligible': sum(a.get('appropriate_abstention_contract') is not None for a in assessments),
            'abstention_contract_pass': sum(a.get('appropriate_abstention_contract') is True for a in assessments),
            'wrong_patch_on_abstain_required': sum(a.get('wrong_patch_on_abstain_required') is True for a in assessments)}


def _summary(rows):
    return {'all': _counts(rows), **{c: _counts([r for r in rows if r['condition'] == c])
                                   for c in ['no_hint', 'hint']}}


def project_runtime_results(report, previous, cases):
    """Preserve all 48 slots, including API errors, without changing source data."""
    if report.get('mode') != 'actual_api' or report.get('suite') != 'queryscope-v4-runtime':
        raise ValueError('actual_v4_runtime_results_required')
    if not report.get('complete') or len(report.get('rows', [])) != 48:
        raise ValueError('complete_48_slot_results_required')
    rows = report['rows']
    old = {(r['case_id'], r['condition']): r for r in previous['rows']}
    expected = {(c['id'], condition) for c in cases for condition in ['no_hint', 'hint']}
    keys = [(r['case_id'], r['condition']) for r in rows]
    if len(old) != 24 or len(keys) != len(set(keys)) or set(keys) != expected:
        raise ValueError('case_condition_set_mismatch')
    for row in rows:
        key = row['case_id'], row['condition']
        expected_group = 'paired_v3' if key in old else 'additional_development'
        if row['comparison_group'] != expected_group:
            raise ValueError('comparison_group_mismatch')
    groups = {g: [r for r in rows if r['comparison_group'] == g]
              for g in ['paired_v3', 'additional_development']}
    if any(len(items) != 24 for items in groups.values()):
        raise ValueError('comparison_group_size_mismatch')
    indexed = {(r['case_id'], r['condition']): r for r in rows}
    pairs = []
    for case in cases:
        conditions = {}
        for condition in ['no_hint', 'hint']:
            key = case['id'], condition
            projected = _row(indexed[key])
            projected['previous'] = _row(old[key]) if key in old else None
            conditions[condition] = projected
        pairs.append({'id': case['id'], 'query': case['query'], 'category': case['category'],
                      'family_hypothesis': case.get('family_hypothesis'),
                      'comparison_group': indexed[(case['id'], 'no_hint')]['comparison_group'],
                      'conditions': conditions})
    captures = [r['http_response'] for r in rows if r.get('http_response')]
    estimates = [c['estimated_usd'] for c in captures if c.get('estimated_usd') is not None]
    known_estimate = round(sum(estimates), 8)
    if known_estimate != report['estimated_usd']:
        raise ValueError('cost_projection_mismatch')
    projected_rows = [row for pair in pairs for row in pair['conditions'].values()]
    quotes = [quote for row in projected_rows for quote in row['citation_checks']]
    citation_summary = {
        'quotes_checked': len(quotes),
        'verified_quotes': sum(q['status'] == 'verified' for q in quotes),
        'untraceable_quotes': sum(q['status'] != 'verified' for q in quotes),
        'responses_with_untraceable_quotes': sum(
            any(q['status'] != 'verified' for q in row['citation_checks']) for row in projected_rows),
        'first_citation_blocked_responses': sum(
            (r.get('assessment') or {}).get('validation_error') == 'citation_source_or_text' for r in rows),
        'scope': 'all_raw_quotes_independent_of_first_validation_failure_not_semantic_support',
    }
    data = {'format_version': 1, 'mode': 'static_actual_response_replay', 'new_api_calls': 0,
            'suite': report['suite'], 'model': report['model'], 'complete': report['complete'],
            'attempts': report['attempts'], 'responses': report['responses'], 'api_errors': report['errors'],
            'provenance_errors': report.get('provenance_errors', 0),
            'semantic_review': report['semantic_review'],
            'cost': {'known_estimate_usd': known_estimate, 'estimate_complete': report['cost_estimate_complete'],
                     'captured_http_responses': len(captures), 'responses_with_usage_estimate': len(estimates),
                     'reserved_usd': report['reserved_usd'], 'scope': 'captured_http_usage_not_invoice'},
            'groups': {g: _summary(items) for g, items in groups.items()},
            'summary': _summary(rows), 'previous_summary': _summary(previous['rows']), 'pairs': pairs,
            'citation_summary': citation_summary,
            'prepared_sha256': report.get('prepared_sha256'),
            'canonical_campaign_sha256': report.get('canonical_campaign_sha256')}
    return copy.deepcopy(data)


def export_runtime_results(source, previous_source, cases_source, output):
    sources = [Path(p) for p in [source, previous_source, cases_source]]
    output = Path(output)
    if output.resolve() in {p.resolve() for p in sources}:
        raise ValueError('source_and_export_must_differ')
    raw = [p.read_bytes() for p in sources]
    data = project_runtime_results(*(json.loads(content) for content in raw))
    data['source_sha256'] = hashlib.sha256(raw[0]).hexdigest()
    data['previous_source_sha256'] = hashlib.sha256(raw[1]).hexdigest()
    data['cases_source_sha256'] = hashlib.sha256(raw[2]).hexdigest()
    output.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return data
