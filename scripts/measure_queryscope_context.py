"""Local context-build latency, alternating strategies; never constructs a provider."""
import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import time
from searchclinic.service import ClinicService
from searchclinic.rag.explanation_service import ExplanationService


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--baseline',choices=['legacy','observed_v2'],default='legacy')
    args=parser.parse_args()
    strategies=[args.baseline,'observed']
    args.output.mkdir(parents=True,exist_ok=False)
    root=Path(__file__).resolve().parents[1]
    cases=json.loads((root/'docs/verification/queryscope-v1/cases.json').read_text(encoding='utf-8'))
    start=time.perf_counter()
    clinic=ClinicService()
    services={s:ExplanationService(clinic,retrieval_strategy=s) for s in strategies}
    initialization=(time.perf_counter()-start)*1000
    rows=[]
    for i,case in enumerate(cases):
        for strategy in (strategies if i%2==0 else list(reversed(strategies))):
            start=time.perf_counter()
            context,_=services[strategy].context(case['query'],case['problem_no_hint'])
            elapsed=(time.perf_counter()-start)*1000
            rows.append({'case_id':case['id'],'strategy':strategy,'milliseconds':round(elapsed,3),
                         'documents':len(context['documents']),'status':'completed'})
    summary={}
    for strategy in services:
        times=sorted(r['milliseconds'] for r in rows if r['strategy']==strategy)
        summary[strategy]={'n':len(times),'p50_ms':times[math.ceil(len(times)*.5)-1],
                           'p95_ms':times[math.ceil(len(times)*.95)-1],'max_ms':times[-1]}
    report={'created_at':datetime.now(timezone.utc).isoformat(),
        'scope':'one local process, 72 catalog items, 24 development queries once per strategy, alternating order; context build only, no generation/network/production load',
        'initialization_ms':round(initialization,3),'new_api_calls':0,'summary':summary,'rows':rows}
    (args.output/'context-latency.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(summary))

if __name__=='__main__':main()
