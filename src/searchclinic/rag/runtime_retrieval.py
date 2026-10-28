"""Versioned runtime-only retrieval of lexical catalog hypotheses.

Frozen observation strategies and campaign contexts remain unchanged. A matching
product description supplies inspection candidates, never synonym approval.
"""
from __future__ import annotations

import hashlib
import re

from searchclinic.rag.knowledge import KnowledgeDoc
from searchclinic.rag.observations import PROBES, build_context, excerpt

# Request boilerplate and generic product nouns cannot establish a useful match.
# These are retrieval stopwords, not evaluation vocabulary or diagnosis labels.
_GENERIC_TERMS = frozenset({
    '찾', '상품', '물품', '도구', '기구', '장치', '결과', '검색', '표현',
    '이름', '요청', '확인', '점검', '원하', '처리', '정보', '제공', '판단',
    '주', '하', '있', '없', '해당', '원인', '자료', '연결', '문제',
})
RUNTIME_VERSION = 'description_fallback_v1'


def build_runtime_retrieval_context(engine, retriever, query: str, problem: str):
    """Expose up to two description matches after a zero-hit direct query.

    Require two distinct non-boilerplate matched tokens, at least one of length
    two, to avoid deriving a script hypothesis from generic request overlap.
    This conservative lexical gate does not validate identity or equivalence.
    """
    context, docs = build_context(engine, retriever, query, problem, strategy='observed')
    context['retrieval'].update(strategy='runtime_description', version=RUNTIME_VERSION,
                                base_strategy='observed_v3')
    context['catalog_candidates'] = []
    if context['search']['total']:
        return context, docs

    for hit in engine.search(problem, k=6):
        informative = [t for t in hit.matched_terms if t not in _GENERIC_TERMS]
        if len(set(informative)) < 2 or not any(len(t) >= 2 for t in informative):
            continue
        product = engine.docs[hit.doc_id]
        context['catalog_candidates'].append({
            'id': product.doc_id, 'name': product.name[:80],
            'description': product.description[:180],
            'matched_terms': informative[:8],
            'provenance': 'problem_text_lexical_search',
            'semantic_equivalence': 'unverified',
        })
        if len(context['catalog_candidates']) == 2:
            break

    candidates = context['catalog_candidates']
    names = ' '.join(c['name'] for c in candidates)
    different_scripts = (
        re.search('[A-Za-z]', query) and re.search('[가-힣]', names)
    ) or (
        re.search('[가-힣]', query) and re.search('[A-Za-z]', names)
    )
    if not different_scripts:
        return context, docs

    context['retrieval']['signals'].append({
        'kind': 'different_scripts', 'catalog_names': [c['name'] for c in candidates],
        'provenance': 'problem_text_lexical_search',
        'semantic_equivalence': 'unverified',
    })
    probe = PROBES['different_scripts']
    context['retrieval']['probe_queries'].append(probe)
    retrieval_query = context['retrieval']['query'] + ' ' + probe
    context['retrieval']['query'] = retrieval_query
    new_hits = retriever.retrieve(probe, k=1)
    if not new_hits:
        return context, docs

    source = new_hits[0].doc
    # Reuse the existing exact-source window and provenance representation.
    body, start, end = excerpt(source.body, retrieval_query, engine.analyzer)
    item = {'id': source.doc_id, 'title': source.title, 'body': body,
            'source': source.source, 'body_start': start, 'body_end': end,
            'full_body_sha256': hashlib.sha256(source.body.encode()).hexdigest()}
    context['documents'] = ([item] + [d for d in context['documents']
                                     if d['id'] != source.doc_id])[:3]
    docs = [KnowledgeDoc(d['id'], d['title'], d['body'], d['source'])
            for d in context['documents']]
    return context, docs
