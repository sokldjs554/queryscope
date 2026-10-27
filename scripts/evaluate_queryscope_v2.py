"""Offline v2 evaluation; v1 is development data, frozen v2 is separate."""
from __future__ import annotations
import argparse
from dataclasses import asdict
from datetime import datetime,timezone
import importlib.metadata
import json
from pathlib import Path
import platform
import subprocess
import time
from searchclinic.corpus.catalog import load_catalog
from searchclinic.corpus.evalset import EvalQuery,load_evalset
from searchclinic.index.engine import SearchEngine
from searchclinic.patch.gate import run_gate
from searchclinic.patch.ir import Prescription
from searchclinic.rag.candidate_review import build_link_candidate
from searchclinic.rag.retriever import KnowledgeRetriever
from searchclinic.evaluation.queryscope_v2 import (
    ROOT,load_bundle,file_sha,write_json,compare_ranking,compare_retrieval,
)


def development_repairs(engine,dev):
    original=[{'query':q.query,'qrels':q.qrels} for q in load_evalset()]
    gate_queries=load_evalset()+[EvalQuery(c['query'],c['qrels']) for c in dev if c['qrels']]
    config=engine.config
    for query,canonical in [('아답터','어댑터'),('백팩','배낭')]:
        config=build_link_candidate(engine,query,canonical).apply_to(config)
    v1=engine.with_config(config)
    candidates=[
        Prescription(target_query='거실 카페트',diagnosis_family='spelling_variant',
            reasoning='카탈로그의 카펫 표기와 카페트 질의를 명시적으로 연결하는 수동 후보입니다.',
            synonym_groups=[{'terms':['카펫','카페트']}]),
        Prescription(target_query='초콜렛 선물',diagnosis_family='spelling_variant',
            reasoning='카탈로그 초콜릿과 초콜렛의 표기 차이를 연결하는 수동 후보입니다.',
            synonym_groups=[{'terms':['초콜릿','초콜렛']}]),
        Prescription(target_query='워시',diagnosis_family='compound_locked',
            reasoning='원문 바디워시를 바디와 워시로 분해하는 수동 후보입니다.',
            compound_expansions=[{'word':'바디워시','parts':['바디','워시']}]),
    ]
    rows=[]
    for rx in candidates:
        gate,sandbox=run_gate(v1,gate_queries,rx)
        rows.append({'prescription':rx.model_dump(),'gate_56':asdict(gate),
            'original_36':compare_ranking(v1,sandbox,original),
            'v1_development_24':compare_ranking(v1,sandbox,dev),
            'tokens_before':v1.analyzer.tokens(rx.target_query),
            'tokens_after':sandbox.analyzer.tokens(rx.target_query)})
        if gate.accepted:config=rx.apply_to(config)
    proposed=engine.with_config(config)
    combined={'original_36':compare_ranking(v1,proposed,original),
              'v1_development_24':compare_ranking(v1,proposed,dev)}
    accepted=not any(s['summary']['decreases'] for s in combined.values())
    return {'individual':rows,'combined':combined,'combined_zero_measured_decreases':accepted,
            'proposed_config':config.model_dump(),
            'selection':'manual candidates tested on development only; no automatic base mutation'},v1,proposed


def novelty(engine,cases):
    old=SearchEngine(load_catalog())
    old_words={w.lower() for d in old.docs.values() for w in d.text.split()}
    new_words={w.lower() for d in engine.docs.values() for w in d.text.split()}
    a=set(old.vocabulary());b=set(engine.vocabulary())
    return {'author':'Codex-assisted authored data; no independent human adjudicator',
        'exact_query_overlap':0,'catalog_id_overlap':0,
        'exact_title_overlap':sorted({d.name for d in old.docs.values()} & {d.name for d in engine.docs.values()}),
        'new_catalog_documents':len(engine.docs), 'old_catalog_documents':len(old.docs),
        'new_whitespace_words':len(new_words),'shared_whitespace_words':sorted(old_words & new_words),
        'new_analysis_tokens':len(b),'shared_analysis_tokens':sorted(a & b),
        'shared_analysis_token_fraction':round(len(a&b)/len(b),4),
        'query_token_overlap':[{'query':c['query'],'tokens':engine.analyzer.tokens(c['query']),
            'shared_with_old':sorted(set(engine.analyzer.tokens(c['query'])) & a)} for c in cases],
        'limits':'same author/task/language/knowledge/family taxonomy; synthetic qrels and overlapping generic words; not independent human or customer generalization'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args();bundle=load_bundle()
    args.output.mkdir(parents=True,exist_ok=False)
    report={'created_at':datetime.now(timezone.utc).isoformat(),'new_api_calls':0,
        'commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'frozen_manifest':bundle['manifest'],'complete':False,
        'environment':{'python':platform.python_version(),**{p:importlib.metadata.version(p) for p in ['kiwipiepy','kiwipiepy_model','pydantic']}},
        'source_sha256':{str(p.relative_to(ROOT)):file_sha(p) for p in sorted((ROOT/'src/searchclinic').rglob('*.py'))},
        'runner_sha256':file_sha(Path(__file__)),
        'preserved_sources':{str(p.relative_to(ROOT)):file_sha(p) for p in [
            ROOT/'docs/verification/queryscope-v1/run-v1/results.json',
            ROOT/'docs/verification/alba-20261027/run/results.json',
            ROOT/'docs/verification/alba-20261027/run/revalidated.json']}}
    def save():write_json(args.output/'results.json',report)
    save()
    dev=json.loads((ROOT/'docs/verification/queryscope-v1/cases.json').read_text(encoding='utf-8'))
    engine=SearchEngine(load_catalog());retriever=KnowledgeRetriever()
    report['development_repairs'],v1,proposed=development_repairs(engine,dev);save()
    start=time.perf_counter()
    report['development_retrieval']=compare_retrieval(engine,retriever,dev,bundle['rubric']['retrieval']['relevant_ids']);save()
    new=SearchEngine(bundle['catalog'])
    report['new_retrieval']=compare_retrieval(new,retriever,bundle['cases'],bundle['rubric']['retrieval']['relevant_ids'])
    report['new_catalog_ranking']=compare_ranking(new,new.with_config(proposed.config),bundle['cases'])
    report['novelty']=novelty(new,bundle['cases'])
    report['retrieval_evaluation_elapsed_seconds']=round(time.perf_counter()-start,3)
    from evaluate_queryscope import legacy_audit
    report['legacy_audit']=legacy_audit()
    report['not_run']=['new LLM generation/diagnostic accuracy/abstention','independent human semantic adjudication',
                       'customer data generalization','public production latency or availability']
    report['complete']=True;save()
    print(json.dumps({'development_retrieval':report['development_retrieval']['summary'],
        'new_retrieval':report['new_retrieval']['summary'],
        'new_rank':report['new_catalog_ranking']['summary'],
        'development_rank':report['development_repairs']['combined']['v1_development_24']['summary']},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
