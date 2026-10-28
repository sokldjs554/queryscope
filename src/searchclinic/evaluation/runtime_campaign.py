"""Separately approved, once-only runtime evaluation; preparation never uses a key.

Historical campaign code and its 24-call budget remain unchanged. One canonical
48-input campaign owns two fixed 24-call ledgers, with no retry or resume.
"""
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path

from searchclinic.corpus import load_catalog, load_evalset
from searchclinic.corpus.evalset import EvalQuery
from searchclinic.evaluation.llm_campaign import campaign_bundle, campaign_engine, summarize
from searchclinic.evaluation.queryscope_v2 import ROOT, compare_ranking, json_sha, write_json
from searchclinic.index.engine import SearchEngine
from searchclinic.patch.gate import run_gate
from searchclinic.patch.ir import Prescription
from searchclinic.rag.knowledge import KnowledgeDoc
from searchclinic.rag.runtime_contract import RUNTIME_CONTRACT_VERSION, validate_runtime_explanation

SUITE = 'queryscope-v4-runtime'
MODEL = 'gpt-5.4-mini-2026-03-17'
MAX_CALLS = 48
MAX_USD = .60
DEFAULT_AUDIT = ROOT / 'docs/verification/queryscope-v4/run-v1/audit.json'
SOURCE_SHA256 = 'd8e71f108982b6d67b3ff0279ba8cbd302d15f5c86b2c0b48a81c67d6711e370'
CAMPAIGN_STATE_ROOT = ROOT / 'work/runtime-llm-campaigns'


def _read_json(path):
    raw = Path(path).read_bytes()
    try:
        data = json.loads(raw)
    except (ValueError, TypeError) as error:
        raise ValueError('invalid_json_input') from error
    if not isinstance(data, dict):
        raise ValueError('invalid_json_object')
    return data, hashlib.sha256(raw).hexdigest()


def _source(source=DEFAULT_AUDIT):
    audit, source_sha = _read_json(source)
    if source_sha != SOURCE_SHA256:
        raise ValueError('source_audit_changed')
    return audit


def _canonical(data):
    return json_sha({'suite': data['suite'], 'model': data['model'],
                     'source_sha256': data['source_sha256'],
                     'ordered_payload_sha256': [r['payload_sha256'] for r in data['requests']]})


def prepare_runtime_campaign(output, source=DEFAULT_AUDIT):
    """Freeze the audited 48 inputs and write a disabled approval template."""
    from searchclinic.rag.openai_provider import request_payload
    output = Path(output)
    if output.exists():
        raise FileExistsError(output)
    audit = _source(source)
    bundle = campaign_bundle('queryscope-v3')
    rows = []
    for original in audit['context_preparation']['rows']:
        row = dict(original)
        row.update(context_sha256=json_sha(row['context']), payload=request_payload(row['context']))
        rows.append(row)
    data = {'created_at': datetime.now(timezone.utc).isoformat(), 'mode': 'dry_run',
            'suite': SUITE, 'new_api_calls': 0, 'model': MODEL,
            'calls_if_approved': MAX_CALLS, 'reservation_usd': MAX_USD,
            'source_sha256': SOURCE_SHA256, 'frozen_manifest': bundle['manifest'],
            'requests': rows}
    data['canonical_campaign_sha256'] = _canonical(data)
    _validate_data(data, audit, bundle)
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / 'requests.json', data)
    prepared_sha = hashlib.sha256((output / 'requests.json').read_bytes()).hexdigest()
    write_json(output / 'approval-template.json', {
        'approved': False, 'approved_by': None, 'suite': SUITE, 'model': MODEL,
        'calls': MAX_CALLS, 'max_usd': MAX_USD, 'prepared_sha256': prepared_sha,
        'canonical_campaign_sha256': data['canonical_campaign_sha256']})
    return data


