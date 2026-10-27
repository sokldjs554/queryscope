"""Frozen authored evaluation; measurement labels never enter production inputs."""
from __future__ import annotations
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
from searchclinic.corpus.catalog import Document, load_catalog
from searchclinic.corpus.evalset import EvalQuery, load_evalset
from searchclinic.evaluation.metrics import evaluate_query
from searchclinic.patch.gate import run_gate
from searchclinic.patch.ir import Prescription
from searchclinic.rag.explanation import validate_explanation
from searchclinic.rag.knowledge import KnowledgeDoc
from searchclinic.rag.observations import build_context

ROOT=Path(__file__).resolve().parents[3]
DATA=ROOT/'docs/verification/queryscope-v2'


def file_sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def json_sha(obj):
    return hashlib.sha256(json.dumps(obj,ensure_ascii=False,sort_keys=True).encode()).hexdigest()


def write_json(path,obj):
    Path(path).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def load_bundle(path=DATA):
    path=Path(path)
    manifest=json.loads((path/'manifest.json').read_text(encoding='utf-8'))
    expected={'catalog.json','cases.json','rubric.json','PROTOCOL.md'}
    if set(manifest)!=expected:
        raise ValueError('invalid_frozen_manifest')
    for name,sha in manifest.items():
        if file_sha(path/name)!=sha:
            raise ValueError('frozen_input_changed: '+name)
    cases=json.loads((path/'cases.json').read_text(encoding='utf-8'))
    rubric=json.loads((path/'rubric.json').read_text(encoding='utf-8'))
    catalog=[Document(**d) for d in json.loads((path/'catalog.json').read_text(encoding='utf-8'))]
    old_queries={q.query for q in load_evalset()}
    sources=['queryscope-v1','alba-20261027']
    if rubric.get('version',2)>=3:
        sources.append('queryscope-v2')
    for source in sources:
        old_queries.update(c['query'] for c in json.loads((ROOT/'docs/verification'/source/'cases.json').read_text(encoding='utf-8')))
    if len({c['query'] for c in cases})!=len(cases) or old_queries & {c['query'] for c in cases}:
        raise ValueError('query_overlap')
    ids={d.doc_id for d in catalog}
    if len(ids)!=len(catalog) or any(set(c['qrels'])-ids for c in cases):
        raise ValueError('invalid_catalog_qrels')
    if ids & {d.doc_id for d in load_catalog()}:
        raise ValueError('catalog_id_overlap')
    return {'cases':cases,'catalog':catalog,'manifest':manifest,
            'rubric':rubric}


def rank(engine,case):
    hits=engine.search(case['query'],k=10)
    metrics=asdict(evaluate_query(engine,EvalQuery(case['query'],case['qrels'])))
    metrics['precision5_returned_denominator']=metrics.pop('precision5')
    metrics['precision_at_5']=round(sum(h.doc_id in case['qrels'] for h in hits[:5])/5,4)
    metrics['hits_at_10']=[h.doc_id for h in hits]
    if not case['qrels']:
        for k in ['ndcg','recall','precision_at_5','precision5_returned_denominator']:
            metrics[k]=None
    return metrics


def compare_ranking(before,after,cases):
    rows=[{'case_id':c.get('id'), 'query':c['query'],'qrels':c['qrels'],
           'before':rank(before,c),'after':rank(after,c)} for c in cases]
    eligible=[r for r in rows if r['qrels']]
    return {'rows':rows,'summary':{
        'ranked':len(eligible),'excluded':len(rows)-len(eligible),
        **{f'mean_ndcg_{stage}':round(sum(r[stage]['ndcg'] for r in eligible)/len(eligible),4)
           if eligible else None for stage in ['before','after']},
        'improved':sum(r['after']['ndcg']>r['before']['ndcg'] for r in eligible),
        'decreases':[{'query':r['query'],'metric':m,'before':r['before'][m],'after':r['after'][m]}
            for r in eligible for m in ['ndcg','recall','precision_at_5'] if r['after'][m]<r['before'][m]],
        'remaining_below_one':[r['query'] for r in eligible if r['after']['ndcg']<1]}}


