"""Exercise the real provider through in-memory HTTP, never a real API key."""
import json

import httpx
import pytest

from searchclinic.evaluation import runtime_campaign as campaign
from searchclinic.rag.openai_provider import MODEL


def setup_campaign(tmp_path, monkeypatch):
    prepared = tmp_path / 'prepared'
    campaign.prepare_runtime_campaign(prepared)
    approval = json.loads((prepared / 'approval-template.json').read_text(encoding='utf-8'))
    approval.update(approved=True, approved_by='temporary unit-test fixture only')
    target = tmp_path / 'test-approval.json'
    target.write_text(json.dumps(approval), encoding='utf-8')
    monkeypatch.setattr(campaign, 'CAMPAIGN_STATE_ROOT', tmp_path / 'state')
    for key, value in {'OPENAI_API_KEY': 'unit-test-not-a-real-key', 'GH_TOKEN': 'unit-test-token',
                       'GITHUB_REPOSITORY': 'sokldjs554/queryscope', 'GITHUB_SHA': 'a' * 40,
                       'GITHUB_RUN_ATTEMPT': '1', 'GITHUB_RUN_ID': 'unit-test'}.items():
        monkeypatch.setenv(key, value)
    return prepared, target


def envelope(number=1):
    answer = {'status': 'abstain', 'family': 'unknown', 'summary': '근거가 부족해 판단을 보류합니다.',
              'evidence': [], 'patches': []}
    return {'id': f'unit_response_{number}', 'model': MODEL, 'status': 'completed',
            'output': [{'type': 'message', 'content': [{'type': 'output_text', 'text': json.dumps(answer)}]}],
            'usage': {'input_tokens': 10, 'output_tokens': 2}}


def install_transport(monkeypatch, handler):
    original_client = httpx.Client
    monkeypatch.setattr(httpx, 'Client',
                        lambda *a, **kw: original_client(*a, transport=httpx.MockTransport(handler), **kw))


def test_remote_claim_is_required_even_with_a_fresh_local_state(tmp_path, monkeypatch):
    prepared, approval = setup_campaign(tmp_path, monkeypatch)
    calls = {'github': 0, 'model': 0}
    def handler(request):
        if request.url.host == 'api.github.com':
            calls['github'] += 1
            return httpx.Response(201 if calls['github'] == 1 else 422, json={})
        assert request.url.host == 'api.openai.com'
        calls['model'] += 1
        return httpx.Response(200, json=envelope(calls['model']))
    install_transport(monkeypatch, handler)
    campaign.execute_runtime_campaign(prepared, tmp_path / 'first', approval)
    monkeypatch.setattr(campaign, 'CAMPAIGN_STATE_ROOT', tmp_path / 'fresh-checkout-state')
    with pytest.raises(RuntimeError, match='remote_claim_failed_422'):
        campaign.execute_runtime_campaign(prepared, tmp_path / 'second', approval)
    assert calls == {'github': 2, 'model': 48}
    assert not (tmp_path / 'second').exists()


@pytest.mark.parametrize('kind', ['incomplete', 'refusal', 'invalid_json', 'missing_usage', 'http_error'])
def test_received_failure_envelope_survives_provider_parsing(tmp_path, monkeypatch, kind):
    prepared, approval = setup_campaign(tmp_path, monkeypatch)
    payload = envelope()
    status = 200
    if kind == 'incomplete':
        payload.update(status='incomplete', incomplete_details={'reason': 'max_output_tokens'})
    elif kind == 'refusal':
        payload['output'][0]['content'] = [{'type': 'refusal', 'refusal': 'cannot answer'}]
    elif kind == 'invalid_json':
        payload['output'][0]['content'][0]['text'] = '{not json'
    elif kind == 'missing_usage':
        del payload['usage']
    else:
        status = 503
        payload = {'error': {'type': 'upstream_error', 'message': 'unavailable'}}
    model_calls = []
    def handler(request):
        if request.url.host == 'api.github.com':
            return httpx.Response(201, json={})
        model_calls.append(request)
        if len(model_calls) > 1:
            raise RuntimeError('stop_after_first_received_response')
        return httpx.Response(status, json=payload)
    install_transport(monkeypatch, handler)
    output = tmp_path / 'out'
    with pytest.raises(RuntimeError, match='stop_after_first_received_response'):
        campaign.execute_runtime_campaign(prepared, output, approval)
    report = json.loads((output / 'results.json').read_text(encoding='utf-8'))
    row = report['rows'][0]
    assert row['generation_status'] == 'api_error'
    capture = row.get('http_response')
    assert capture is not None, 'paid HTTP response was discarded by provider parsing'
    assert json.loads((output / capture['body_path']).read_bytes()) == payload
    assert capture['http_status'] == status
    assert report['complete'] is False and report['responses'] == 0
    if 'usage' in payload:
        assert capture['usage'] == payload['usage']
        assert report['estimated_usd'] > 0


@pytest.mark.parametrize('kind', ['missing_model', 'wrong_model', 'missing_id', 'duplicate_id'])
def test_unproven_model_or_response_id_is_preserved_but_not_scored(tmp_path, monkeypatch, kind):
    prepared, approval = setup_campaign(tmp_path, monkeypatch)
    calls = []
    def handler(request):
        if request.url.host == 'api.github.com':
            return httpx.Response(201, json={})
        calls.append(request)
        payload = envelope(len(calls))
        if kind == 'missing_model':
            del payload['model']
        elif kind == 'wrong_model':
            payload['model'] = 'unapproved-model'
        elif kind == 'missing_id':
            del payload['id']
        else:
            payload['id'] = 'duplicate-response-id'
        return httpx.Response(200, json=payload)
    install_transport(monkeypatch, handler)
    output = tmp_path / 'out'
    with pytest.raises(RuntimeError, match='response_provenance_invalid'):
        campaign.execute_runtime_campaign(prepared, output, approval)
    report = json.loads((output / 'results.json').read_text(encoding='utf-8'))
    bad = report['rows'][-1]
    assert bad['generation_status'] == 'provenance_error'
    assert bad['model_answer'] is not None
    assert 'assessment' not in bad
    assert (output / bad['http_response']['body_path']).is_file()
    assert report['provenance_errors'] == 1
    assert report['responses'] == (1 if kind == 'duplicate_id' else 0)
    assert report['complete'] is False


def test_response_recording_redacts_exact_credential(tmp_path, monkeypatch):
    prepared, approval = setup_campaign(tmp_path, monkeypatch)
    calls = []
    def handler(request):
        if request.url.host == 'api.github.com':
            return httpx.Response(201, json={})
        calls.append(request)
        if len(calls) > 1:
            raise RuntimeError('stop_after_first_received_response')
        return httpx.Response(401, json={'error': {'message': 'Bad key: unit-test-not-a-real-key'}})
    install_transport(monkeypatch, handler)
    output = tmp_path / 'out'
    with pytest.raises(RuntimeError, match='stop_after_first_received_response'):
        campaign.execute_runtime_campaign(prepared, output, approval)
    files = [p for p in output.rglob('*') if p.is_file()]
    assert all(b'unit-test-not-a-real-key' not in p.read_bytes() for p in files)
    report = json.loads((output / 'results.json').read_text(encoding='utf-8'))
    capture = report['rows'][0].get('http_response')
    assert capture is not None and capture['secret_redacted'] is True