def _validate_data(data, audit, bundle):
    from searchclinic.rag.openai_provider import MAX_REQUEST_BYTES, RESERVATION_USD, request_payload
    if round(MAX_CALLS * RESERVATION_USD, 6) != MAX_USD:
        raise ValueError('provider_budget_reservation_changed')
    try:
        if (data['mode'] != 'dry_run' or data['suite'] != SUITE or data['model'] != MODEL or
                data['calls_if_approved'] != MAX_CALLS or data['reservation_usd'] != MAX_USD or
                data['new_api_calls'] != 0):
            raise ValueError('preparation_identity_or_budget_mismatch')
        if data['source_sha256'] != SOURCE_SHA256 or data['frozen_manifest'] != bundle['manifest']:
            raise ValueError('preparation_source_mismatch')
        expected = audit['context_preparation']['rows']
        rows = data['requests']
        pairs = [(r['case_id'], r['condition']) for r in rows]
        if (len(rows) != MAX_CALLS or len(set(pairs)) != MAX_CALLS or
                pairs != [(r['case_id'], r['condition']) for r in expected]):
            raise ValueError('preparation_cases_changed')
        for row, original in zip(rows, expected):
            if (row['context'] != original['context'] or row['full_context'] != original['full_context'] or
                    row['query'] != original['query'] or
                    row['context_sha256'] != json_sha(row['context']) or
                    row['context']['runtime_contract']['version'] != RUNTIME_CONTRACT_VERSION):
                raise ValueError('preparation_context_changed')
            payload = request_payload(row['context'])
            size = len(json.dumps(payload, ensure_ascii=False).encode('utf-8'))
            if (row['payload'] != payload or row['payload_sha256'] != json_sha(payload) or
                    row['payload_sha256'] != original['payload_sha256'] or
                    row['payload_bytes'] != size or size > MAX_REQUEST_BYTES or
                    not row['within_request_limit']):
                raise ValueError('preparation_payload_changed')
            if row['model_answer'] is not None or row['generation_status'] != 'not_run':
                raise ValueError('preparation_already_generated')
        if data['canonical_campaign_sha256'] != _canonical(data):
            raise ValueError('preparation_canonical_mismatch')
    except (KeyError, TypeError, AttributeError) as error:
        raise ValueError('preparation_structure_invalid') from error


def validate_runtime_preparation(prepared_dir):
    """Read once and validate, without key lookup, claim, or provider creation.

    prepared_sha256 is computed metadata in the return value, never a field in
    the saved preparation (which would make its own hash self-referential).
    """
    data, prepared_sha = _read_json(Path(prepared_dir) / 'requests.json')
    _validate_data(data, _source(), campaign_bundle('queryscope-v3'))
    return {**data, 'prepared_sha256': prepared_sha}


def _approval(data, approval_path):
    if not approval_path:
        raise ValueError('approval_required')
    approval, approval_sha = _read_json(approval_path)
    if (approval.get('approved') is not True or not isinstance(approval.get('approved_by'), str) or
            not approval['approved_by'].strip()):
        raise ValueError('approval_required')
    if approval.get('prepared_sha256') != data['prepared_sha256']:
        raise ValueError('approval_preparation_mismatch')
    if (approval.get('suite') != SUITE or approval.get('model') != MODEL or
            approval.get('calls') != MAX_CALLS or approval.get('max_usd') != MAX_USD or
            approval.get('canonical_campaign_sha256') != data['canonical_campaign_sha256']):
        raise ValueError('approval_identity_or_budget_mismatch')
    return {**approval, 'canonical_campaign_sha256': data['canonical_campaign_sha256'],
            'prepared_sha256': data['prepared_sha256'], 'approval_sha256': approval_sha}


def check_runtime_approval(prepared_dir, approval_path):
    """Return the verified approval and its canonical remote/local claim identity."""
    return _approval(validate_runtime_preparation(prepared_dir), approval_path)


