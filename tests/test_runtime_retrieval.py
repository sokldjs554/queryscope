"""Runtime evidence retrieval uses descriptions without asserting synonymy."""
import hashlib

from searchclinic.analysis.config import AnalyzerConfig
from searchclinic.corpus.catalog import Document
from searchclinic.index.engine import SearchEngine
from searchclinic.rag.knowledge import load_knowledge
from searchclinic.rag.observations import build_context
from searchclinic.rag.retriever import KnowledgeRetriever


def runtime(engine, query, problem):
    from searchclinic.rag.runtime_retrieval import build_runtime_retrieval_context
    return build_runtime_retrieval_context(engine, KnowledgeRetriever(), query, problem)


def test_missing_latin_query_exposes_description_candidate_and_script_hypothesis():
    engine = SearchEngine([Document('X1', '실내용 온도계', '실내 온도를 재는 기구', '측정')])
    original, _ = build_context(engine, KnowledgeRetriever(), 'thermometer', '온도를 재는 기구를 찾습니다.')
    context, docs = runtime(engine, 'thermometer', '온도를 재는 기구를 찾습니다.')
    assert context['search'] == original['search']
    assert context['catalog_candidates'][0]['id'] == 'X1'
    assert context['catalog_candidates'][0]['semantic_equivalence'] == 'unverified'
    assert any(s['kind'] == 'different_scripts' and s['semantic_equivalence'] == 'unverified'
               for s in context['retrieval']['signals'])
    assert any('영한 혼용' in d.title for d in docs)
    assert context['retrieval']['strategy'] != original['retrieval']['strategy']


def test_description_candidate_does_not_promote_spelling_neighbor_to_synonym():
    engine = SearchEngine([
        Document('X1', '제도용 컴퍼스', '원을 그리는 도구', '문구'),
        Document('X2', '종이 날개', '모형 비행기의 날개 부품', '공작'),
    ], AnalyzerConfig(user_words=[{'form': '날개기'}]))
    context, _ = runtime(engine, '날개기', '원을 그리는 도구를 찾습니다.')
    assert [d['id'] for d in context['catalog_candidates']] == ['X1']
    assert all(d['semantic_equivalence'] == 'unverified' for d in context['catalog_candidates'])
    assert not any(s['kind'] == 'different_scripts' for s in context['retrieval']['signals'])
    assert 'patches' not in context


def test_generic_request_and_single_informative_overlap_do_not_infer_relation():
    engine = SearchEngine([
        Document('X1', '물품 안내서', '요청한 물품의 검색 결과를 확인하는 정보', '문서'),
        Document('X2', '온도 표시판', '온도 정보를 표시하는 물품', '측정'),
    ])
    for problem in ['요청한 물품의 검색 결과를 확인해 주세요.', '온도 기구를 찾습니다.']:
        context, _ = runtime(engine, 'florbin', problem)
        assert context['catalog_candidates'] == []
        assert not any(s['kind'] == 'different_scripts' for s in context['retrieval']['signals'])


def test_direct_query_hit_does_not_trigger_description_fallback():
    engine = SearchEngine([Document('X1', '온도계', '온도를 재는 기구', '측정')])
    original, original_docs = build_context(engine, KnowledgeRetriever(), '온도계', '온도를 재는 기구')
    context, docs = runtime(engine, '온도계', '온도를 재는 기구')
    assert context['catalog_candidates'] == []
    assert context['documents'] == original['documents']
    assert docs == original_docs
    assert context['retrieval']['signals'] == original['retrieval']['signals']


def test_candidates_are_bounded_and_knowledge_excerpts_keep_exact_provenance():
    engine = SearchEngine([Document(str(i), '실내 온도계 ' + str(i),
        '온도를 재는 측정 장치 ' + '긴 설명 ' * 300, '측정') for i in range(4)])
    context, docs = runtime(engine, 'thermometer', '온도를 재는 측정 장치를 찾습니다.')
    assert len(context['catalog_candidates']) == 2
    assert all(len(c['description']) <= 180 for c in context['catalog_candidates'])
    assert len(docs) <= 3
    sources = {d.doc_id: d for d in load_knowledge()}
    for item in context['documents']:
        source = sources[item['id']]
        assert item['body'] == source.body[item['body_start']:item['body_end']]
        assert item['full_body_sha256'] == hashlib.sha256(source.body.encode()).hexdigest()
    assert [d.doc_id for d in docs] == [d['id'] for d in context['documents']]


def test_default_explanation_service_uses_description_hypotheses(monkeypatch):
    from searchclinic.rag.explanation_service import ExplanationService
    from searchclinic.service import ClinicService
    clinic = ClinicService()
    engine = SearchEngine([Document('X1', '실내용 온도계', '실내 온도를 재는 기구', '측정')])
    monkeypatch.setattr(clinic, '_baseline', engine)
    context, _ = ExplanationService(clinic).context('thermometer', '온도를 재는 기구를 찾습니다.')
    assert context['catalog_candidates'][0]['id'] == 'X1'
    assert context['catalog_candidates'][0]['semantic_equivalence'] == 'unverified'
    assert context['retrieval']['version'] == 'description_fallback_v1'


def test_frozen_campaign_contexts_still_match_original_preparations():
    import json
    from pathlib import Path
    from searchclinic.evaluation.llm_campaign import campaign_bundle, campaign_engine
    from searchclinic.evaluation.queryscope_v2 import paired_context
    from searchclinic.rag.observations import model_context
    root = Path(__file__).resolve().parents[1]
    retriever = KnowledgeRetriever()
    for suite, strategy in [('queryscope-v2', 'observed'), ('queryscope-v3', 'observed_v3')]:
        bundle = campaign_bundle(suite)
        engine = campaign_engine(bundle)
        original = json.loads((root / 'docs/verification' / suite / 'llm-prepared-v1/requests.json').read_text(encoding='utf-8'))
        cases = {c['id']: c for c in bundle['cases']}
        for row in original['requests']:
            context, _ = paired_context(engine, retriever, cases[row['case_id']], row['condition'], strategy)
            assert model_context(context) == row['context'], (suite, row['case_id'], row['condition'])
