"""Mandatory remote claim and durable HTTP evidence for the new v4 campaign."""
import hashlib
import json
import os
from pathlib import Path
import re

import httpx

from searchclinic.evaluation.queryscope_v2 import write_json

REPOSITORY = 'sokldjs554/queryscope'


def claim(client, commit, token, attempt, campaign_sha256):
    if attempt != '1':
        raise ValueError('rerun_not_authorized')
    if not re.fullmatch('[0-9a-f]{40}', commit):
        raise ValueError('invalid_commit')
    if not token:
        raise ValueError('github_token_missing')
    if not re.fullmatch('[0-9a-f]{64}', campaign_sha256):
        raise ValueError('invalid_campaign_identity')
    ref = 'refs/tags/queryscope-v4-runtime-paid-' + campaign_sha256
    response = client.post(
        f'https://api.github.com/repos/{REPOSITORY}/git/refs',
        headers={'Authorization': 'Bearer ' + token,
                 'Accept': 'application/vnd.github+json',
                 'X-GitHub-Api-Version': '2022-11-28'},
        json={'ref': ref, 'sha': commit},
    )
    if response.status_code != 201:
        raise RuntimeError(f'remote_claim_failed_{response.status_code}')
    return {'ref': ref, 'commit': commit, 'canonical_campaign_sha256': campaign_sha256}


def acquire_remote_claim(campaign_sha256):
    """Always create, never merely check, the repository-wide once-only ref."""
    if os.environ.get('GITHUB_REPOSITORY') != REPOSITORY:
        raise ValueError('wrong_repository')
    with httpx.Client(timeout=30, follow_redirects=False) as client:
        receipt = claim(client, os.environ.get('GITHUB_SHA', ''), os.environ.get('GH_TOKEN', ''),
                        os.environ.get('GITHUB_RUN_ATTEMPT', ''), campaign_sha256)
    return {**receipt, 'run_id': os.environ.get('GITHUB_RUN_ID'),
            'run_attempt': os.environ.get('GITHUB_RUN_ATTEMPT')}


def redact_secret(value, secret):
    """Remove an exact credential from any unexpected reflected response value."""
    if isinstance(value, str):
        return value.replace(secret, '[REDACTED]')
    if isinstance(value, list):
        return [redact_secret(item, secret) for item in value]
    if isinstance(value, dict):
        return {redact_secret(key, secret): redact_secret(item, secret) for key, item in value.items()}
    return value


class RecordingClient:
    """Buffer and save each received envelope before the legacy adapter parses it.

    Request headers are never recorded. The normal transport verifies TLS and
    follows no redirects. No retry is implemented. One fresh client per request
    preserves the historical provider's connection behavior.
    """
    def __init__(self, output, secret):
        self.output = Path(output)
        self._secret = secret
        self.metadata = None
        self.envelope = None
        self._attempt = None

    def begin(self, index, case_id, condition, payload):
        self.metadata = None
        self.envelope = None
        self._attempt = {'number': index + 1, 'case_id': case_id, 'condition': condition,
                         'request_body_sha256': hashlib.sha256(
                             json.dumps(payload, ensure_ascii=False).encode('utf-8')).hexdigest()}

    def post(self, url, *, content, headers):
        if self._attempt is None:
            raise RuntimeError('response_recorder_not_initialized')
        if hashlib.sha256(content).hexdigest() != self._attempt['request_body_sha256']:
            raise RuntimeError('transmitted_payload_changed')
        with httpx.Client(timeout=45, follow_redirects=False) as client:
            response = client.post(url, content=content, headers=headers)
            self.record_response(response)
            return response

    def record_response(self, response):
        if self._attempt is None:
            raise RuntimeError('response_recorder_not_initialized')
        body = response.content
        saved = body.replace(self._secret.encode('utf-8'), b'[REDACTED]')
        folder = self.output / 'raw-http'
        folder.mkdir(exist_ok=True)
        path = folder / f"response-{self._attempt['number']:03d}.txt"
        path.write_bytes(saved)
        try:
            parsed = json.loads(saved)
        except (ValueError, UnicodeDecodeError):
            parsed = None
        self.envelope = parsed if isinstance(parsed, dict) else None
        envelope = self.envelope or {}
        usage = envelope.get('usage')
        estimate = None
        if (isinstance(usage, dict) and all(type(usage.get(k)) is int and usage[k] >= 0
                                          for k in ['input_tokens', 'output_tokens'])):
            from searchclinic.rag.openai_provider import INPUT_USD, OUTPUT_USD
            estimate = round(usage['input_tokens'] * INPUT_USD + usage['output_tokens'] * OUTPUT_USD, 8)
        self.metadata = {
            **self._attempt, 'http_status': response.status_code,
            'body_path': str(path.relative_to(self.output)),
            'received_body_sha256': hashlib.sha256(body).hexdigest(),
            'saved_body_sha256': hashlib.sha256(saved).hexdigest(),
            'secret_redacted': saved != body,
            'observed_model': envelope.get('model'), 'response_id': envelope.get('id'),
            'upstream_status': envelope.get('status'), 'usage': usage,
            'estimated_usd': estimate,
        }
        write_json(path.with_suffix('.receipt.json'), self.metadata)


def verify_generation_provenance(generated, recorder, requested_model, seen_ids):
    """Observed upstream fields are required; adapter defaults are not evidence."""
    envelope = recorder.envelope
    reason = None
    if not isinstance(envelope, dict):
        reason = 'missing_http_envelope'
    elif recorder.metadata['secret_redacted']:
        reason = 'credential_reflection_redacted'
    elif envelope.get('model') != requested_model:
        reason = 'observed_model_mismatch'
    elif not isinstance(envelope.get('id'), str) or not envelope['id'].strip():
        reason = 'missing_response_id'
    elif envelope['id'] in seen_ids:
        reason = 'duplicate_response_id'
    elif generated.get('response_id') != envelope['id'] or generated.get('model') != envelope['model']:
        reason = 'adapter_provenance_mismatch'
    if reason:
        raise RuntimeError('response_provenance_invalid:' + reason)
    seen_ids.add(envelope['id'])
