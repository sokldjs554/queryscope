"""Paid-run orchestration is tested with local, explicit test-only providers."""
import copy
import importlib
import json
from pathlib import Path

import pytest
import httpx

from searchclinic.evaluation.llm_campaign import campaign_bundle, campaign_engine
from searchclinic.evaluation.queryscope_v2 import file_sha, json_sha
from searchclinic.rag import openai_provider


def campaign():
    try:
        return importlib.import_module('searchclinic.evaluation.runtime_campaign')
    except ModuleNotFoundError:
        pytest.fail('runtime campaign preparation, validation and execution are not implemented')


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def prepared(tmp_path):
    module = campaign()
    folder = tmp_path / 'prepared'
    module.prepare_runtime_campaign(folder)
    return module, folder


def test_only_approval(module, folder, target):
    # This is a temporary fake authorization for mocked provider tests only.
    data = json.loads((folder / 'approval-template.json').read_text(encoding='utf-8'))
    data.update(approved=True, approved_by='unit test fixture only')
    write_json(target, data)
    return target


test_only_approval.__test__ = False


def abstention():
    return {'status': 'abstain', 'family': 'unknown', 'summary': '확인된 근거가 충분하지 않아 보류합니다.',
            'evidence': [], 'patches': []}


def fake_provider(monkeypatch, *, fail_calls=(), interrupt=False):
    from searchclinic.evaluation import runtime_campaign_io
    monkeypatch.setattr(runtime_campaign_io, 'acquire_remote_claim',
                        lambda identity: {'canonical_campaign_sha256': identity, 'test_fixture': True})
    seen = []
    class Fake:
        def __init__(self, key, *, budget, client):
            assert key == 'unit-test-not-a-real-key'
            self.budget = budget
            self.client = client

        def generate(self, context):
            self.budget.reserve()
            seen.append((copy.deepcopy(context), self.budget.path.name))
            if interrupt:
                raise RuntimeError('simulated interruption after reservation')
            if len(seen) in fail_calls:
                raise openai_provider.ProviderError('upstream_timeout')
            self.client.record_response(httpx.Response(200, json={
                'id': f'fixture_{len(seen)}', 'model': openai_provider.MODEL,
                'status': 'completed', 'usage': {'input_tokens': 0, 'output_tokens': 0},
                'output': [{'type': 'message', 'content': [{'type': 'output_text', 'text': json.dumps(abstention())}]}],
            }))
            return {'raw': abstention(), 'response_id': f'fixture_{len(seen)}',
                    'model': openai_provider.MODEL, 'usage': {'input_tokens': 0, 'output_tokens': 0},
                    'estimated_usd': 0, 'latency_ms': 0}
    monkeypatch.setenv('OPENAI_API_KEY', 'unit-test-not-a-real-key')
    monkeypatch.setattr(openai_provider, 'OpenAIExplainer', Fake)
    return seen


def test_preparation_freezes_all48_without_constructing_provider(tmp_path, monkeypatch):
    module = campaign()
    monkeypatch.setattr(openai_provider, 'OpenAIExplainer', lambda *a, **k: pytest.fail('provider constructed'))
    monkeypatch.setenv('OPENAI_API_KEY', 'unit-test-not-a-real-key')
    result = module.prepare_runtime_campaign(tmp_path / 'prepared')
    assert result['suite'] == 'queryscope-v4-runtime'
    assert result['calls_if_approved'] == 48
    assert result['reservation_usd'] == .60
    assert len(result['requests']) == 48
    assert len({(r['case_id'], r['condition']) for r in result['requests']}) == 48
    assert all(r['model_answer'] is None and r['generation_status'] == 'not_run' for r in result['requests'])
    for row in result['requests']:
        assert row['payload'] == openai_provider.request_payload(row['context'])
        assert row['payload_bytes'] <= 11000
    template = json.loads((tmp_path / 'prepared/approval-template.json').read_text(encoding='utf-8'))
    assert template['approved'] is False
    assert template['calls'] == 48 and template['max_usd'] == .60
    assert template['prepared_sha256'] == file_sha(tmp_path / 'prepared/requests.json')
    assert module.validate_runtime_preparation(tmp_path / 'prepared')['prepared_sha256'] == template['prepared_sha256']
    with pytest.raises(FileExistsError):
        module.prepare_runtime_campaign(tmp_path / 'prepared')


