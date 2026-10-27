"""Validate authored control construction; this is not human semantic judgment."""
from searchclinic.patch.ir import Prescription


def validate_controls(bundle,engine):
    rows=[];config=engine.config
    for case in bundle['cases']:
        if case['category']=='healthy':
            hits=engine.search(case['query'],k=1)
            rows.append({'id':case['id'],'check':'healthy_top1','passed':bool(hits) and hits[0].doc_id in case['qrels']})
        if case['reference_status']=='controlled_token_gap':
            target=next(iter(case['qrels']))
            word=engine.docs[target].name;query=case['query']
            structural=word.endswith(query) and word!=query
            if not structural:
                rows.append({'id':case['id'],'check':'compound_reconstruction','passed':False});continue
            rx=Prescription(target_query=query,diagnosis_family='compound_locked',
                reasoning='통제된 통짜 색인을 재구성 분해하여 누락이 복구되는지 확인하는 사전조건입니다.',
                compound_expansions=[{'word':word,'parts':[word[:-len(query)],query]}])
            repaired=engine.with_config(rx.apply_to(engine.config))
            query_tokens=engine.analyzer.tokens(query);doc_tokens=engine.doc_tokens(target)
            after=repaired.search(query,k=1)
            passed=bool(query_tokens) and not set(query_tokens).issubset(doc_tokens) and (
                any(d.doc_id==target for d in engine.grep_raw(query)) and not engine.search(query) and
                bool(after) and after[0].doc_id==target)
            rows.append({'id':case['id'],'check':'controlled_atomic_gap_and_recovery','passed':passed,
                         'query_tokens':query_tokens,'document_tokens':doc_tokens,
                         'counterfactual':rx.model_dump()})
            config=rx.apply_to(config)
    return {'passed':all(r['passed'] for r in rows),'rows':rows},config