def paired_context(engine,retriever,case,condition,strategy):
    # Preserve the v2 benchmark exactly; v3 evaluation calls build_context directly.
    context,docs=build_context(engine,retriever,case['query'],case['problem_'+condition],
                               {'observed':'observed_v2','observed_v3':'observed'}.get(strategy,strategy))
    if not case.get('documents_available',True):
        context['documents']=[];docs=[]
    return context,docs


def compare_retrieval(engine,retriever,cases,relevance,strategies=('legacy','observed')):
    rows=[]
    for case in cases:
        family=case.get('family_hypothesis',case.get('family'))
        relevant=relevance.get(family,[])
        row={'case_id':case['id'],'query':case['query'],'family_hypothesis':family,
             'relevant_ids':relevant,'conditions':{}}
        for condition in ['hint','no_hint']:
            row['conditions'][condition]={}
            for strategy in strategies:
                context,_=paired_context(engine,retriever,case,condition,strategy)
                ids=[d['id'] for d in context['documents']]
                rr=next((1/i for i,d in enumerate(ids,1) if d in relevant),0)
                row['conditions'][condition][strategy]={'context':context,'context_sha256':json_sha(context),
                    'retrieved_ids':ids,'hit_at_3':bool(rr) if relevant else None,
                    'mrr_at_3':rr if relevant else None,'model_answer':None,'generation_status':'not_run'}
        rows.append(row)
    def summarize(subset):
        result={}
        for condition in ['hint','no_hint']:
            result[condition]={}
            for strategy in strategies:
                scores=[r['conditions'][condition][strategy] for r in subset if r['relevant_ids']]
                n=len(scores)
                result[condition][strategy]={'eligible':n,'hits':sum(s['hit_at_3'] for s in scores),
                    'mrr_at_3':round(sum(s['mrr_at_3'] for s in scores)/n,4) if n else None,
                    'failures':[r['case_id'] for r in subset if r['relevant_ids'] and not r['conditions'][condition][strategy]['hit_at_3']]}
        return result
    return {'summary':summarize(rows),'per_family':{f:summarize([r for r in rows if r['family_hypothesis']==f])
            for f in relevance},'rows':rows,'meaning':'family-principle retrieval, not diagnostic accuracy'}


def assess_generation(raw,context,case,engine,evalset):
    docs=[KnowledgeDoc(d['id'],d['title'],d['body'],d['source']) for d in context['documents']]
    validated=validate_explanation(raw,docs,case['query'])
    raw=raw if isinstance(raw,dict) else {}
    needs_abstain=case['expected_action']=='abstain_no_patch'
    valid=validated['status']!='invalid'
    assessment={
        'raw_status':raw.get('status'),'raw_family':raw.get('family'),
        'validated_status':validated['status'],'validation_error':validated['validation_error'],
        'cause_reference_status':case.get('reference_status','authored_reference'),
        'family_label_match':raw.get('family')==case['expected_family'] if case['expected_family'] else None,
        'appropriate_abstention_contract':(valid and raw.get('status')=='abstain' and not raw.get('patches')) if needs_abstain else None,
        'wrong_patch_on_abstain_required':bool(raw.get('patches')) if needs_abstain else None,
        'raw_patch_attempted':bool(raw.get('patches')),
        'citation_trace':validated['assessment']['citation_trace'],
        'semantic_support':'requires_independent_human_review',
        'patch_structure':validated['assessment']['patch_structure'],
        'patch_effect':{'status':'not_run'},'validated':validated,
    }
    if validated['prescription'] and case['qrels']:
        rx=Prescription.model_validate(validated['prescription'])
        verdict,sandbox=run_gate(engine,evalset,rx)
        assessment['patch_effect']={'status':'measured','gate':asdict(verdict),
            'all_queries':compare_ranking(engine,sandbox,[{'query':q.query,'qrels':q.qrels} for q in evalset])}
    return assessment
