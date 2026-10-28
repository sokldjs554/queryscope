"""Runtime safety checks exercise the service without making model requests."""
import copy
import json
from pathlib import Path

import pytest

from searchclinic.rag.explanation_service import ExplanationService
from searchclinic.rag.knowledge import KnowledgeDoc
from searchclinic.rag.openai_provider import request_payload
from searchclinic.rag.retriever import Retrieved
from searchclinic.rag.runtime_contract import build_runtime_context, validate_runtime_explanation
from searchclinic.service import ClinicService, ToolFailed


DOC = KnowledgeDoc('K1', '표기 변형', '표기 변형은 좁은 동의어로 연결한다.', 'test knowledge')


class FixedRetriever:
    def retrieve(self, query, k=3):
        return [Retrieved(DOC, 1.0)]


class FixedProvider:
    def __init__(self, raw):
        self.raw = raw

    def generate(self, context):
        return {'raw': copy.deepcopy(self.raw), 'model': 'offline-test'}


@pytest.fixture(scope='module')
def clinic():
    return ClinicService()


def supported(kind='synonym', terms=None):
    return {'status': 'supported', 'summary': '표기 변형을 최소한의 후보로 제안합니다.',
            'family': 'spelling_variant',
            'evidence': [{'doc_id': 'K1', 'quote': DOC.body}],
            'patches': [{'kind': kind, 'terms': terms or ['프라이팬', '후라이팬']}]}


def explain(clinic, raw, query='후라이팬', strategy='observed'):
    return ExplanationService(clinic, FixedProvider(raw), FixedRetriever(), strategy).explain(query, '검색 결과 점검')


def test_runtime_context_distinguishes_knowledge_from_catalog_and_observations(clinic):
    report = explain(clinic, supported(), query='프라이팬')
    context = report['model_context']
    assert context.get('runtime_contract', {}).get('citable_doc_ids') == ['K1']
    catalog_ids = {row['doc_id'] for row in context['search']['results']}
    assert catalog_ids
    assert not catalog_ids.intersection(context['runtime_contract']['citable_doc_ids'])
    assert context['runtime_contract']['search_counts'] == 'not_health_or_relevance_labels'
    assert 'runtime_contract' not in report['context']


def test_runtime_prompt_applies_only_to_marked_contexts(clinic):
    report = explain(clinic, supported())
    legacy = request_payload({'query': '후라이팬', 'documents': []})
    current = request_payload(report['model_context'])
    assert current['input'][0]['content'] != legacy['input'][0]['content']
    assert current['text'] == legacy['text']


def test_missing_indexed_canonical_has_no_executable_prescription(clinic):
    raw = supported(terms=['마이크로스코프', 'microscope'])
    report = explain(clinic, raw, query='microscope')
    assert report['answer']['status'] == 'invalid'
    assert report['answer']['validation_error'] == 'canonical_not_in_index'
    assert report['answer']['prescription'] is None
    assert report['answer']['patches'] == []
    assert report['answer']['assessment']['semantic_support'] == 'requires_human_review'
    assert report['generation']['raw'] == raw


def test_known_indexed_canonical_remains_candidate_for_gate_and_human_review(clinic):
    answer = explain(clinic, supported())['answer']
    assert answer['status'] == 'supported'
    assert answer['prescription']['synonym_groups'] == [{'terms': ['프라이팬', '후라이팬']}]
    assert answer['assessment']['semantic_support'] == 'requires_human_review'
    assert answer['assessment']['patch_effect'] == 'not_run'


def test_compound_whole_must_be_current_index_token(clinic):
    raw = supported('compound', ['보디워시', '보디', '워시'])
    raw['family'] = 'compound_locked'
    answer = explain(clinic, raw, query='워시')['answer']
    assert answer['validation_error'] == 'compound_whole_not_in_index'
    assert answer['prescription'] is None


def test_indexed_compound_whole_and_query_part_remain_gate_candidate(clinic):
    raw = supported('compound', ['바디워시', '바디', '워시'])
    raw['family'] = 'compound_locked'
    answer = explain(clinic, raw, query='워시')['answer']
    assert answer['status'] == 'supported'
    assert answer['prescription']['compound_expansions'] == [{'word': '바디워시', 'parts': ['바디', '워시']}]


@pytest.mark.parametrize('kind,terms', [('synonym', ['프라이팬', '후라이팬']), ('user_word', ['후라이팬']),
                                       ('compound', ['바디워시', '바디', '워시'])])
def test_unrelated_patch_targets_are_blocked(clinic, kind, terms):
    answer = explain(clinic, supported(kind, terms), query='노트북')['answer']
    assert answer['validation_error'] == 'patch_target_unrelated_to_query'
    assert answer['prescription'] is None


def test_catalog_id_cannot_be_used_as_knowledge_source(clinic):
    raw = supported()
    raw['evidence'][0]['doc_id'] = next(iter(clinic.baseline_engine.docs))
    answer = explain(clinic, raw)['answer']
    assert answer['status'] == 'invalid'
    assert answer['validation_error'] == 'citation_source_or_text'
    assert answer['prescription'] is None


