"""Offline, retrospective runtime audit. No model provider is constructed.

Original responses and primary verdicts are immutable inputs. Updated contexts
are preparation artifacts, never responses or new-model effectiveness evidence.
"""
from __future__ import annotations
from collections import Counter
from dataclasses import asdict
import json
from pathlib import Path

from searchclinic.corpus import load_catalog, load_evalset
from searchclinic.corpus.evalset import EvalQuery
from searchclinic.index.engine import SearchEngine
from searchclinic.patch.gate import run_gate
from searchclinic.patch.ir import Prescription
from searchclinic.rag.knowledge import KnowledgeDoc
from searchclinic.rag.runtime_contract import validate_runtime_explanation, build_runtime_context
from searchclinic.evaluation.llm_campaign import campaign_bundle, campaign_engine, summarize
from searchclinic.evaluation.queryscope_v2 import ROOT, file_sha, json_sha, write_json, compare_ranking


def verify_actual_lineage(actual, source):
    """Bind this retrospective audit to the frozen campaign and saved response bytes."""
    folder = ROOT / 'docs/verification/queryscope-v3'
    prepared_path = folder / 'llm-prepared-v1/requests.json'
    prepared = json.loads(prepared_path.read_text(encoding='utf-8'))
    reference = json.loads((folder / 'actual-api-human-review.json').read_text(encoding='utf-8'))
    try:
        if actual['prepared_sha256'] != file_sha(prepared_path):
            raise ValueError('evidence_preparation_mismatch')
        expected = {(r['case_id'], r['condition']): r for r in prepared['requests']}
        pairs = [(r['case_id'], r['condition']) for r in actual['rows']]
        if len(set(pairs)) != 24 or set(pairs) != set(expected):
            raise ValueError('evidence_case_pairs_mismatch')
        response_ids = []
        for row in actual['rows']:
            request = expected[(row['case_id'], row['condition'])]
            if (row['context_sha256'] != json_sha(row['context']) or
                    row['context'] != request['context']):
                raise ValueError('evidence_context_mismatch')
            if row['generation_status'] != 'completed' or row['model_answer'] != row['generation']['raw']:
                raise ValueError('evidence_raw_answer_mismatch')
            if row['generation']['model'] != prepared['model']:
                raise ValueError('evidence_model_mismatch')
            response_ids.append(row['generation']['response_id'])
        if not all(response_ids) or len(set(response_ids)) != 24:
            raise ValueError('evidence_response_ids_mismatch')
        if file_sha(source) != reference['actual_results_sha256']:
            raise ValueError('evidence_source_bytes_mismatch')
    except (KeyError, TypeError) as error:
        raise ValueError('evidence_structure_invalid') from error


def prepare_runtime_contexts(bundle, engine):
    from searchclinic.rag.runtime_retrieval import build_runtime_retrieval_context
    from searchclinic.rag.observations import build_context
    from searchclinic.rag.retriever import KnowledgeRetriever
    from searchclinic.rag.openai_provider import request_payload, MAX_REQUEST_BYTES
    retriever = KnowledgeRetriever()
    rows = []
    relevant = bundle['rubric']['retrieval']['relevant_ids']
    for case in bundle['cases']:
        for condition in ['no_hint', 'hint']:
            full, docs = build_runtime_retrieval_context(engine, retriever, case['query'], case['problem_' + condition])
            prior, _ = build_context(engine, retriever, case['query'], case['problem_' + condition])
            if not case.get('documents_available', True):
                full['documents'] = []; docs = []; prior['documents'] = []
            transmitted = build_runtime_context(full, docs)
            payload = request_payload(transmitted)
            payload_bytes = len(json.dumps(payload, ensure_ascii=False).encode('utf-8'))
            family_ids = relevant.get(case.get('family_hypothesis'), [])
            ids = [d.doc_id for d in docs]
            previous_ids = [d['id'] for d in prior['documents']]
            rows.append({'case_id': case['id'], 'condition': condition, 'query': case['query'],
                         'context': transmitted, 'full_context': full, 'payload_sha256': json_sha(payload),
                         'payload_bytes': payload_bytes, 'within_request_limit': payload_bytes <= MAX_REQUEST_BYTES,
                         'prior_document_ids': previous_ids, 'runtime_document_ids': ids,
                         'family_principle_prior_hit': bool(set(family_ids) & set(previous_ids)) if family_ids else None,
                         'family_principle_runtime_hit': bool(set(family_ids) & set(ids)) if family_ids else None,
                         'model_answer': None, 'generation_status': 'not_run'})
    summary = {}
    for condition in ['no_hint', 'hint']:
        eligible = [r for r in rows if r['condition'] == condition and r['family_principle_prior_hit'] is not None]
        summary[condition] = {'eligible': len(eligible),
                              'prior_hits': sum(r['family_principle_prior_hit'] for r in eligible),
                              'runtime_hits': sum(r['family_principle_runtime_hit'] for r in eligible)}
    return {'mode': 'offline_preparation_only', 'new_api_calls': 0, 'model_answers': 0,
            'scope': 'v3 is now development material; principle retrieval is not diagnosis or semantic correctness',
            'max_payload_bytes': max(r['payload_bytes'] for r in rows),
            'all_within_request_limit': all(r['within_request_limit'] for r in rows),
            'summary': summary, 'rows': rows}


