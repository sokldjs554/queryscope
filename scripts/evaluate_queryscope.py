"""Frozen offline evaluation. No provider, key, or paid path; never overwrites runs."""
from __future__ import annotations
import argparse
from collections import Counter
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import subprocess
from searchclinic.corpus.catalog import load_catalog
from searchclinic.corpus.evalset import EvalQuery, load_evalset
from searchclinic.evaluation.metrics import evaluate_all, evaluate_query, mean_ndcg
from searchclinic.index.engine import SearchEngine
from searchclinic.patch.gate import run_gate
from searchclinic.patch.ir import Prescription
from searchclinic.rag.candidate_review import build_link_candidate
from searchclinic.rag.explanation import validate_explanation
from searchclinic.rag.explanation_service import ExplanationService
from searchclinic.rag.knowledge import KnowledgeDoc, load_knowledge
from searchclinic.service import ClinicService

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'docs/verification/queryscope-v1'
BASE='493935f6b7ddd9201e67125a4897e8e76ffd67f8'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def encoded_sha(obj):
    return hashlib.sha256(json.dumps(obj,ensure_ascii=False,sort_keys=True).encode()).hexdigest()


def load_frozen(data=DATA):
    manifest=json.loads((data/'manifest.json').read_text(encoding='utf-8'))
    for name,expected in manifest.items():
        if digest(data/name)!=expected:
            raise ValueError('frozen_input_changed: '+name)
    cases=json.loads((data/'cases.json').read_text(encoding='utf-8'))
    old={q.query for q in load_evalset()}
    old.update(c['query'] for c in json.loads((ROOT/'docs/verification/alba-20261027/cases.json').read_text(encoding='utf-8')))
    if len({c['query'] for c in cases})!=len(cases) or old & {c['query'] for c in cases}:
        raise ValueError('duplicate_or_development_query')
    catalog={d.doc_id for d in load_catalog()}
    if any(set(c['qrels'])-catalog for c in cases):
        raise ValueError('unknown_relevance_document')
    return cases,manifest


def metrics(engine,case):
    eq=EvalQuery(case['query'],case['qrels'])
    m=asdict(evaluate_query(engine,eq))
    hits=engine.search(eq.query,k=10)
    m['precision5_returned_denominator']=m.pop('precision5')
    m['precision_at_5']=round(sum(h.doc_id in eq.qrels for h in hits[:5])/5,4)
    m['hits_at_10']=[h.doc_id for h in hits]
    if not eq.qrels:
        m.update(ndcg=None,recall=None,precision_at_5=None,precision5_returned_denominator=None)
    return m


def ablations(cases,svc):
    knowledge=load_knowledge()
    rows=[]
    for case in cases:
        family=case.get('family')
        relevant={d.doc_id for d in knowledge if family in d.families and len(d.families)<5}
        pair={'case_id':case['id'],'family_hypothesis':family,'expected_diagnosis':case.get('expected_diagnosis'),
              'relevant_doc_ids':sorted(relevant),'generation_evaluation':'not_run_no_paid_calls','conditions':{}}
        for condition,key in [('hint','problem_hint'),('no_hint','problem_no_hint')]:
            context,_=svc.context(case['query'],case[key])
            ids=[d['id'] for d in context['documents']]
            rr=next((1/i for i,d in enumerate(ids,1) if d in relevant),0)
            pair['conditions'][condition]={'context':context,'context_sha256':encoded_sha(context),
                'retrieved_ids':ids,'family_hit_at_3':bool(set(ids)&relevant) if relevant else None,
                'family_mrr':rr if relevant else None,'model_answer':None}
        rows.append(pair)
    summary={}
    for condition in ['hint','no_hint']:
        eligible=[r['conditions'][condition] for r in rows if r['relevant_doc_ids']]
        summary[condition]={'eligible':len(eligible),
            'hits':sum(r['family_hit_at_3'] for r in eligible),
            'hit_rate':round(sum(r['family_hit_at_3'] for r in eligible)/len(eligible),4) if eligible else None,
            'mrr':round(sum(r['family_mrr'] for r in eligible)/len(eligible),4) if eligible else None}
    return {'summary':summary,'rows':rows,'scope':'retrieval only; no new model diagnosis or abstention measurement'}