@pytest.mark.parametrize('quote', ['표기 변형은 넓은 동의어로 연결한다.', '원문에는 없는 새로운 인용문입니다.'])
def test_runtime_keeps_strict_original_body_quote_validation(clinic, quote):
    raw = supported()
    raw['evidence'][0]['quote'] = quote
    answer = explain(clinic, raw)['answer']
    assert answer['validation_error'] == 'citation_source_or_text'
    assert answer['prescription'] is None


def test_fuzzy_neighbor_remains_unverified_not_automatic_semantic_approval(clinic):
    raw = supported(terms=['박자', '박자기'])
    answer = explain(clinic, raw, query='박자기')['answer']
    assert answer['validation_error'] == 'canonical_not_in_index'
    assert answer['prescription'] is None
    assert answer['assessment']['semantic_support'] == 'requires_human_review'


def test_even_indexed_spelling_neighbor_does_not_receive_semantic_approval():
    from searchclinic.corpus.catalog import Document
    from searchclinic.index.engine import SearchEngine
    engine = SearchEngine([Document('T1', '박자', '리듬 연습', 'test')])
    answer = validate_runtime_explanation(supported(terms=['박자', '박자기']), [DOC], '박자기', engine)
    assert answer['status'] == 'supported'
    assert answer['prescription'] is not None
    assert answer['assessment']['cause'] == 'requires_human_review'
    assert answer['assessment']['semantic_support'] == 'requires_human_review'
    assert answer['assessment']['patch_effect'] == 'not_run'


def test_catalog_shaped_document_cannot_expand_trusted_knowledge_allowlist(clinic):
    full, docs = ExplanationService(clinic, retriever=FixedRetriever()).context('프라이팬', '점검')
    catalog = full['search']['results'][0]
    full['documents'].append({'id': catalog['doc_id'], 'title': catalog['name'],
                              'body': '상품 원문은 지식 출처로 승격하지 않습니다.', 'source': 'catalog'})
    sent = build_runtime_context(full, docs)
    assert sent['runtime_contract']['citable_doc_ids'] == ['K1']
    assert [doc['id'] for doc in sent['documents']] == ['K1']


def test_no_knowledge_docs_never_makes_catalog_ids_citable(clinic):
    full, _ = ExplanationService(clinic, retriever=FixedRetriever()).context('프라이팬', '점검')
    sent = build_runtime_context(full, [])
    assert sent['documents'] == []
    assert sent['runtime_contract']['citable_doc_ids'] == []


def test_description_fallback_candidates_reach_model_as_uncitable_observations(clinic):
    full, docs = ExplanationService(clinic, retriever=FixedRetriever()).context('microscope', '교육용 현미경')
    candidate = {'id': 'R015', 'name': '교육용 현미경', 'description': '관찰 도구',
                 'matched_terms': ['현미경'], 'provenance': 'problem_text_lexical_search',
                 'semantic_equivalence': 'unverified'}
    full['catalog_candidates'] = [candidate]
    sent = build_runtime_context(full, docs)
    assert sent['observations'].get('catalog_candidates') == [candidate]
    assert sent['runtime_contract']['citable_doc_ids'] == ['K1']
    assert 'R015' not in sent['runtime_contract']['citable_doc_ids']


def test_normal_abstention_has_no_patch_or_gate(clinic):
    raw = {'status': 'abstain', 'summary': '근거가 충분하지 않아 판단을 보류합니다.',
           'family': 'unknown', 'evidence': [], 'patches': []}
    service = ExplanationService(clinic, FixedProvider(raw), FixedRetriever())
    report = service.explain('후라이팬', '결과 점검')
    assert report['answer']['status'] == 'abstain'
    assert report['answer']['prescription'] is None
    assert report['gate'] is None
    with pytest.raises(ToolFailed, match='수정 후보'):
        service.apply(report['id'])


@pytest.mark.parametrize('version', ['v2', 'v3'])
def test_frozen_prepared_payload_bytes_remain_identical(version):
    path = Path(__file__).parents[1] / 'docs' / 'verification' / f'queryscope-{version}' / 'llm-prepared-v1' / 'requests.json'
    for row in json.loads(path.read_text(encoding='utf-8'))['requests']:
        expected = json.dumps(row['payload'], ensure_ascii=False).encode('utf-8')
        actual = json.dumps(request_payload(row['context']), ensure_ascii=False).encode('utf-8')
        assert actual == expected


@pytest.mark.parametrize('strategy', ['legacy', 'observed_v2'])
def test_historical_service_strategies_do_not_enable_runtime_validation(clinic, strategy):
    report = explain(clinic, supported(terms=['마이크로스코프', 'microscope']), query='microscope', strategy=strategy)
    assert 'runtime_contract' not in report['model_context']
    assert report['answer']['status'] == 'supported'
