"""Independent failure contracts; all network transports below are test doubles."""
import copy
import subprocess
import sys
from pathlib import Path
import httpx
import pytest
from searchclinic.rag.explanation import validate_explanation
from searchclinic.rag.knowledge import KnowledgeDoc
from searchclinic.rag.openai_provider import OpenAIExplainer, ProviderError

ROOT=Path(__file__).resolve().parents[1]
DOC=KnowledgeDoc('D1','운영','색인을 변경하면 전체 회귀 검사를 수행해야 합니다.','작성 문서')
RAW={'status':'supported','summary':'형태소 분해가 검색 실패의 원인으로 확정되었습니다.',
     'family':'garbage_split','evidence':[{'doc_id':'D1','quote':DOC.body}],
     'patches':[{'kind':'user_word','terms':['백팩']}]}

def test_exact_but_irrelevant_quote_is_not_semantically_verified():
    r=validate_explanation(RAW,[DOC],'백팩')
    assert r['assessment']['citation_trace']=='verified'
    assert r['assessment']['semantic_support']=='requires_human_review'
    assert r['assessment']['cause']=='requires_human_review'
    assert r['assessment']['patch_effect']=='not_run'

@pytest.mark.parametrize('change',[{'family':'unknown'},{'evidence':[]}, {'status':'abstain'}])
def test_insufficient_or_abstaining_claim_never_yields_patch(change):
    r=validate_explanation({**RAW,**change},[DOC],'백팩')
    assert r['prescription'] is None

@pytest.mark.parametrize('terms',[['티슈','티슈'],['물티슈','물','휴지']])
def test_wrong_compound_is_blocked_without_rewriting_generated_answer(terms):
    raw=copy.deepcopy(RAW);raw['patches']=[{'kind':'compound','terms':terms}]
    before=copy.deepcopy(raw)
    assert validate_explanation(raw,[DOC],'티슈')['prescription'] is None
    assert raw==before

def test_default_provider_cannot_spend_even_if_key_is_present():
    calls=[]
    client=httpx.Client(transport=httpx.MockTransport(lambda req:calls.append(req)))
    with pytest.raises(ProviderError,match='budget_exhausted'):
        OpenAIExplainer('test-key',client=client).generate({'query':'백팩'})
    assert not calls

def test_retired_paid_campaign_cannot_restart_or_create_outputs(tmp_path):
    output=tmp_path/'paid'
    r=subprocess.run([sys.executable,str(ROOT/'scripts/evaluate_alba.py'),'--live','--output',str(output)],capture_output=True,text=True)
    assert r.returncode!=0
    assert not output.exists()
    assert 'retired' in r.stderr

@pytest.mark.parametrize('query,canonical,doc_id',[('아답터','어댑터','P035'),('백팩','배낭','P110')])
def test_link_candidate_recovers_target_and_preserves_base(query,canonical,doc_id):
    from searchclinic.rag.candidate_review import build_link_candidate
    from searchclinic.index.engine import SearchEngine
    from searchclinic.corpus.catalog import load_catalog
    from searchclinic.corpus.evalset import load_evalset
    from searchclinic.patch.gate import run_gate
    engine=SearchEngine(load_catalog())
    original=[h.doc_id for h in engine.search(query)]
    rx=build_link_candidate(engine,query,canonical)
    verdict,sandbox=run_gate(engine,load_evalset(),rx)
    assert verdict.accepted
    assert verdict.target_before.ndcg==0
    assert verdict.target_after.ndcg==1
    assert not verdict.regressions
    assert doc_id in [h.doc_id for h in sandbox.search(query)]
    assert [h.doc_id for h in engine.search(query)]==original

def test_unobserved_canonical_word_cannot_be_invented():
    from searchclinic.rag.candidate_review import build_link_candidate
    from searchclinic.index.engine import SearchEngine
    from searchclinic.corpus.catalog import load_catalog
    with pytest.raises(ValueError,match='canonical_not_in_index'):
        build_link_candidate(SearchEngine(load_catalog()),'백팩','미존재표준형')


def test_frozen_protocol_tampering_stops_evaluation(tmp_path):
    import importlib.util
    import shutil
    spec=importlib.util.spec_from_file_location('queryscope_eval',ROOT/'scripts/evaluate_queryscope.py')
    runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)
    for file in (ROOT/'docs/verification/queryscope-v1').glob('*'):
        if file.is_file():shutil.copyfile(file,tmp_path/file.name)
    runner.load_frozen(tmp_path)
    (tmp_path/'cases.json').write_text('[]',encoding='utf-8')
    with pytest.raises(ValueError,match='frozen_input_changed'):
        runner.load_frozen(tmp_path)
