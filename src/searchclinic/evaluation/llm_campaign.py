"""Prepare for a separately authorized campaign. Importing never reads a key."""
from __future__ import annotations
from datetime import datetime,timezone
import json
import os
from pathlib import Path
from searchclinic.corpus.evalset import EvalQuery
from searchclinic.index.engine import SearchEngine
from searchclinic.rag.retriever import KnowledgeRetriever
from searchclinic.rag.observations import model_context
from searchclinic.evaluation.queryscope_v2 import (
    ROOT,load_bundle,file_sha,json_sha,write_json,paired_context,assess_generation,
)

# Stable within this checkout, independent of copied input/output directories.
# Preserve this durable local state across runs; it is not an account-wide quota.
CAMPAIGN_STATE_ROOT=ROOT/'work/llm-campaigns'


def prepare(output):
    from searchclinic.rag.openai_provider import MODEL,MAX_REQUEST_BYTES,request_payload
    output=Path(output)
    if output.exists(): raise FileExistsError(output)
    bundle=load_bundle();engine=SearchEngine(bundle['catalog']);retriever=KnowledgeRetriever()
    rows=[]
    for case_id in bundle['rubric']['paid_case_ids']:
        case=next(c for c in bundle['cases'] if c['id']==case_id)
        for condition in ['no_hint','hint']:
            full,_=paired_context(engine,retriever,case,condition,'observed')
            context=model_context(full)
            payload=request_payload(context)
            size=len(json.dumps(payload,ensure_ascii=False).encode('utf-8'))
            if size>MAX_REQUEST_BYTES:raise ValueError('prepared_input_too_large: '+case_id)
            rows.append({'case_id':case_id,'condition':condition,'context':context,
                'context_sha256':json_sha(context),'full_context':full,'payload':payload,
                'payload_sha256':json_sha(payload),'payload_bytes':size,
                'model_answer':None,'generation_status':'not_run'})
    output.mkdir(parents=True,exist_ok=False)
    prepared={'created_at':datetime.now(timezone.utc).isoformat(),'mode':'dry_run',
        'new_api_calls':0,'model':MODEL,'calls_if_approved':len(rows),'reservation_usd':.30,
        'frozen_manifest':bundle['manifest'],'requests':rows}
    write_json(output/'requests.json',prepared)
    write_json(output/'approval-template.json',{'approved':False,'approved_by':None,
        'prepared_sha256':file_sha(output/'requests.json'),'model':MODEL,'calls':24,'max_usd':.30})
    write_json(output/'human-review.json',{'status':'pending_independent_human_review',
        'rows':[{'case_id':r['case_id'],'condition':r['condition'],'reviewer':None,
            'independent':None,'cause_sufficiency':None,'semantic_support':None,
            'abstention_appropriateness':None,'patch_semantics':None,'reason':None} for r in rows]})
    return prepared


def check_approval(prepared_dir,approval_path):
    from searchclinic.rag.openai_provider import MODEL,request_payload,MAX_REQUEST_BYTES
    if not approval_path:raise ValueError('approval_required')
    approval=json.loads(Path(approval_path).read_text(encoding='utf-8'))
    if approval.get('approved') is not True or not approval.get('approved_by'):
        raise ValueError('approval_required')
    path=Path(prepared_dir)/'requests.json'
    if approval.get('prepared_sha256')!=file_sha(path):raise ValueError('approval_preparation_mismatch')
    if approval.get('model')!=MODEL or approval.get('calls')!=24 or approval.get('max_usd')!=.30:
        raise ValueError('approval_budget_mismatch')
    data=json.loads(path.read_text(encoding='utf-8'));bundle=load_bundle()
    expected={(c,cond) for c in bundle['rubric']['paid_case_ids'] for cond in ['hint','no_hint']}
    if (data['frozen_manifest']!=bundle['manifest'] or len(data['requests'])!=24 or
        {(r['case_id'],r['condition']) for r in data['requests']}!=expected):
        raise ValueError('preparation_cases_changed')
    for row in data['requests']:
        if row['context_sha256']!=json_sha(row['context']) or row['payload']!=request_payload(row['context']):
            raise ValueError('preparation_payload_changed')
        if len(json.dumps(row['payload'],ensure_ascii=False).encode())>MAX_REQUEST_BYTES:
            raise ValueError('prepared_input_too_large')
    return approval


