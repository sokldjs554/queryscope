"""Catalog observations for retrieval, never evaluation labels or diagnoses.

All heuristics are deliberately visible. A spelling neighbor is not a synonym,
and a raw substring is not proof of a valid compound boundary.
"""
from __future__ import annotations
import hashlib
import re
from functools import lru_cache
from searchclinic.analysis.jamo import jamo_similarity
from searchclinic.rag.knowledge import KnowledgeDoc

PROBES = {
    'fragmented_surface': '형태소 분석기 짧은 음절 분해 감탄사 사용자 사전 원자 토큰 표준형 연결',
    'raw_substring_token_gap': '복합어 통짜 부분어 색인 분해 확장 원문 대조',
    'near_spelling': '외래어 표준 표기 관용 표기 자모 편집 거리 동의어',
    'different_scripts': '영한 혼용 로마자 한글 음차 문자 체계 표기',
}


def model_context(full):
    """Keep retrieval probes out of model instructions; send compact observations."""
    result={k:full[k] for k in ['query','problem','analysis','search']}
    result['documents']=[{k:d[k] for k in ['id','title','body','source']} for d in full['documents']]
    result['observations']={'status':'observations_not_diagnosis',
                            'signals':full.get('retrieval',{}).get('signals',[])[:4]}
    return result


def observe(engine, query: str, *, token_coverage: bool = True) -> list[dict]:
    """Finite catalog/token probes; no knowledge family metadata is inspected."""
    signals = []
    vocab = set(engine.vocabulary())
    for surface in re.findall(r'[가-힣A-Za-z0-9]+', query)[:8]:
        word = surface.lower()
        tokens = engine.analyzer.tokens(surface)
        dropped = engine.analyzer.dropped(surface)
        if any(tag == 'IC' for _, tag in dropped) or sum(len(t) == 1 for t in tokens) >= 2:
            signals.append({'kind':'fragmented_surface','surface':surface,'tokens':tokens,
                            'dropped':dropped})
        raw = engine.grep_raw(surface, limit=3) if len(word) >= 2 else []
        # A removed suffix is not missing content: 휴대용 -> 휴대 may be fully
        # represented in the index. Compare actual query tokens, not surface text.
        if token_coverage:
            gaps = [d for d in raw if tokens and not set(tokens).issubset(engine.doc_tokens(d.doc_id))]
        else:
            gaps = [d for d in raw if word not in engine.doc_tokens(d.doc_id)]
        if gaps:
            signals.append({'kind':'raw_substring_token_gap','surface':surface,
                            'documents':[{'id':d.doc_id,'name':d.name,
                                          'tokens':engine.doc_tokens(d.doc_id)[:24]} for d in gaps]})
        if word not in vocab and re.fullmatch(r'[가-힣]{2,}', word):
            neighbors = sorted([(jamo_similarity(word, v), v) for v in vocab
                                if re.fullmatch(r'[가-힣]{2,}', v)], key=lambda x:(-x[0], x[1]))
            for score, candidate in neighbors[:2]:
                if score >= .65:
                    signals.append({'kind':'near_spelling','surface':surface,
                                    'candidate':candidate,'similarity':round(score,4),
                                    'semantic_equivalence':'unverified'})
    top = [engine.docs[h.doc_id] for h in engine.search(query, k=3)]
    if (re.search('[A-Za-z]', query) and re.search('[가-힣]', ''.join(d.name for d in top))) or (
        re.search('[가-힣]', query) and re.search('[A-Za-z]', ''.join(d.name for d in top))
    ):
        signals.append({'kind':'different_scripts','catalog_names':[d.name for d in top]})
    return signals[:10]


@lru_cache(maxsize=512)
def _window_terms(analyzer, text):
    return frozenset(analyzer.tokens(text))


def excerpt(body: str, retrieval_query: str, analyzer, limit: int = 400, *, cached=True) -> tuple[str,int,int]:
    """Select a contiguous source window; keep offsets into the exact original."""
    if len(body) <= limit:
        return body, 0, len(body)
    terms = set(analyzer.tokens(retrieval_query))
    starts = {0, *(m.end() for m in re.finditer(r'\n\s*\n', body))}
    for term in terms:
        if len(term) >= 2:
            starts.update(max(0,m.start()-60) for m in re.finditer(re.escape(term),body))
    def score(start):
        window=body[start:start+limit]
        tokens = _window_terms(analyzer,window) if cached else set(analyzer.tokens(window))
        return len(terms & tokens), -start
    start = max(starts,key=score)
    end = min(len(body),start+limit)
    return body[start:end],start,end


def build_context(engine, retriever, query: str, problem: str, strategy: str = 'observed'):
    if strategy not in {'legacy','observed','observed_v2'}:
        raise ValueError('unknown_retrieval_strategy')
    analysis={'text':query,'session_id':None,'tokens':engine.analyzer.explain(query),
              'dropped':[{'token':t,'tag':tag} for t,tag in engine.analyzer.dropped(query)]}
    hits=engine.search(query,k=3)
    search={'query':query,'session_id':None,'total':len(hits),'results':[
        {'doc_id':h.doc_id,'name':engine.docs[h.doc_id].name,'score':h.score,
         'matched_terms':list(h.matched_terms)} for h in hits]}
    is_observed=strategy!='legacy'
    signals=observe(engine,query,token_coverage=strategy!='observed_v2') if is_observed else []
    probes=list(dict.fromkeys(PROBES[s['kind']] for s in signals))
    retrieval_query=query+' '+problem+(' '+' '.join(probes) if probes else '')
    chosen=[]
    # Preserve distinct observable signals: incidental Latin model names must not
    # crowd out a dropped syllable. Every probe uses normal BM25, never doc labels.
    probe_queries=[]
    if is_observed:
        kinds={s['kind'] for s in signals}
        for kind in ['raw_substring_token_gap','fragmented_surface','near_spelling','different_scripts']:
            if kind in kinds:
                probe_queries.append(PROBES[kind])
                for hit in retriever.retrieve(PROBES[kind],k=1):
                    if hit.doc.doc_id not in {h.doc.doc_id for h in chosen}:
                        chosen.append(hit)
    for hit in retriever.retrieve(retrieval_query,k=3):
        if hit.doc.doc_id not in {h.doc.doc_id for h in chosen}:
            chosen.append(hit)
    chosen=chosen[:3]
    docs=[]; rendered=[]
    for h in chosen:
        body,start,end=(excerpt(h.doc.body,retrieval_query,engine.analyzer,cached=strategy!='observed_v2') if is_observed
                        else (h.doc.body[:400],0,min(400,len(h.doc.body))))
        docs.append(KnowledgeDoc(h.doc.doc_id,h.doc.title,body,h.doc.source))
        item={'id':h.doc.doc_id,'title':h.doc.title,'body':body,'source':h.doc.source}
        if is_observed:
            item.update(body_start=start,body_end=end,
                        full_body_sha256=hashlib.sha256(h.doc.body.encode()).hexdigest())
        rendered.append(item)
    context={'query':query,'problem':problem,'analysis':analysis,'search':search,'documents':rendered}
    if is_observed:
        context['retrieval']={'strategy':'observed','query':retrieval_query,'probe_queries':probe_queries,'signals':signals,
                              'status':'observations_not_diagnosis'}
        if strategy=='observed':context['retrieval']['version']='v3'
    return context,docs
