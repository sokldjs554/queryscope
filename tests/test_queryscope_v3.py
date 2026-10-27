from searchclinic.analysis.config import AnalyzerConfig
from searchclinic.corpus.catalog import Document
from searchclinic.index.engine import SearchEngine
from searchclinic.rag.observations import build_context
from searchclinic.rag.retriever import KnowledgeRetriever


def test_normal_suffix_token_coverage_is_not_a_missing_compound():
    engine=SearchEngine([Document('D','휴대용 전지','작은 전원 공급 장치','전기')])
    context,_=build_context(engine,KnowledgeRetriever(),'휴대용 배터리','원하는 물품을 찾습니다.')
    assert not any(s['kind']=='raw_substring_token_gap' for s in context['retrieval']['signals'])


def test_frozen_v2_mode_preserves_its_known_false_signal():
    engine=SearchEngine([Document('D','휴대용 전지','작은 전원 공급 장치','전기')])
    context,_=build_context(engine,KnowledgeRetriever(),'휴대용 배터리','원하는 물품을 찾습니다.',strategy='observed_v2')
    assert any(s['kind']=='raw_substring_token_gap' for s in context['retrieval']['signals'])


def test_true_atomic_compound_gap_still_retrieves_principle():
    engine=SearchEngine([Document('D','물티슈','깨끗한 위생용품','생활')],AnalyzerConfig(user_words=[{'form':'물티슈'}]))
    context,_=build_context(engine,KnowledgeRetriever(),'티슈','이 표현이 들어간 상품을 찾습니다.')
    assert any(s['kind']=='raw_substring_token_gap' for s in context['retrieval']['signals'])
    assert {'K004','K009'} & {d['id'] for d in context['documents']}


def test_excerpt_cache_is_bounded_and_never_changes_exact_offsets():
    from searchclinic.rag.observations import excerpt,_window_terms
    engine=SearchEngine([])
    body='배경 설명입니다. '*80+'\n\n복합어 부분어 색인 오류의 근거입니다.'
    expected=excerpt(body,'복합어 부분어',engine.analyzer,cached=False)
    assert excerpt(body,'복합어 부분어',engine.analyzer,cached=True)==expected
    before=_window_terms.cache_info().hits
    assert excerpt(body,'복합어 부분어',engine.analyzer,cached=True)==expected
    assert _window_terms.cache_info().hits>before
    assert _window_terms.cache_info().maxsize==512


def test_v3_preparation_uses_frozen_atomic_config_without_model_calls(tmp_path):
    from searchclinic.evaluation.llm_campaign import prepare
    result=prepare(tmp_path/'prep',suite='queryscope-v3')
    assert result['suite']=='queryscope-v3'
    assert result['new_api_calls']==0 and len(result['requests'])==24
    row=next(r for r in result['requests'] if r['case_id']=='T01' and r['condition']=='no_hint')
    assert row['context']['search']['total']==0
    assert any(s['kind']=='raw_substring_token_gap' for s in row['context']['observations']['signals'])
    assert all(r['model_answer'] is None for r in result['requests'])


def test_suite_selection_is_validated_not_used_as_a_path(tmp_path):
    import pytest
    from searchclinic.evaluation.llm_campaign import prepare
    with pytest.raises(ValueError,match='unknown_suite'):
        prepare(tmp_path/'out',suite='../other')
    assert not (tmp_path/'out').exists()


def test_invalid_control_prevents_llm_preparation(tmp_path,monkeypatch):
    import pytest
    from searchclinic.evaluation import llm_campaign as campaign
    original=campaign.campaign_bundle('queryscope-v3')
    # Removing forced atomic indexing makes at least some controls invalid.
    original['cases'][0]['query']='상품명이아닌말'
    monkeypatch.setattr(campaign,'campaign_bundle',lambda _:original)
    with pytest.raises(ValueError,match='control_precondition_failed'):
        campaign.prepare(tmp_path/'bad',suite='queryscope-v3')
    assert not (tmp_path/'bad').exists()


def test_approval_is_bound_to_suite(tmp_path):
    import json
    import pytest
    from searchclinic.evaluation.llm_campaign import prepare, check_approval
    prepare(tmp_path/'prep',suite='queryscope-v3')
    approval=tmp_path/'prep/approval-template.json'
    data=json.loads(approval.read_text(encoding='utf-8'))
    data.update(approved=True,approved_by='unit test only',suite='queryscope-v2')
    approval.write_text(json.dumps(data),encoding='utf-8')
    with pytest.raises(ValueError,match='approval_suite_mismatch'):
        check_approval(tmp_path/'prep',approval)
    data['suite']='queryscope-v3'
    approval.write_text(json.dumps(data),encoding='utf-8')
    assert check_approval(tmp_path/'prep',approval)['suite']=='queryscope-v3'