def summarize(rows):
    """Keep errors, invalid responses and contract-level abstentions separate."""
    def counts(items):
        assessments=[r['assessment'] for r in items if 'assessment' in r]
        return {'planned_or_attempted':len(items),
            'api_errors':sum(r['generation_status']=='api_error' for r in items),
            'supported':sum(a['validated_status']=='supported' for a in assessments),
            'abstain':sum(a['validated_status']=='abstain' for a in assessments),
            'invalid':sum(a['validated_status']=='invalid' for a in assessments),
            'abstention_contract_eligible':sum(a['appropriate_abstention_contract'] is not None for a in assessments),
            'abstention_contract_pass':sum(a['appropriate_abstention_contract'] is True for a in assessments),
            'wrong_patch_on_abstain_required':sum(a['wrong_patch_on_abstain_required'] is True for a in assessments),
            'literal_family_match':sum(a['family_label_match'] is True for a in assessments),
            'family_label_eligible':sum(a['family_label_match'] is not None for a in assessments),
            'semantic_human_review':'pending'}
    return {'all':counts(rows),**{c:counts([r for r in rows if r['condition']==c]) for c in ['hint','no_hint']}}


def execute(prepared_dir,output,approval_path):
    """Only explicit future authorization may call this; no retry/resume/overwrite."""
    from searchclinic.rag.openai_provider import Budget,OpenAIExplainer,ProviderError
    approval=check_approval(prepared_dir,approval_path)
    output=Path(output)
    if output.exists():raise FileExistsError(output)
    key=os.environ.get('OPENAI_API_KEY')
    if not key:raise ValueError('provider_not_configured')
    campaign_state=CAMPAIGN_STATE_ROOT/approval['prepared_sha256']
    CAMPAIGN_STATE_ROOT.mkdir(parents=True,exist_ok=True)
    try:
        campaign_state.mkdir(exist_ok=False)
    except FileExistsError:
        raise ValueError('campaign_already_claimed') from None
    # Claim before initialization/network. Crashes leave the campaign claimed.
    write_json(campaign_state/'execution-claim.json',
        {'approval_sha256':file_sha(approval_path),'prepared_sha256':approval['prepared_sha256'],
         'output':str(output.resolve())})
    bundle=load_bundle();engine=SearchEngine(bundle['catalog'])
    evalset=[EvalQuery(c['query'],c['qrels']) for c in bundle['cases'] if c['qrels']]
    data=json.loads((Path(prepared_dir)/'requests.json').read_text(encoding='utf-8'))
    output.mkdir(parents=True,exist_ok=False)
    budget=Budget(campaign_state/'budget.json',max_calls=24)
    provider=OpenAIExplainer(key,budget=budget)
    report={'mode':'actual_api','prepared_sha256':file_sha(Path(prepared_dir)/'requests.json'),
        'campaign_state_path':str(campaign_state.resolve()),
        'approval_sha256':file_sha(approval_path),'complete':False,'attempts':0,'responses':0,'errors':0,
        'estimated_usd':0,'semantic_review':'pending_independent_human_review','rows':[]}
    write_json(output/'results.json',report)
    for request in data['requests']:
        row={'case_id':request['case_id'],'condition':request['condition'],
             'context':request['context'],'context_sha256':request['context_sha256'],
             'generation_status':'pending','model_answer':None}
        report['rows'].append(row);write_json(output/'results.json',report)
        try:
            generated=provider.generate(request['context'])
            row.update(generation=generated,model_answer=generated['raw'],generation_status='completed')
            report['responses']+=1;report['estimated_usd']+=generated['estimated_usd']
            # Persist the real response BEFORE evaluation, so scoring errors cannot lose it.
            write_json(output/'results.json',report)
            case=next(c for c in bundle['cases'] if c['id']==request['case_id'])
            row['assessment']=assess_generation(generated['raw'],request['context'],case,engine,evalset)
        except ProviderError as error:
            row.update(generation_status='api_error',error=str(error));report['errors']+=1
        finally:
            report['attempts']=budget.calls
            report['reserved_usd']=round(budget.calls*.0125,6)
            if budget.path.exists():
                # Receipt for convenient inspection; never used as the authority.
                write_json(output/'budget-receipt.json',json.loads(budget.path.read_text(encoding='utf-8')))
            write_json(output/'results.json',report)
    report['summary']=summarize(report['rows'])
    report['complete']=True;write_json(output/'results.json',report)
    return report
