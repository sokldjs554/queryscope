"""Frozen v3 controlled positives/healthy negatives; v1/v2 are development."""
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
import subprocess
from searchclinic.analysis.config import AnalyzerConfig
from searchclinic.corpus.catalog import load_catalog
from searchclinic.index.engine import SearchEngine
from searchclinic.rag.retriever import KnowledgeRetriever
from searchclinic.evaluation.controlled_cases import validate_controls
from searchclinic.evaluation.queryscope_v2 import ROOT,load_bundle,file_sha,write_json,compare_retrieval,compare_ranking


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args();bundle=load_bundle(ROOT/'docs/verification/queryscope-v3')
    args.output.mkdir(parents=True,exist_ok=False)
    engine=SearchEngine(bundle['catalog'],AnalyzerConfig(**bundle['rubric']['search_config']))
    controls,repaired_config=validate_controls(bundle,engine)
    report={'created_at':datetime.now(timezone.utc).isoformat(),'new_api_calls':0,'complete':False,
            'commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
            'frozen_manifest':bundle['manifest'],'controls':controls,
            'source_sha256':{str(p.relative_to(ROOT)):file_sha(p) for p in sorted((ROOT/'src/searchclinic').rglob('*.py'))},
            'runner_sha256':file_sha(Path(__file__))}
    def save():write_json(args.output/'results.json',report)
    save()
    if not controls['passed']:raise ValueError('control_precondition_failed; no scores calculated')
    retriever=KnowledgeRetriever();strategies=('observed_v2','observed_v3')
    report['new_retrieval']=compare_retrieval(engine,retriever,bundle['cases'],bundle['rubric']['retrieval']['relevant_ids'],strategies)
    report['healthy_gap_signals']={}
    healthy_ids={c['id'] for c in bundle['cases'] if c['category']=='healthy'}
    for condition in ['hint','no_hint']:
        report['healthy_gap_signals'][condition]={s:{'n':len(healthy_ids),'flagged_ids':[
            r['case_id'] for r in report['new_retrieval']['rows'] if r['case_id'] in healthy_ids and any(
                x['kind']=='raw_substring_token_gap' for x in r['conditions'][condition][s]['context']['retrieval']['signals'])]} for s in strategies}
    report['controlled_counterfactual_ranking']=compare_ranking(engine,engine.with_config(repaired_config),bundle['cases'])
    report['counterfactual_scope']='Only reconstruction interventions mandated by control construction, not newly discovered automatic repairs.'
    v2=load_bundle(ROOT/'docs/verification/queryscope-v2')
    report['v2_development_retrieval']=compare_retrieval(SearchEngine(v2['catalog']),retriever,v2['cases'],v2['rubric']['retrieval']['relevant_ids'],strategies)
    v1=json.loads((ROOT/'docs/verification/queryscope-v1/cases.json').read_text(encoding='utf-8'))
    report['v1_development_retrieval']=compare_retrieval(SearchEngine(load_catalog()),retriever,v1,bundle['rubric']['retrieval']['relevant_ids'],strategies)
    old_docs=load_catalog()+v2['catalog'];old_tokens=set(SearchEngine(old_docs).vocabulary());new_tokens=set(engine.vocabulary())
    report['novelty']={'author':'Codex-authored controlled/synthetic data, not customer records or independent human evaluation',
        'old_documents':len(old_docs),'new_documents':len(bundle['catalog']),
        'query_exact_overlap':0,'title_exact_overlap':sorted({d.name for d in old_docs}&{d.name for d in bundle['catalog']}),
        'new_token_count':len(new_tokens),'shared_tokens':sorted(old_tokens&new_tokens),
        'shared_token_fraction':round(len(old_tokens&new_tokens)/len(new_tokens),4),
        'limitations':['forced atomic indexing for 4 positives','shared Korean product domain and knowledge','shared suffix patterns and author','unadjudicated semantic relations','no new garbage_split coverage']}
    report['not_run']=['actual new LLM generation','independent human semantics/qrels','customer generalization','public HTTP availability']
    report['complete']=True;save()
    print(json.dumps({k:(v['summary'] if k.endswith('retrieval') else v) for k,v in report.items()
        if k in ['new_retrieval','healthy_gap_signals','v1_development_retrieval','v2_development_retrieval']},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