def legacy_audit():
    src=ROOT/'docs/verification/alba-20261027/run/results.json'
    revalidated=ROOT/'docs/verification/alba-20261027/run/revalidated.json'
    old=json.loads(revalidated.read_text(encoding='utf-8'))
    original=json.loads(src.read_text(encoding='utf-8'))
    reviewed=[]
    notes={
        'A01':'원문 어미를 바꾼 인용. 의미가 비슷해도 자동 복원 금지; 그대로 차단.',
        'A04':'일반 동의어 원칙은 핸드폰=휴대폰을 이번 관측만으로 입증하지 못함.',
        'A05':'compound=[티슈,티슈]는 전체 단어+최소 두 부분어 계약 위반. 별도 수동 후보를 실험.',
        'A06':'사전만으로 표준형 연결 불가. 과거 K001의 NR 제거 설명은 현재 필터와 불일치; 새 지식 수정, 옛 인용은 보존.',
        'A07':'family=compound_locked는 분해된 백/팩 관측 및 garbage_split 라벨과 불일치. 인용 존재와 원인 정확도는 다름.',
        'A08':'K019 일반 회귀 경고가 이 질의의 표기 변형을 직접 뒷받침하지는 않음.',
        'A09':'제목을 본문처럼 인용. 정상 검색의 무수정 설명은 가능하나 기존 상태 계약에는 부적합.',
        'A12':'요약은 판단 불가인데 status=supported/family=unknown. 새 생성 없이 상태를 임의 교정하지 않음.'}
    for rawrow,prev in zip(original['rows'],old['rows'],strict=True):
        context=rawrow['context'];raw=rawrow['generation']['raw']
        docs=[KnowledgeDoc(d['id'],d['title'],d['body'],d['source']) for d in context['documents']]
        result=validate_explanation(raw,docs,context['query'])
        eligible=rawrow['category'] in {'spelling_variant','cross_script','synonym_gap','garbage_split','compound_locked'}
        reviewed.append({'case_id':rawrow['case_id'],'condition':rawrow['condition'],
            'query':context['query'],'original_family':raw['family'],'reference_family':rawrow['category'],
            'family_label_match':raw['family']==rawrow['category'] if eligible else None,
            'original_answer':raw,'assessment':result['assessment'],'validation_error':result['validation_error'],
            'validated_status':result['status'],'prior_gate':prev.get('gate'),
            'semantic_review_status':'requires_independent_human_review',
            'analyst_note':notes.get(rawrow['case_id'],'일반 원칙과 이번 관측의 연결은 독립 의미 검토 필요. 근거 제거 조건에서는 원인을 확정할 수 없음.'),
            'analyst':'Codex-assisted analysis, not an independent human adjudication'})
    return {'source_sha256':digest(src),'revalidated_sha256':digest(revalidated),
            'new_api_calls':0,'rows':reviewed,
            'summary':{'statuses':dict(Counter(r['validated_status'] for r in reviewed)),
                'semantic_human_pending':len(reviewed)}}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    cases,manifest=load_frozen()
    args.output.mkdir(parents=True,exist_ok=False)
    report={'created_at':datetime.now(timezone.utc).isoformat(),'base_commit':BASE,
        'commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'frozen_manifest':manifest,'new_api_calls':0,'authored':True,
        'environment':{'python':platform.python_version(),**{p:importlib.metadata.version(p) for p in ['kiwipiepy','kiwipiepy_model','pydantic']}},
        'source_sha256':{str(p.relative_to(ROOT)):digest(p) for p in sorted((ROOT/'src/searchclinic').rglob('*.py'))},
        'runner_sha256':digest(Path(__file__)),'scope':'offline local authored data; no customer/generalization/LLM accuracy claim'}
    path=args.output/'results.json'
    def save():path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    save()
    engine=SearchEngine(load_catalog());oldset=load_evalset()
    candidates=[];config=engine.config
    for query,canonical in [('아답터','어댑터'),('백팩','배낭')]:
        rx=build_link_candidate(engine,query,canonical)
        original=Prescription(target_query=query,diagnosis_family='garbage_split',
            reasoning='과거 모델이 제안한 사용자 사전 단독 후보 재현입니다.',user_words=[{'form':query}])
        attempts=[]
        for name,candidate in [('dictionary_only',original),('dictionary_and_explicit_link',rx)]:
            verdict,sandbox=run_gate(engine,oldset,candidate)
            before=evaluate_all(engine,oldset);after=evaluate_all(sandbox,oldset)
            attempts.append({'name':name,'prescription':candidate.model_dump(),'gate':asdict(verdict),
                'all_36_before':{q:asdict(v) for q,v in before.items()},
                'all_36_after':{q:asdict(v) for q,v in after.items()},
                'query_tokens':sandbox.analyzer.tokens(query),
                'canonical_tokens':sandbox.analyzer.tokens(canonical)})
        candidates.append({'query':query,'canonical_proposed_by':'Codex-assisted operator, not LLM generation',
            'canonical':canonical,'base_tokens':engine.analyzer.tokens(query),'dropped':engine.analyzer.dropped(query),'attempts':attempts})
        config=rx.apply_to(config)
    compound=Prescription(target_query='티슈',diagnosis_family='compound_locked',reasoning='원문과 색인에 존재하는 물티슈를 물+티슈로 분해하는 수동 대체 후보입니다.',compound_expansions=[{'word':'물티슈','parts':['물','티슈']}])
    verdict,_=run_gate(engine,oldset,compound)
    report['known_failures']={'linked_candidates':candidates,'compound_manual_alternative':{'prescription':compound.model_dump(),'gate':asdict(verdict)}}
    patched=engine.with_config(config)
    combined_gate_before=evaluate_all(engine,oldset);combined_gate_after=evaluate_all(patched,oldset)
    report['combined_existing_36']={'before':{q:asdict(v) for q,v in combined_gate_before.items()},'after':{q:asdict(v) for q,v in combined_gate_after.items()},'mean_before':mean_ndcg(combined_gate_before),'mean_after':mean_ndcg(combined_gate_after)}
    rows=[{'case_id':c['id'],'query':c['query'],'qrels':c['qrels'],'family_hypothesis':c['family'],
           'before':metrics(engine,c),'after':metrics(patched,c)} for c in cases]
    eligible=[r for r in rows if r['qrels']]
    changes=[{'case_id':r['case_id'],'query':r['query'],'metric':m,'before':r['before'][m],'after':r['after'][m]} for r in eligible for m in ['ndcg','recall','precision_at_5'] if r['after'][m]<r['before'][m]]
    report['new_queries']={'rows':rows,'summary':{'ranked_n':len(eligible),'unanswerable_n':len(rows)-len(eligible),
        'mean_ndcg_before':round(sum(r['before']['ndcg'] for r in eligible)/len(eligible),4),
        'mean_ndcg_after':round(sum(r['after']['ndcg'] for r in eligible)/len(eligible),4),
        'improved_ndcg':sum(r['after']['ndcg']>r['before']['ndcg'] for r in eligible),
        'degraded_metrics':changes,'remaining_below_1':[r['case_id'] for r in eligible if r['after']['ndcg']<1],
        'unanswerable_with_results_before':sum(r['before']['n_results']>0 for r in rows if not r['qrels']),
        'unanswerable_with_results_after':sum(r['after']['n_results']>0 for r in rows if not r['qrels'])}}
    save()
    svc=ExplanationService(ClinicService(), retrieval_strategy='legacy')
    report['new_hint_ablation']=ablations(cases,svc)
    oldcases=json.loads((ROOT/'docs/verification/alba-20261027/cases.json').read_text(encoding='utf-8'))
    report['legacy_hint_ablation']=ablations([{'id':c['id'],'query':c['query'],'family':c['category'],
        'problem_hint':c['problem'],'problem_no_hint':'검색 결과를 점검해 주세요.'} for c in oldcases],svc)
    report['legacy_audit']=legacy_audit()
    report['not_run']=['new LLM hint/no-hint generation','new LLM abstention rate','independent human semantic adjudication','public production latency/load','real recruitment data']
    report['complete']=True;save()
    print(json.dumps({'new_queries':report['new_queries']['summary'],'new_hint_ablation':report['new_hint_ablation']['summary'],
        'legacy_hint_ablation':report['legacy_hint_ablation']['summary'],'known':[(c['query'],[(a['name'],a['gate']['accepted'],a['gate']['target_after']['ndcg']) for a in c['attempts']]) for c in candidates],
        'compound_gate':asdict(verdict),'new_api_calls':0},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