def run_audit(source, output, *, prepare_contexts=True):
    source, output = Path(source), Path(output)
    if output.exists():
        raise FileExistsError(output)
    original_bytes = source.read_bytes()
    actual = json.loads(original_bytes)
    if actual.get('mode') != 'actual_api' or actual.get('suite') != 'queryscope-v3':
        raise ValueError('actual_v3_results_required')
    if not actual.get('complete') or len(actual.get('rows', [])) != 24:
        raise ValueError('complete_24_response_source_required')
    verify_actual_lineage(actual, source)
    if summarize(actual['rows']) != actual['summary']:
        raise ValueError('primary_summary_mismatch')
    bundle = campaign_bundle('queryscope-v3')
    engine = campaign_engine(bundle)
    evaluation = [EvalQuery(c['query'], c['qrels']) for c in bundle['cases'] if c['qrels']]
    old_engine = SearchEngine(load_catalog())
    old_cases = [{'query': q.query, 'qrels': q.qrels} for q in load_evalset()]
    rows, decreases = [], []
    for original in actual['rows']:
        docs = [KnowledgeDoc(d['id'], d['title'], d['body'], d['source']) for d in original['context']['documents']]
        answer = validate_runtime_explanation(original['model_answer'], docs, original['context']['query'], engine)
        effect = {'status': 'not_run'}
        if answer['prescription']:
            candidate = Prescription.model_validate(answer['prescription'])
            gate, sandbox = run_gate(engine, evaluation, candidate)
            new = compare_ranking(engine, sandbox, bundle['cases'])
            old = compare_ranking(old_engine, old_engine.with_config(candidate.apply_to(old_engine.config)), old_cases)
            effect = {'status': 'measured', 'gate': asdict(gate), 'development_16': new,
                      'original_36': old, 'semantic_support': 'pending_independent_human_review'}
            for scope, comparison in [('development_16', new), ('original_36', old)]:
                decreases.extend({'case_id': original['case_id'], 'condition': original['condition'],
                                  'scope': scope, **change} for change in comparison['summary']['decreases'])
        rows.append({'case_id': original['case_id'], 'condition': original['condition'],
                     'query': original['context']['query'], 'context': original['context'],
                     'response_id': original['generation']['response_id'], 'raw_answer': original['model_answer'],
                     'primary_status': original['assessment']['validated_status'],
                     'primary_validation_error': original['assessment']['validation_error'],
                     'primary_effect': original['assessment']['patch_effect'],
                     'runtime_status': answer['status'], 'runtime_validation_error': answer['validation_error'],
                     'runtime_answer': answer, 'runtime_effect': effect,
                     'human_review': 'pending_independent_human_review'})
    measured = [r for r in rows if r['runtime_effect']['status'] == 'measured']
    report = {'mode': 'retrospective_runtime_audit', 'version': 4,
              'source_sha256': file_sha(source), 'new_api_calls': 0, 'new_model_responses': 0,
              'human_review': 'pending_independent_human_review',
              'method': 'same stored answers and original contexts, stricter runtime applicability; primary verdicts unchanged',
              'primary_summary': actual['summary'],
              'summary': {'primary_status_counts': dict(Counter(r['primary_status'] for r in rows)),
                          'runtime_status_counts': dict(Counter(r['runtime_status'] for r in rows)),
                          'newly_blocked': sum(r['primary_status'] != 'invalid' and r['runtime_status'] == 'invalid' for r in rows),
                          'gate_measured': len(measured),
                          'accepted_responses': sum(r['runtime_effect']['gate']['accepted'] for r in measured),
                          'rejected_responses': sum(not r['runtime_effect']['gate']['accepted'] for r in measured),
                          'regression_decreases': decreases}, 'rows': rows}
    if prepare_contexts:
        report['context_preparation'] = prepare_runtime_contexts(bundle, engine)
    if source.read_bytes() != original_bytes:
        raise ValueError('source_changed_during_audit')
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / 'audit.json', report)
    return report
