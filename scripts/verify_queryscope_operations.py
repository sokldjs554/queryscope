"""Measure a real local HTTP process with paid generation disabled."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import httpx


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=False)
    # An explicit factory with provider=None makes the test independent of any API key.
    started=time.perf_counter()
    server=subprocess.Popen([sys.executable,'-m','uvicorn','searchclinic.api.explanation_api:create_explanation_app',
        '--factory','--host','127.0.0.1','--port','8766'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
        env={**os.environ,'CLINIC_ENABLE_LIVE':'0','CLINIC_MAX_CALLS':'0'})
    rows=[]
    try:
        with httpx.Client(base_url='http://127.0.0.1:8766',timeout=15) as client:
            for _ in range(150):
                if server.poll() is not None:raise RuntimeError('server_exited')
                try:
                    if client.get('/explanation-status').status_code==200:break
                except httpx.HTTPError:pass
                time.sleep(.1)
            else:raise RuntimeError('startup_timeout')
            cold_ms=round((time.perf_counter()-started)*1000,2)
            for path in ['/demo/','/demo/replay.json','/demo/evaluation.json','/explanation-status']:
                for _ in range(30):
                    t=time.perf_counter();r=client.get(path)
                    rows.append({'method':'GET','path':path,'status':r.status_code,'elapsed_ms':round((time.perf_counter()-t)*1000,3)})
            for body,expected in [({'query':'백팩'},503),({'query':''},422)]:
                t=time.perf_counter();r=client.post('/explanations',json=body)
                rows.append({'method':'POST','path':'/explanations','status':r.status_code,'expected':expected,'elapsed_ms':round((time.perf_counter()-t)*1000,3)})
                assert r.status_code==expected
            state=client.get('/explanation-status').json()
            assert state['live_enabled'] is False and state['metrics']['requests']==0
            assert all(r['status']==200 for r in rows if r['method']=='GET')
        values=sorted(r['elapsed_ms'] for r in rows if r['method']=='GET')
        import math
        report={'created_at':datetime.now(timezone.utc).isoformat(),'scope':'single local loopback process, sequential warmed GETs; no model latency or production SLA',
            'new_api_calls':0,'cold_start_ms':cold_ms,'warmed_gets':len(values),'p50_ms':values[len(values)//2],
            'p95_ms':values[math.ceil(.95*len(values))-1],'max_ms':max(values),
            'status_counts':dict(Counter(str(r['status']) for r in rows)),'server_state':state,'rows':rows,'passed':True}
        (args.output/'operations.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        print(json.dumps({k:v for k,v in report.items() if k!='rows'},ensure_ascii=False))
    finally:
        server.terminate()
        try:server.wait(timeout=10)
        except subprocess.TimeoutExpired:server.kill();server.wait()

if __name__=='__main__':main()
