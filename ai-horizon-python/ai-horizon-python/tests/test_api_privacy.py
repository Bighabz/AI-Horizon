import asyncio
import json

from src.api import main as api


def test_evidence_error_does_not_return_provider_details(monkeypatch):
    monkeypatch.setattr(api, 'client', object())
    monkeypatch.setattr(api, 'EVIDENCE_STORE_NAME', 'fileSearchStores/test')

    def fail(*args, **kwargs):
        raise RuntimeError('private-provider-connection-detail')

    monkeypatch.setattr(api, 'call_with_retry', fail)
    response = asyncio.run(api.get_evidence('TEST-TASK'))
    assert response['evidence'] == []
    assert 'error' in response
    assert 'private-provider-connection-detail' not in json.dumps(response)