def assess_runtime_generation(raw, context, case, engine, evalset):
    """Runtime eligibility precedes every gate; semantic judgment stays pending."""
    docs = [KnowledgeDoc(d['id'], d['title'], d['body'], d['source']) for d in context['documents']]
    validated = validate_runtime_explanation(raw, docs, case['query'], engine)
    raw = raw if isinstance(raw, dict) else {}
    needs_abstain = case['expected_action'] == 'abstain_no_patch'
    valid = validated['status'] != 'invalid'
    assessment = {
        'raw_status': raw.get('status'), 'raw_family': raw.get('family'),
        'validated_status': validated['status'], 'validation_error': validated['validation_error'],
        'cause_reference_status': case.get('reference_status', 'authored_reference'),
        'family_label_match': raw.get('family') == case['expected_family'] if case['expected_family'] else None,
        'appropriate_abstention_contract': (valid and raw.get('status') == 'abstain' and not raw.get('patches')) if needs_abstain else None,
        'wrong_patch_on_abstain_required': bool(raw.get('patches')) if needs_abstain else None,
        'raw_patch_attempted': bool(raw.get('patches')),
        'citation_trace': validated['assessment']['citation_trace'],
        'semantic_support': 'requires_independent_human_review',
        'patch_structure': validated['assessment']['patch_structure'],
        'patch_effect': {'status': 'not_run'}, 'validated': validated,
    }
    if validated['prescription'] and case['qrels']:
        candidate = Prescription.model_validate(validated['prescription'])
        gate, sandbox = run_gate(engine, evalset, candidate)
        development = [{'query': q.query, 'qrels': q.qrels} for q in evalset]
        original = [{'query': q.query, 'qrels': q.qrels} for q in load_evalset()]
        original_engine = SearchEngine(load_catalog())
        assessment['patch_effect'] = {
            'status': 'measured', 'gate': asdict(gate),
            'development_16': compare_ranking(engine, sandbox, development),
            'original_36': compare_ranking(original_engine,
                original_engine.with_config(candidate.apply_to(original_engine.config)), original),
        }
    return assessment


def _summaries(report):
    report['summary'] = summarize(report['rows'])
    report['paired_summary'] = summarize([r for r in report['rows'] if r['comparison_group'] == 'paired_v3'])
    report['additional_summary'] = summarize([r for r in report['rows'] if r['comparison_group'] == 'additional_development'])
    report['provenance_errors'] = sum(r['generation_status'] == 'provenance_error' for r in report['rows'])
    captures = [r['http_response'] for r in report['rows'] if r.get('http_response')]
    report['raw_responses_received'] = len(captures)
    report['estimated_usd'] = round(sum(c['estimated_usd'] for c in captures
                                        if c['estimated_usd'] is not None), 8)
    report['cost_estimate_complete'] = (len(captures) == report['attempts'] and
                                      all(c['estimated_usd'] is not None for c in captures))


