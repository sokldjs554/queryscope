"""The follow-up audit must never rewrite primary evidence or call a model."""
import json
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'docs/verification/queryscope-v3/actual-api-v1/results.json'


def test_audit_refuses_overwrite_and_non_actual_input(tmp_path):
    from searchclinic.evaluation.runtime_audit import run_audit
    existing = tmp_path / 'existing'
    existing.mkdir()
    with pytest.raises(FileExistsError):
        run_audit(SOURCE, existing)
    fake = tmp_path / 'fake.json'
    fake.write_text(json.dumps({'mode': 'dry_run', 'suite': 'queryscope-v3'}), encoding='utf-8')
    with pytest.raises(ValueError, match='actual_v3_results_required'):
        run_audit(fake, tmp_path / 'new')
    assert not (tmp_path / 'new').exists()


def test_audit_preserves_primary_answers_and_has_no_provider(tmp_path, monkeypatch):
    from searchclinic.evaluation.runtime_audit import run_audit
    from searchclinic.rag import openai_provider
    def forbidden(*args, **kwargs):
        raise AssertionError('offline audit attempted model construction')
    monkeypatch.setattr(openai_provider, 'OpenAIExplainer', forbidden)
    before = SOURCE.read_bytes()
    report = run_audit(SOURCE, tmp_path / 'audit', prepare_contexts=False)
    assert SOURCE.read_bytes() == before
    assert report['new_api_calls'] == 0
    assert report['human_review'] == 'pending_independent_human_review'
    assert len(report['rows']) == 24
    source_rows = json.loads(before)['rows']
    for original, row in zip(source_rows, report['rows']):
        assert row['primary_status'] == original['assessment']['validated_status']
        assert row['raw_answer'] == original['model_answer']
    microscope = next(r for r in report['rows'] if r['case_id'] == 'T15' and r['condition'] == 'hint')
    assert microscope['primary_status'] == 'supported'
    assert microscope['runtime_status'] == 'invalid'
    assert microscope['runtime_validation_error'] == 'canonical_not_in_index'
    assert microscope['runtime_effect']['status'] == 'not_run'
    assert report['summary']['accepted_responses'] == 4
    assert report['summary']['regression_decreases'] == []


@pytest.mark.parametrize('mutation', ['context', 'duplicate_pair', 'raw_answer', 'prepared_hash', 'response_id'])
def test_audit_rejects_drifted_actual_evidence_before_reporting(tmp_path, mutation):
    from searchclinic.evaluation.runtime_audit import run_audit
    data = json.loads(SOURCE.read_text(encoding='utf-8'))
    if mutation == 'context':
        data['rows'][0]['context']['problem'] = 'ALTERED AFTER GENERATION'
    elif mutation == 'duplicate_pair':
        data['rows'][1]['case_id'] = data['rows'][0]['case_id']
        data['rows'][1]['condition'] = data['rows'][0]['condition']
    elif mutation == 'raw_answer':
        data['rows'][0]['model_answer']['summary'] = '생성 후 바꾼 응답이며 원래 응답이 아닙니다.'
    elif mutation == 'prepared_hash':
        data['prepared_sha256'] = '0' * 64
    else:
        data['rows'][1]['generation']['response_id'] = data['rows'][0]['generation']['response_id']
    changed = tmp_path / 'changed.json'
    changed.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
    with pytest.raises(ValueError, match='evidence_'):
        run_audit(changed, tmp_path / 'out', prepare_contexts=False)
    assert not (tmp_path / 'out').exists()
