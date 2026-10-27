"""Explicit operator candidates, never inferred semantic equivalence or model output.

A user-word-only patch can repair tokenization without linking to the catalog.
The caller supplies the proposed canonical term; the gate still decides effect.
"""
from searchclinic.index.engine import SearchEngine
from searchclinic.patch.ir import Prescription


def build_link_candidate(engine: SearchEngine, query: str, canonical: str) -> Prescription:
    if not query or not canonical or any(c.isspace() for c in query+canonical):
        raise ValueError('single_word_required')
    if canonical.lower() not in engine.vocabulary():
        raise ValueError('canonical_not_in_index')
    if query.lower() == canonical.lower():
        raise ValueError('distinct_terms_required')
    words=[] if engine.analyzer.tokens(query)==[query.lower()] else [{'form':query}]
    return Prescription(target_query=query,diagnosis_family='garbage_split',
        reasoning='운영자가 제안한 표준형 연결 후보입니다. 단일 토큰 보존과 색인 연결을 함께 검증하며 동의성은 별도 검토해야 합니다.',
        user_words=words,synonym_groups=[{'terms':[canonical,query]}])