def test_modified_source_is_rejected_without_creating_output(tmp_path):
    module = campaign()
    source = tmp_path / 'source.json'
    source.write_bytes(Path(module.DEFAULT_AUDIT).read_bytes() + b' ')
    with pytest.raises(ValueError, match='source'):
        module.prepare_runtime_campaign(tmp_path / 'prepared', source=source)
    assert not (tmp_path / 'prepared').exists()


def test_changed_provider_reservation_cannot_exceed_approved_campaign_cap(tmp_path, monkeypatch):
    module, folder = prepared(tmp_path)
    monkeypatch.setattr(openai_provider, 'RESERVATION_USD', .02)
    with pytest.raises(ValueError, match='budget'):
        module.validate_runtime_preparation(folder)


@pytest.mark.parametrize('mutation', ['context', 'payload', 'duplicate', 'missing', 'model',
                                     'source', 'canonical', 'budget', 'full_context'])
def test_preparation_tampering_fails_before_key_or_provider(tmp_path, monkeypatch, mutation):
    module, folder = prepared(tmp_path)
    data = json.loads((folder / 'requests.json').read_text(encoding='utf-8'))
    if mutation == 'context':
        data['requests'][0]['context']['problem'] = 'changed'
        data['requests'][0]['context_sha256'] = json_sha(data['requests'][0]['context'])
    elif mutation == 'payload':
        data['requests'][0]['payload']['max_output_tokens'] = 801
    elif mutation == 'duplicate':
        data['requests'][1] = copy.deepcopy(data['requests'][0])
    elif mutation == 'missing':
        data['requests'].pop()
    elif mutation == 'model':
        data['model'] = 'different-model'
    elif mutation == 'source':
        data['source_sha256'] = '0' * 64
    elif mutation == 'canonical':
        data['canonical_campaign_sha256'] = '0' * 64
    elif mutation == 'budget':
        data['reservation_usd'] = .61
    else:
        data['requests'][0]['full_context']['problem'] = 'changed'
    write_json(folder / 'requests.json', data)
    monkeypatch.setattr(openai_provider, 'OpenAIExplainer', lambda *a, **k: pytest.fail('provider constructed'))
    with pytest.raises(ValueError):
        module.validate_runtime_preparation(folder)


@pytest.mark.parametrize('field,value', [('approved', False), ('approved_by', '   '),
                                        ('calls', 24), ('max_usd', .30), ('model', 'other'),
                                        ('suite', 'queryscope-v3'), ('prepared_sha256', '0' * 64),
                                        ('canonical_campaign_sha256', '0' * 64)])
def test_wrong_approval_is_rejected_before_claim(tmp_path, monkeypatch, field, value):
    module, folder = prepared(tmp_path)
    approval = test_only_approval(module, folder, tmp_path / 'test-approval.json')
    data = json.loads(approval.read_text(encoding='utf-8')); data[field] = value; write_json(approval, data)
    state = tmp_path / 'state'; monkeypatch.setattr(module, 'CAMPAIGN_STATE_ROOT', state)
    with pytest.raises(ValueError):
        module.execute_runtime_campaign(folder, tmp_path / 'out', approval)
    assert not state.exists() and not (tmp_path / 'out').exists()


def test_missing_key_does_not_claim_campaign(tmp_path, monkeypatch):
    module, folder = prepared(tmp_path)
    approval = test_only_approval(module, folder, tmp_path / 'test-approval.json')
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    state = tmp_path / 'state'; monkeypatch.setattr(module, 'CAMPAIGN_STATE_ROOT', state)
    with pytest.raises(ValueError, match='provider_not_configured'):
        module.execute_runtime_campaign(folder, tmp_path / 'out', approval)
    assert not state.exists()


