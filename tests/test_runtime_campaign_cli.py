"""The v4 command and repository claim must not spend or reuse an approval."""
import importlib.util
from pathlib import Path

import httpx
import pytest


ROOT = Path(__file__).resolve().parents[1]


def script(name):
    path = ROOT / 'scripts' / name
    assert path.is_file(), f'v4 command is not implemented: {name}'
    spec = importlib.util.spec_from_file_location(name.replace('.', '_'), path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def claims():
    from searchclinic.evaluation import runtime_campaign_io
    return runtime_campaign_io


def test_default_cli_prepares_without_constructing_provider(tmp_path, monkeypatch, capsys):
    from searchclinic.rag import openai_provider
    monkeypatch.setenv('OPENAI_API_KEY', 'test-only-not-a-credential')
    monkeypatch.setattr(openai_provider, 'OpenAIExplainer',
                        lambda *a, **k: pytest.fail('free command constructed provider'))
    command = script('evaluate_queryscope_runtime_llm.py')
    output = tmp_path / 'prepared'
    command.main(['--output', str(output)])
    assert (output / 'requests.json').is_file()
    assert 'prepared=48' in capsys.readouterr().out
    command.main(['--validate-only', '--prepared', str(output)])
    assert 'validated=48' in capsys.readouterr().out
    assert not (output / 'results.json').exists()


def test_live_cli_requires_explicit_preparation_and_approval(tmp_path):
    command = script('evaluate_queryscope_runtime_llm.py')
    with pytest.raises(SystemExit) as error:
        command.main(['--live', '--output', str(tmp_path / 'out')])
    assert error.value.code == 2
    assert not (tmp_path / 'out').exists()


def test_remote_claim_is_atomic_and_not_reusable():
    command = claims()
    seen = []
    def handler(request):
        seen.append(request)
        assert request.url.host == 'api.github.com'
        return httpx.Response(201 if len(seen) == 1 else 422, json={})
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        command.claim(client, 'a' * 40, 'test-only', '1', 'b' * 64)
        with pytest.raises(RuntimeError, match='remote_claim_failed_422'):
            command.claim(client, 'a' * 40, 'test-only', '1', 'b' * 64)
    assert len(seen) == 2
    assert b'refs/tags/queryscope-v4-runtime-paid-' in seen[0].content
    assert b'queryscope-v3-paid-' not in seen[0].content


@pytest.mark.parametrize('status', [401, 403, 500])
def test_remote_claim_error_has_no_retry(status):
    command = claims()
    seen = []
    def handler(request):
        seen.append(request)
        return httpx.Response(status, json={})
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(RuntimeError, match=f'remote_claim_failed_{status}'):
            command.claim(client, 'a' * 40, 'test-only', '1', 'b' * 64)
    assert len(seen) == 1


@pytest.mark.parametrize('commit,token,attempt,identity,error', [
    ('a' * 40, 'test-only', '2', 'b' * 64, 'rerun_not_authorized'),
    ('bad', 'test-only', '1', 'b' * 64, 'invalid_commit'),
    ('a' * 40, '', '1', 'b' * 64, 'github_token_missing'),
    ('a' * 40, 'test-only', '1', 'bad', 'invalid_campaign_identity'),
])
def test_bad_claim_metadata_is_rejected_before_network(commit, token, attempt, identity, error):
    command = claims()
    with httpx.Client(transport=httpx.MockTransport(lambda _: pytest.fail('network forbidden'))) as client:
        with pytest.raises(ValueError, match=error):
            command.claim(client, commit, token, attempt, identity)


def test_wrong_repository_is_rejected_before_network(monkeypatch):
    command = claims()
    monkeypatch.setenv('GITHUB_REPOSITORY', 'someone/else')
    with pytest.raises(ValueError, match='wrong_repository'):
        command.acquire_remote_claim('b' * 64)
