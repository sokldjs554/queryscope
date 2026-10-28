"""Checks use development cases and tiny counterexample catalogs, not v2 holdout."""
from dataclasses import replace
from searchclinic.corpus.catalog import Document, load_catalog
from searchclinic.index.engine import SearchEngine
from searchclinic.rag.knowledge import KnowledgeDoc, load_knowledge
from searchclinic.rag.retriever import KnowledgeRetriever
from searchclinic.rag.explanation_service import ExplanationService
from searchclinic.service import ClinicService


def test_service_uses_actual_token_and_raw_observations_without_root_cause_hint():
    context, _ = ExplanationService(ClinicService()).context('워시', '세정용 상품을 찾습니다.')
    assert context.get('retrieval', {}).get('strategy') == 'runtime_description'
    assert context['retrieval']['base_strategy'] == 'observed_v3'
    assert any(s['kind'] == 'raw_substring_token_gap' for s in context['retrieval']['signals'])
    assert {'K004', 'K009'} & {d['id'] for d in context['documents']}


def test_dropped_and_fragmented_surface_is_visible_but_not_diagnosed():
    context, _ = ExplanationService(ClinicService()).context('아답터', '결과를 점검해 주세요.')
    assert any(s['kind'] == 'fragmented_surface' for s in context.get('retrieval', {}).get('signals', []))
    assert 'family' not in context and 'qrels' not in context
    assert context['retrieval']['status'] == 'observations_not_diagnosis'


def test_observed_fragmentation_is_not_drowned_out_by_incidental_latin_product_names():
    context, _ = ExplanationService(ClinicService()).context('노트북 아답터', '휴대용 상품을 찾습니다.')
    assert {'K001','K002','K003','K005','K011','K016','K017'} & {d['id'] for d in context['documents']}


def test_spelling_neighbors_are_only_candidates_and_require_catalog_support():
    from searchclinic.rag.observations import build_context
    engine = SearchEngine([Document('T', '카펫', '거실 바닥용', 'test')])
    ctx, _ = build_context(engine, KnowledgeRetriever(), '카페트', '점검')
    neighbors = [s for s in ctx['retrieval']['signals'] if s['kind'] == 'near_spelling']
    assert neighbors and all(s['candidate'] in engine.vocabulary() for s in neighbors)
    assert all(s['semantic_equivalence'] == 'unverified' for s in neighbors)
    empty, _ = build_context(SearchEngine([]), KnowledgeRetriever(), '카페트', '점검')
    assert not any(s['kind'] == 'near_spelling' for s in empty['retrieval']['signals'])


def test_excerpt_is_contiguous_body_and_records_offsets_not_title():
    from searchclinic.rag.observations import build_context
    body = '배경 설명입니다. ' * 60 + '\n\n복합어 부분어 색인 불일치를 원문 검색으로 점검한다.\n' + '나머지 설명. ' * 30
    doc = KnowledgeDoc('X', '제목을 본문으로 인용하지 않는다', body, 'fixture')
    ctx, docs = build_context(SearchEngine(load_catalog()), KnowledgeRetriever(docs=[doc]), '워시', '점검')
    d = ctx['documents'][0]
    assert d['body'] == body[d['body_start']:d['body_end']]
    assert len(d['body']) <= 400 and '복합어 부분어' in d['body']
    assert docs[0].body == d['body'] and d['body_start'] > 0


def test_family_metadata_does_not_change_retrieval():
    from searchclinic.rag.observations import build_context
    engine = SearchEngine(load_catalog())
    a, _ = build_context(engine, KnowledgeRetriever(), '백팩', '결과 확인')
    b, _ = build_context(engine, KnowledgeRetriever(docs=[replace(d, families=('bogus',)) for d in load_knowledge()]), '백팩', '결과 확인')
    assert a == b


def test_legacy_context_is_exact_original_input_shape():
    service = ExplanationService(ClinicService(), retrieval_strategy='legacy')
    ctx, _ = service.context('워시', '세정용 상품을 찾으려 합니다.')
    assert set(ctx) == {'query', 'problem', 'analysis', 'search', 'documents'}
    assert all(set(d) == {'id','title','body','source'} for d in ctx['documents'])


def test_generation_records_exact_compact_input_without_search_probe_instructions():
    sent=[]
    class Provider:
        def generate(self,context):
            sent.append(context)
            return {'raw':{'status':'abstain','family':'unknown','summary':'독립 근거가 부족하여 판단을 보류합니다.','evidence':[],'patches':[]}}
    report=ExplanationService(ClinicService(),provider=Provider()).explain('노트북 아답터','검색 결과를 점검합니다.')
    assert 'retrieval' not in sent[0]
    assert sent[0]==report['model_context']
    assert 'retrieval' in report['context']
