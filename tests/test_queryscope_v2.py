"""No paid requests: exercise immutable preparation and real scoring contracts."""
from pathlib import Path
import json
import shutil
import pytest
from searchclinic.analysis.config import UserWord, SynonymGroup, CompoundExpansion

ROOT=Path(__file__).resolve().parents[1]


def test_frozen_bundle_tamper_and_unknown_qrels_are_rejected(tmp_path):
    from searchclinic.evaluation.queryscope_v2 import load_bundle
    path=tmp_path/'bundle'; shutil.copytree(ROOT/'docs/verification/queryscope-v2',path)
    assert len(load_bundle(path)['cases']) == 24
    (path/'cases.json').write_text('[]',encoding='utf-8')
    with pytest.raises(ValueError,match='frozen_input_changed'):
        load_bundle(path)


def test_prepare_never_constructs_provider_and_keeps_paired_inputs(tmp_path,monkeypatch):
    from searchclinic.evaluation.llm_campaign import prepare, check_approval
    import searchclinic.rag.openai_provider as provider
    monkeypatch.setattr(provider.OpenAIExplainer,'__init__',lambda *a,**k:pytest.fail('paid provider constructed'))
    p=prepare(tmp_path/'prepared')
    assert len(p['requests']) == 24 and p['new_api_calls'] == 0
    assert all(r['model_answer'] is None for r in p['requests'])
    assert all(r['generation_status']=='not_run' for r in p['requests'])
    for row in p['requests']:
        assert not {'qrels','expected_action','expected_family','family_hypothesis'} & row['context'].keys()
        assert row['payload_bytes'] <= 11000
    insufficient=[r for r in p['requests'] if r['case_id'] in {'V21','V22'}]
    assert len(insufficient)==4 and all(not r['context']['documents'] for r in insufficient)
    with pytest.raises(FileExistsError): prepare(tmp_path/'prepared')
    with pytest.raises(ValueError,match='approval_required'):
        check_approval(tmp_path/'prepared',None)


def test_live_requires_exact_approval_and_refuses_modified_preparation(tmp_path):
    from searchclinic.evaluation.llm_campaign import prepare, check_approval, file_sha
    prepare(tmp_path/'prepared')
    a=tmp_path/'approval.json'
    a.write_text(json.dumps({'approved':False}),encoding='utf-8')
    with pytest.raises(ValueError,match='approval_required'):check_approval(tmp_path/'prepared',a)
    from searchclinic.rag.openai_provider import MODEL
    a.write_text(json.dumps({'approved':True,'approved_by':'test only','prepared_sha256':file_sha(tmp_path/'prepared/requests.json'),'model':MODEL,'calls':24,'max_usd':.30}),encoding='utf-8')
    assert check_approval(tmp_path/'prepared',a)['calls']==24
    f=tmp_path/'prepared/requests.json';f.write_text(f.read_text(encoding='utf-8')+' ',encoding='utf-8')
    with pytest.raises(ValueError,match='approval_preparation_mismatch'):check_approval(tmp_path/'prepared',a)


def test_invalid_patch_is_not_counted_as_successful_abstention():
    from searchclinic.evaluation.queryscope_v2 import assess_generation
    from searchclinic.index.engine import SearchEngine
    raw={'status':'abstain','family':'unknown','summary':'제공된 근거가 부족하여 판단을 보류합니다.','evidence':[], 'patches':[{'kind':'user_word','terms':['임의어']} ]}
    case={'expected_action':'abstain_no_patch','expected_family':None,'query':'임의어','qrels':{}}
    result=assess_generation(raw,{'documents':[]},case,SearchEngine([]),[])
    assert result['validated_status']=='invalid'
    assert result['appropriate_abstention_contract'] is False
    assert result['wrong_patch_on_abstain_required'] is True
    assert result['semantic_support']=='requires_independent_human_review'
    assert result['patch_effect']['status']=='not_run'


@pytest.mark.parametrize('factory',[
    lambda:UserWord(form='백\t팩'),
    lambda:SynonymGroup(terms=['백\n팩','배낭']),
    lambda:CompoundExpansion(word='물\t티슈',parts=['물\t','티슈']),
])
def test_direct_prescription_models_reject_hidden_whitespace(factory):
    with pytest.raises(ValueError):factory()


def test_campaign_error_is_not_abstention_and_approval_cannot_be_reused(tmp_path,monkeypatch):
    from searchclinic.evaluation.llm_campaign import prepare,execute,file_sha
    from searchclinic.rag import openai_provider as provider
    prepared=tmp_path/'prepared';prepare(prepared)
    approval=tmp_path/'approval.json'
    approval.write_text(json.dumps({'approved':True,'approved_by':'test fixture only',
        'prepared_sha256':file_sha(prepared/'requests.json'),'model':provider.MODEL,
        'calls':24,'max_usd':.30}),encoding='utf-8')
    class Fake:
        def __init__(self,key,*,budget):self.budget=budget
        def generate(self,context):
            self.budget.reserve()
            if self.budget.calls==1:raise provider.ProviderError('upstream_timeout')
            return {'raw':{'status':'abstain','family':'unknown','summary':'근거가 충분하지 않아 진단을 보류합니다.',
                'evidence':[],'patches':[]},'estimated_usd':0,'latency_ms':0,'model':'test-double',
                'response_id':'fixture-only','usage':{'input_tokens':0,'output_tokens':0}}
    monkeypatch.setattr(provider,'OpenAIExplainer',Fake)
    monkeypatch.setenv('OPENAI_API_KEY','fixture-not-a-real-key')
    result=execute(prepared,tmp_path/'first',approval)
    assert result['attempts']==24 and result['errors']==1 and result['responses']==23
    assert result['rows'][0]['model_answer'] is None and 'assessment' not in result['rows'][0]
    assert result['summary']['all']['api_errors']==1
    assert result['summary']['all']['abstain']==23
    with pytest.raises(ValueError,match='campaign_already_claimed'):
        execute(prepared,tmp_path/'second',approval)
    assert not (tmp_path/'second').exists()
