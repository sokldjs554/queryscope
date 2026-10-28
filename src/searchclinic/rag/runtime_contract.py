"""Versioned runtime evidence policy and deterministic candidate applicability.

Historical campaign inputs and their validator remain unchanged. These checks
establish only source traceability and mechanical eligibility for the gate;
indexed terms and spelling neighbors never establish semantic equivalence.
"""
from __future__ import annotations

import re

from searchclinic.index.engine import SearchEngine
from searchclinic.rag.explanation import validate_explanation
from searchclinic.rag.knowledge import KnowledgeDoc
from searchclinic.rag.observations import model_context

RUNTIME_CONTRACT_VERSION = 'runtime-v4'
RUNTIME_SYSTEM = '''
Runtime evidence policy: only runtime_contract.citable_doc_ids identify citable
knowledge document bodies in documents. Catalog/search result IDs, product names,
analysis tokens and observation signals are not knowledge citations. Never use
them as evidence.doc_id. Quote an exact supplied knowledge body substring.
Search hit counts do not establish health or relevance; observations and spelling
similarity do not prove a cause or semantic equivalence. A synonym's first term
must be an actual indexed canonical token; a compound's whole must be an actual
indexed token. Target the query's observed surface/tokens. Abstain without patches
when support or applicability is insufficient. Human review and the regression
gate remain required; do not claim an improvement or semantic approval.'''


def build_runtime_context(full_context: dict, docs: list[KnowledgeDoc]) -> dict:
    """Publish a knowledge-only allowlist without promoting catalog observations."""
    context = model_context(full_context)
    # Use the retrieved KnowledgeDoc bodies accepted by citation validation,
    # rather than deriving trusted sources from IDs elsewhere in the context.
    context['documents'] = [
        {'id': doc.doc_id, 'title': doc.title, 'body': doc.body, 'source': doc.source}
        for doc in docs
    ]
    context['runtime_contract'] = {
        'version': RUNTIME_CONTRACT_VERSION,
        'citable_doc_ids': list(dict.fromkeys(doc.doc_id for doc in docs)),
        'catalog_and_observations': 'not_citable_knowledge',
        'search_counts': 'not_health_or_relevance_labels',
        'semantic_equivalence': 'requires_human_review',
    }
    if full_context.get('catalog_candidates'):
        context['observations']['catalog_candidates'] = full_context['catalog_candidates'][:2]
    return context


def validate_runtime_explanation(raw: dict, docs: list[KnowledgeDoc], query: str,
                                 engine: SearchEngine) -> dict:
    """Keep strict citation checks, then fail closed on inapplicable patches.

    An eligible result is still an unmeasured candidate requiring human review.
    Invalid candidates retain no executable prescription. Callers keep the raw
    generation separately so this safety decision cannot rewrite model evidence.
    """
    answer = validate_explanation(raw, docs, query)
    if answer['status'] != 'supported' or not answer['prescription']:
        return answer

    vocabulary = set(engine.vocabulary())
    query_terms = set(re.findall(r'[가-힣A-Za-z0-9]+', query.lower()))
    query_terms.update(engine.analyzer.tokens(query))
    for patch in answer['patches']:
        terms = [term.lower() for term in patch['terms']]
        reason = None
        if patch['kind'] == 'synonym' and terms[0] not in vocabulary:
            reason = 'canonical_not_in_index'
        elif patch['kind'] == 'compound' and terms[0] not in vocabulary:
            reason = 'compound_whole_not_in_index'
        elif not query_terms.intersection(terms[1:] if patch['kind'] == 'synonym' else terms):
            reason = 'patch_target_unrelated_to_query'
        if reason:
            answer.update(status='invalid', patches=[], prescription=None,
                          validation_error=reason)
            answer['assessment'].update(cause='requires_human_review',
                                        semantic_support='requires_human_review',
                                        patch_structure='no_executable_candidate')
            return answer
    return answer
