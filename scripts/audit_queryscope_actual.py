"""Offline secondary audit of frozen actual answers; never calls a provider.

The original primary verdicts remain unchanged. Raw patches with invalid citations
are measured only as counterfactuals in isolated engines, never applied to service.
"""
import argparse
from dataclasses import asdict
import json
import math
from pathlib import Path
from searchclinic.corpus import load_catalog,load_evalset
from searchclinic.corpus.evalset import EvalQuery
from searchclinic.index.engine import SearchEngine
from searchclinic.patch.ir import Prescription
from searchclinic.patch.gate import run_gate
from searchclinic.rag.explanation import Explanation,source_quote
from searchclinic.evaluation.llm_campaign import campaign_bundle,campaign_engine,summarize
from searchclinic.evaluation.queryscope_v2 import file_sha,write_json,compare_ranking


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--results',required=True,type=Path);p.add_argument('--output',required=True,type=Path)
    args=p.parse_args();raw=json.loads(args.results.read_text(encoding='utf-8'))
    if raw['mode']!='actual_api' or raw['suite']!='queryscope-v3':raise ValueError('wrong_source')
    args.output.mkdir(parents=True,exist_ok=False)
    bundle=campaign_bundle('queryscope-v3');engine=campaign_engine(bundle)
    new_eval=[EvalQuery(c['query'],c['qrels']) for c in bundle['cases'] if c['qrels']]
    old=SearchEngine(load_catalog());old_cases=[{'query':q.query,'qrels':q.qrels} for q in load_evalset()]
    rows=[]
    for r in raw['rows']:
        if r['generation_status']!='completed':continue
        answer=Explanation.model_validate(r['model_answer']);sources={d['id']:d for d in r['context']['documents']}
        row={'case_id':r['case_id'],'condition':r['condition'],'query':r['context']['query'],
             'response_id':r['generation']['response_id'],'primary_status':r['assessment']['validated_status'],
             'citation_checks':[],'semantic_support':'pending_independent_human_review',
             'raw_patch_structure':'no_patch','counterfactual_effect':{'status':'not_run'}}
        for e in answer.evidence:
            c={'doc_id':e.doc_id,'quote':e.quote,'status':'unknown_evidence_source'}
            if e.doc_id in sources:
                try:
                    matched,changed=source_quote(e.quote,sources[e.doc_id]['body'])
                    c.update(status='verified',matched_source=matched,display_format_recovered=changed,
                             excerpt_offset=sources[e.doc_id]['body'].find(matched))
                except ValueError:c['status']='text_mismatch'
            row['citation_checks'].append(c)
        if answer.patches:
            try:
                fields={'target_query':r['context']['query'],'diagnosis_family':answer.family,'reasoning':answer.summary,
                        'synonym_groups':[],'user_words':[],'compound_expansions':[]}
                for patch in answer.patches:
                    if patch.kind=='synonym':fields['synonym_groups'].append({'terms':patch.terms})
                    elif patch.kind=='user_word':
                        if len(patch.terms)!=1:raise ValueError('user_word_arity')
                        fields['user_words'].append({'form':patch.terms[0]})
                    else:fields['compound_expansions'].append({'word':patch.terms[0],'parts':patch.terms[1:]})
                rx=Prescription.model_validate(fields);rx.apply_to(engine.config)
                row['raw_patch_structure']='valid_structure_not_semantics'
                gate,sandbox=run_gate(engine,new_eval,rx)
                row['counterfactual_effect']={'status':'measured','primary_candidate_eligible':row['primary_status']=='supported',
                    'gate':asdict(gate),'new_16':compare_ranking(engine,sandbox,bundle['cases']),
                    'original_36_secondary_regression':compare_ranking(old,old.with_config(rx.apply_to(old.config)),old_cases)}
            except ValueError as e:
                row['raw_patch_structure']='invalid';row['structure_error']=type(e).__name__
        rows.append(row)
    times=sorted(r['generation']['latency_ms'] for r in raw['rows'] if 'generation' in r)
    usage={'input_tokens':sum(r['generation']['usage']['input_tokens'] for r in raw['rows'] if 'generation' in r),
           'output_tokens':sum(r['generation']['usage']['output_tokens'] for r in raw['rows'] if 'generation' in r)}
    report={'source_sha256':file_sha(args.results),'script_sha256':file_sha(Path(__file__)),
        'method':'post-run secondary diagnostic audit, no model calls, no changed primary verdicts; counterfactual patches never applied to production',
        'new_api_calls':0,'primary_summary_recomputed':summarize(raw['rows']),
        'usage':usage,'estimated_usd':round(raw['estimated_usd'],8),
        'api_latency_ms':{'n':len(times),'p50_nearest_rank':times[math.ceil(len(times)*.5)-1],
            'p95_nearest_rank':times[math.ceil(len(times)*.95)-1],'max':times[-1],
            'scope':'one sequential actual API batch, excludes search/gate/UI; not production SLA'},
        'rows':rows}
    assert report['primary_summary_recomputed']==raw['summary']
    write_json(args.output/'audit.json',report)
    print(json.dumps({'rows':len(rows),'usage':usage,'estimated_usd':report['estimated_usd']}))

if __name__=='__main__':main()
