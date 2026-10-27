"""One repository-wide claim for the explicitly approved v3 campaign. No model calls."""
import os
import re
import httpx
from searchclinic.evaluation.llm_campaign import check_approval

PREPARED_SHA='dfb4442ed8935b804cecfb5428ac374a765862c9ee96354cd8ddba556bdf3dfb'
REPOSITORY='sokldjs554/queryscope'
CLAIM_REF='refs/tags/queryscope-v3-paid-'+PREPARED_SHA


def claim(client,commit,token,attempt):
    if attempt!='1':raise ValueError('rerun_not_authorized')
    if not re.fullmatch('[0-9a-f]{40}',commit):raise ValueError('invalid_commit')
    if not token:raise ValueError('github_token_missing')
    # POST creates a ref atomically. Existing refs fail even at the same commit.
    response=client.post(f'https://api.github.com/repos/{REPOSITORY}/git/refs',
        headers={'Authorization':'Bearer '+token,'Accept':'application/vnd.github+json',
                 'X-GitHub-Api-Version':'2022-11-28'},
        json={'ref':CLAIM_REF,'sha':commit})
    if response.status_code!=201:
        raise RuntimeError(f'remote_claim_failed_{response.status_code}')


def main():
    if os.environ.get('GITHUB_REPOSITORY')!=REPOSITORY:
        raise ValueError('wrong_repository')
    approval=check_approval('docs/verification/queryscope-v3/llm-prepared-v1',
                            'docs/verification/queryscope-v3/actual-api-approval.json')
    if approval['prepared_sha256']!=PREPARED_SHA or approval['suite']!='queryscope-v3':
        raise ValueError('wrong_campaign')
    with httpx.Client(timeout=30,follow_redirects=False) as client:
        claim(client,os.environ['GITHUB_SHA'],os.environ['GH_TOKEN'],os.environ['GITHUB_RUN_ATTEMPT'])
    print('Repository claim created. This approval cannot be automatically reused.')

if __name__=='__main__':main()