def test_execute48_uses_two_fixed_ledgers_and_separate_comparison_summaries(tmp_path, monkeypatch):
    module, folder = prepared(tmp_path)
    monkeypatch.setattr(module, 'CAMPAIGN_STATE_ROOT', tmp_path / 'state')
    approval = test_only_approval(module, folder, tmp_path / 'test-approval.json')
    seen = fake_provider(monkeypatch, fail_calls=(1, 25))
    result = module.execute_runtime_campaign(folder, tmp_path / 'out', approval)
    assert result['complete'] is True
    assert result['attempts'] == 48 and result['responses'] == 46 and result['errors'] == 2
    assert result['reserved_usd'] == .60
    assert len(seen) == 48
    assert {name for _, name in seen[:24]} == {'budget-0.json'}
    assert {name for _, name in seen[24:]} == {'budget-1.json'}
    assert result['summary']['all']['planned_or_attempted'] == 48
    assert result['paired_summary']['all']['planned_or_attempted'] == 24
    assert result['additional_summary']['all']['planned_or_attempted'] == 24
    state = Path(result['campaign_state_path'])
    for name in ['budget-0.json', 'budget-1.json']:
        assert json.loads((state / name).read_text(encoding='utf-8'))['calls'] == 24
        with pytest.raises(openai_provider.ProviderError, match='budget_exhausted'):
            openai_provider.Budget(state / name, max_calls=24).reserve()
    assert result['rows'][0]['generation_status'] == 'api_error'
    assert 'assessment' not in result['rows'][0]
    with pytest.raises(ValueError, match='campaign_already_claimed'):
        module.execute_runtime_campaign(folder, tmp_path / 'second-out', approval)
    assert len(seen) == 48


def test_changed_timestamp_cannot_create_second_campaign(tmp_path, monkeypatch):
    module, folder = prepared(tmp_path)
    monkeypatch.setattr(module, 'CAMPAIGN_STATE_ROOT', tmp_path / 'state')
    approval = test_only_approval(module, folder, tmp_path / 'test-approval.json')
    seen = fake_provider(monkeypatch, interrupt=True)
    with pytest.raises(RuntimeError, match='simulated interruption'):
        module.execute_runtime_campaign(folder, tmp_path / 'out', approval)
    original = module.validate_runtime_preparation(folder)
    data = json.loads((folder / 'requests.json').read_text(encoding='utf-8')); data['created_at'] = 'different creation time'
    copied = tmp_path / 'copied'; copied.mkdir(); write_json(copied / 'requests.json', data)
    template = json.loads((folder / 'approval-template.json').read_text(encoding='utf-8'))
    template['prepared_sha256'] = file_sha(copied / 'requests.json')
    write_json(copied / 'approval-template.json', template)
    other_approval = test_only_approval(module, copied, tmp_path / 'other-test-approval.json')
    changed = module.validate_runtime_preparation(copied)
    assert changed['prepared_sha256'] != original['prepared_sha256']
    assert changed['canonical_campaign_sha256'] == original['canonical_campaign_sha256']
    with pytest.raises(ValueError, match='campaign_already_claimed'):
        module.execute_runtime_campaign(copied, tmp_path / 'second-out', other_approval)
    assert len(seen) == 1


def test_scoring_failure_keeps_raw_receipt_and_prevents_resume(tmp_path, monkeypatch):
    module, folder = prepared(tmp_path)
    monkeypatch.setattr(module, 'CAMPAIGN_STATE_ROOT', tmp_path / 'state')
    approval = test_only_approval(module, folder, tmp_path / 'test-approval.json')
    seen = fake_provider(monkeypatch)
    def broken(*args):
        persisted = json.loads((tmp_path / 'out/results.json').read_text(encoding='utf-8'))
        assert persisted['rows'][0]['model_answer'] == abstention()
        assert persisted['rows'][0]['generation']['response_id'] == 'fixture_1'
        raise RuntimeError('scoring failed')
    monkeypatch.setattr(module, 'assess_runtime_generation', broken)
    with pytest.raises(RuntimeError, match='scoring failed'):
        module.execute_runtime_campaign(folder, tmp_path / 'out', approval)
    persisted = json.loads((tmp_path / 'out/results.json').read_text(encoding='utf-8'))
    assert persisted['complete'] is False and persisted['responses'] == 1
    assert persisted['attempts'] == 1 and persisted['reserved_usd'] == .0125
    assert persisted['rows'][0]['model_answer'] == abstention()
    assert persisted['rows'][0]['assessment_status'] == 'error'
    with pytest.raises(ValueError, match='campaign_already_claimed'):
        module.execute_runtime_campaign(folder, tmp_path / 'second-out', approval)
    assert len(seen) == 1