def execute_runtime_campaign(prepared_dir, output, approval_path):
    """Execute a new explicit approval once; errors never authorize a retry."""
    from searchclinic.rag.openai_provider import Budget, OpenAIExplainer, ProviderError, RESERVATION_USD
    from searchclinic.evaluation.runtime_campaign_io import (
        acquire_remote_claim, RecordingClient, verify_generation_provenance, redact_secret,
    )
    # These are the only preparation/approval reads. Use these verified objects
    # throughout; later file replacements cannot change transmitted inputs.
    data = validate_runtime_preparation(prepared_dir)
    approval = _approval(data, approval_path)
    output = Path(output)
    if output.exists():
        raise FileExistsError(output)
    key = os.environ.get('OPENAI_API_KEY')
    if not key:
        raise ValueError('provider_not_configured')
    bundle = campaign_bundle('queryscope-v3')
    engine = campaign_engine(bundle)
    evalset = [EvalQuery(c['query'], c['qrels']) for c in bundle['cases'] if c['qrels']]
    state = CAMPAIGN_STATE_ROOT / data['canonical_campaign_sha256']
    if state.exists():
        raise ValueError('campaign_already_claimed')
    # Mandatory inside the spending entry point, including direct CLI use.
    # A fresh checkout still meets the same atomic remote claim and cannot spend
    # again. A receipt or an existing tag alone never authorizes a later run.
    remote_claim = acquire_remote_claim(data['canonical_campaign_sha256'])
    CAMPAIGN_STATE_ROOT.mkdir(parents=True, exist_ok=True)
    try:
        state.mkdir(exist_ok=False)
    except FileExistsError:
        raise ValueError('campaign_already_claimed') from None
    write_json(state / 'execution-claim.json', {
        'canonical_campaign_sha256': data['canonical_campaign_sha256'],
        'prepared_sha256': data['prepared_sha256'], 'approval_sha256': approval['approval_sha256'],
        'output': str(output.resolve()), 'suite': SUITE})
    write_json(state / 'remote-claim.json', remote_claim)
    output.mkdir(parents=True, exist_ok=False)
    budgets = [Budget(state / f'budget-{i}.json', max_calls=24) for i in range(2)]
    recorder = RecordingClient(output, key)
    providers = [OpenAIExplainer(key, budget=budget, client=recorder) for budget in budgets]
    seen_ids = {r['response_id'] for r in _source()['rows']}
    paid_ids = set(bundle['rubric']['paid_case_ids'])
    cases = {c['id']: c for c in bundle['cases']}
    report = {'mode': 'actual_api', 'suite': SUITE, 'model': MODEL,
        'prepared_sha256': data['prepared_sha256'], 'approval_sha256': approval['approval_sha256'],
        'canonical_campaign_sha256': data['canonical_campaign_sha256'],
        'source_sha256': SOURCE_SHA256, 'campaign_state_path': str(state.resolve()),
        'complete': False, 'attempts': 0, 'responses': 0, 'errors': 0,
        'estimated_usd': 0, 'reserved_usd': 0,
        'semantic_review': 'pending_independent_human_review',
        'comparison_scope': {'paired_v3_case_ids': sorted(paid_ids),
                             'all_planned': 48, 'paired_planned': 24, 'additional_planned': 24},
        'rows': []}
    _summaries(report)
    write_json(output / 'results.json', report)
    for index, request in enumerate(data['requests']):
        row = {'case_id': request['case_id'], 'condition': request['condition'],
            'comparison_group': 'paired_v3' if request['case_id'] in paid_ids else 'additional_development',
            'context': request['context'], 'context_sha256': request['context_sha256'],
            'payload_sha256': request['payload_sha256'],
            'generation_status': 'pending', 'model_answer': None}
        report['rows'].append(row)
        write_json(output / 'results.json', report)
        recorder.begin(index, request['case_id'], request['condition'], request['payload'])
        try:
            try:
                generated = providers[index // 24].generate(request['context'])
            except ProviderError as error:
                row.update(generation_status='api_error', error=str(error))
                report['errors'] += 1
            else:
                stored = redact_secret(generated, key)
                observed_model = (recorder.envelope or {}).get('model')
                stored['model'] = observed_model
                row.update(generation=stored, model_answer=stored['raw'],
                           requested_model=MODEL, observed_model=observed_model,
                           generation_status='received', assessment_status='not_run')
                # Preserve parsed output before provenance checks or scoring.
                write_json(output / 'results.json', report)
                try:
                    verify_generation_provenance(generated, recorder, MODEL, seen_ids)
                except RuntimeError as error:
                    row.update(generation_status='provenance_error', provenance_error=str(error))
                    raise
                row.update(generation_status='completed', assessment_status='pending')
                report['responses'] += 1
                write_json(output / 'results.json', report)
                try:
                    row['assessment'] = assess_runtime_generation(generated['raw'], request['context'],
                        cases[request['case_id']], engine, evalset)
                    row['assessment_status'] = 'completed'
                except Exception as error:
                    row.update(assessment_status='error', evaluation_error=type(error).__name__)
                    raise
        finally:
            if recorder.metadata is not None:
                row['http_response'] = recorder.metadata
            report['attempts'] = sum(budget.calls for budget in budgets)
            report['reserved_usd'] = round(report['attempts'] * RESERVATION_USD, 6)
            for index_budget, budget in enumerate(budgets):
                if budget.path.exists():
                    receipt = json.loads(budget.path.read_text(encoding='utf-8'))
                    write_json(output / f'budget-{index_budget}-receipt.json', receipt)
            _summaries(report)
            write_json(output / 'results.json', report)
    report['complete'] = True
    write_json(output / 'results.json', report)
    return report
