"""Remote atomic claim prevents fresh Actions runners from reusing one approval."""
import importlib.util
from pathlib import Path
import httpx
import pytest


def module():
    path=Path(__file__).resolve().parents[1]/'scripts/claim_queryscope_campaign.py'
    spec=importlib.util.spec_from_file_location('campaign_claim',path)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result)
    return result


def test_same_commit_cannot_claim_campaign_twice():
    m=module();seen=[]
    def handler(request):
        assert request.url.host=='api.github.com'
        assert request.headers['Authorization']=='Bearer test-only'
        seen.append(request)
        return httpx.Response(201 if len(seen)==1 else 422,json={})
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        m.claim(client,'a'*40,'test-only','1')
        with pytest.raises(RuntimeError,match='remote_claim_failed_422'):
            m.claim(client,'a'*40,'test-only','1')
    assert len(seen)==2


@pytest.mark.parametrize('status',[401,403,500])
def test_claim_errors_fail_closed_without_retry(status):
    m=module();seen=[]
    def handler(request):
        seen.append(request);return httpx.Response(status,json={})
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(RuntimeError,match=f'remote_claim_failed_{status}'):
            m.claim(client,'a'*40,'test-only','1')
    assert len(seen)==1


def test_rerun_attempt_rejected_before_network():
    m=module()
    with httpx.Client(transport=httpx.MockTransport(lambda _:pytest.fail('network forbidden'))) as client:
        with pytest.raises(ValueError,match='rerun_not_authorized'):
            m.claim(client,'a'*40,'test-only','2')
