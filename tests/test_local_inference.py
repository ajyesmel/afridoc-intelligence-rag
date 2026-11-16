"""Confidential on-prem LLM selection, with deterministic HTTP test doubles."""
from app import llm


def test_local_llm_uses_enterprise_address_not_groq(monkeypatch):
    monkeypatch.setenv('LLM_PROVIDER', 'local')
    monkeypatch.setenv('LOCAL_LLM_BASE_URL', 'http://ollama:11434/v1')
    monkeypatch.setenv('LOCAL_LLM_MODEL', 'qwen2.5:3b')
    monkeypatch.setenv('GROQ_API_KEY', 'should-not-be-used')
    seen = {}
    class Client:
        def __init__(self, **kw): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def post(self, url, **kw):
            seen['url'] = url
            seen['request'] = kw
            class Response:
                def raise_for_status(self): pass
                def json(self): return {'choices': [{'message': {'content': 'Document retrouvé [S1]'}}]}
            return Response()
    monkeypatch.setattr(llm.httpx, 'Client', Client)
    assert llm.generate('system', 'question') == 'Document retrouvé [S1]'
    assert seen['url'] == 'http://ollama:11434/v1/chat/completions'
    assert 'Authorization' not in seen['request']['headers']
    assert seen['request']['json']['model'] == 'qwen2.5:3b'


def test_off_mode_never_calls_external_llm(monkeypatch):
    monkeypatch.setenv('LLM_PROVIDER', 'off')
    monkeypatch.setenv('GROQ_API_KEY', 'even-if-set')
    monkeypatch.setattr(llm.httpx, 'Client', lambda **kwargs: (_ for _ in ()).throw(AssertionError('network')))
    assert llm.generate('system', 'question') is None