def test_execution_uses_validated_in_memory_input_not_second_file_read(tmp_path, monkeypatch):
    from searchclinic.evaluation import runtime_campaign_io
    monkeypatch.setattr(runtime_campaign_io, 'acquire_remote_claim', lambda _: {'test_fixture': True})
    module, folder = prepared(tmp_path)
    monkeypatch.setattr(module, 'CAMPAIGN_STATE_ROOT', tmp_path / 'state')
    approval = test_only_approval(module, folder, tmp_path / 'test-approval.json')
    expected = module.validate_runtime_preparation(folder)['requests'][0]['context']
    received = []
    class MutatingProvider:
        def __init__(self, key, *, budget, client):
            self.budget = budget
            (folder / 'requests.json').write_text('INVALID REPLACEMENT AFTER VALIDATION', encoding='utf-8')
            approval.write_text('INVALID APPROVAL AFTER VALIDATION', encoding='utf-8')
        def generate(self, context):
            self.budget.reserve(); received.append(copy.deepcopy(context))
            raise RuntimeError('stop after observing transmitted context')
    monkeypatch.setenv('OPENAI_API_KEY', 'unit-test-not-a-real-key')
    monkeypatch.setattr(openai_provider, 'OpenAIExplainer', MutatingProvider)
    with pytest.raises(RuntimeError, match='stop after observing'):
        module.execute_runtime_campaign(folder, tmp_path / 'out', approval)
    assert received == [expected]


def test_absent_canonical_is_blocked_before_gate(monkeypatch):
    module = campaign()
    bundle = campaign_bundle('queryscope-v3'); engine = campaign_engine(bundle)
    case = next(c for c in bundle['cases'] if c['id'] == 'T15')
    doc = {'id': 'KTEST', 'title': '표기', 'body': '표기 변형은 좁은 동의어로 연결한다.', 'source': 'test'}
    raw = {'status': 'supported', 'family': 'cross_script', 'summary': '표기 변형을 동의어 후보로 제안합니다.',
           'evidence': [{'doc_id': 'KTEST', 'quote': doc['body']}],
           'patches': [{'kind': 'synonym', 'terms': ['마이크로스코프', 'microscope']}]}
    monkeypatch.setattr(module, 'run_gate', lambda *a, **k: pytest.fail('ineligible patch reached gate'))
    assessment = module.assess_runtime_generation(raw, {'documents': [doc]}, case, engine, [])
    assert assessment['validated_status'] == 'invalid'
    assert assessment['validation_error'] == 'canonical_not_in_index'
    assert assessment['patch_effect']['status'] == 'not_run'


def test_eligible_candidate_records_both_development_and_original_regressions():
    from searchclinic.corpus.evalset import EvalQuery
    module = campaign()
    bundle = campaign_bundle('queryscope-v3'); engine = campaign_engine(bundle)
    case = next(c for c in bundle['cases'] if c['id'] == 'T13')
    doc = {'id': 'KTEST', 'title': '표기', 'body': '표기 변형은 좁은 동의어로 연결한다.', 'source': 'test'}
    raw = {'status': 'supported', 'family': 'spelling_variant', 'summary': '표기 변형을 동의어 후보로 제안합니다.',
           'evidence': [{'doc_id': 'KTEST', 'quote': doc['body']}],
           'patches': [{'kind': 'synonym', 'terms': ['팔레트', '팔래트']}]}
    evalset = [EvalQuery(c['query'], c['qrels']) for c in bundle['cases'] if c['qrels']]
    assessment = module.assess_runtime_generation(raw, {'documents': [doc]}, case, engine, evalset)
    assert assessment['patch_effect']['gate']['accepted'] is True
    assert len(assessment['patch_effect']['development_16']['rows']) == 16
    assert len(assessment['patch_effect']['original_36']['rows']) == 36
    assert assessment['semantic_support'] == 'requires_independent_human_review'
