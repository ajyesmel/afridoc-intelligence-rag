from pathlib import Path
from app.store import DocumentStore
from app.rag import split_text, HybridRetriever, answer_question, agent_query


def test_overlap_and_no_empty_chunks():
    chunks = split_text('A' * 1000, chunk_size=300, overlap=50)
    assert len(chunks) >= 4
    assert chunks[0][-50:] == chunks[1][:50]
    assert all(c for c in chunks)


def test_source_grounding_and_no_answer_when_no_evidence(tmp_path: Path):
    store = DocumentStore(f'sqlite:///{tmp_path / "rag.db"}')
    store.add('tarifs.txt', 'Les frais de transfert mobile money sont de 250 FCFA pour 10 000 FCFA.')
    retriever = HybridRetriever(store)
    result = answer_question('Quels sont les frais de transfert ?', retriever)
    assert result['sources'] and 'tarifs.txt' in result['sources'][0]['document']
    assert '[S1]' in result['answer']
    unknown = answer_question('Quelle est la capitale du Kirghizistan ?', retriever)
    assert unknown['sources'] == []
    assert 'information' in unknown['answer'].lower()


def test_upsert_deduplicates_and_delete_cascades(tmp_path):
    store = DocumentStore(f'sqlite:///{tmp_path / "rag.db"}')
    a = store.add('contrat.txt', 'Le taux annuel est de 5 pour cent.')
    b = store.add('contrat.txt', 'Le taux annuel est de 5 pour cent.')
    assert a['id'] == b['id']
    assert len(store.list_documents()) == 1
    assert store.delete(a['id'])
    assert not store.all_chunks()


def test_agent_exposes_tool_trace(tmp_path):
    store = DocumentStore(f'sqlite:///{tmp_path / "rag.db"}')
    store.add('guide.txt', 'Une PME peut demander un microcredit de 200000 FCFA.')
    response = agent_query('Quel microcrédit pour une PME ?', HybridRetriever(store))
    assert response['steps']
    assert response['mode'] == 'agentic'


def test_api_auth_and_ingestion(tmp_path, monkeypatch):
    monkeypatch.setenv('APP_API_KEY', 'test-secret')
    monkeypatch.setenv('DATABASE_URL', f'sqlite:///{tmp_path / "api.db"}')
    from fastapi.testclient import TestClient
    from app.api import create_app
    with TestClient(create_app()) as client:
        assert client.get('/healthz').status_code == 200
        assert client.get('/v1/documents').status_code == 401
        headers = {'X-API-Key': 'test-secret'}
        r = client.post('/v1/documents', headers=headers, json={'name': 'agriculture.txt', 'text': 'Le cacao est une filière importante en Côte d’Ivoire.'})
        assert r.status_code == 201
        q = client.post('/v1/query', headers=headers, json={'question': 'Quelle filière est importante ?'})
        assert q.status_code == 200 and q.json()['sources']


def test_calculator_never_executes_python():
    from app.rag import safe_calculate
    import pytest
    assert safe_calculate('120000 + 30000') == 150000
    with pytest.raises(ValueError):
        safe_calculate('__import__("os").system("echo bad")')
    with pytest.raises(ValueError):
        safe_calculate('2**100')


def test_compare_requires_explicit_document_names(tmp_path):
    store = DocumentStore(f'sqlite:///{tmp_path / "rag.db"}')
    store.add('a.txt', 'La cotisation annuelle est de 1000 FCFA pour les membres.')
    store.add('b.txt', 'La cotisation annuelle est de 2000 FCFA pour les membres.')
    retriever = HybridRetriever(store)
    missing = agent_query('Compare les cotisations', retriever)
    assert missing['steps'][0]['status'] == 'needs_sources'
    found = agent_query('Compare les cotisations annuelles', retriever, 'a.txt', 'b.txt')
    assert {s['document'] for s in found['sources']} == {'a.txt', 'b.txt'}


def test_upload_blocks_unknown_extension(tmp_path, monkeypatch):
    monkeypatch.setenv('APP_API_KEY', 'test-secret')
    monkeypatch.setenv('DATABASE_URL', f'sqlite:///{tmp_path / "file.db"}')
    from fastapi.testclient import TestClient
    from app.api import create_app
    with TestClient(create_app()) as c:
        assert c.post('/v1/documents/upload', files={'file': ('bad.exe', b'abc')}, headers={'X-API-Key':'test-secret'}).status_code == 415
        assert c.get('/').status_code == 200


def test_chunker_does_not_duplicate_final_suffix():
    from app.rag import split_text
    chunks = split_text('x' * 850, chunk_size=850, overlap=140)
    assert chunks == ['x' * 850]


def test_duplicate_document_reports_correct_chunk_count(tmp_path):
    store = DocumentStore(f'sqlite:///{tmp_path / "rag.db"}')
    store.add('long.txt', 'Les producteurs de riz et de cacao. ' * 120)
    duplicate = store.add('long.txt', 'Les producteurs de riz et de cacao. ' * 120)
    assert duplicate['deduplicated'] is True
    assert duplicate['chunks'] == len(store.all_chunks())


def test_llm_router_is_allowlisted(monkeypatch):
    from app import rag
    monkeypatch.setenv('ENABLE_LLM_TOOL_ROUTER', 'true')
    monkeypatch.setattr(rag, 'generate', lambda system, user: '{"tool":"delete_all_documents"}')
    assert rag.select_tool('Quels sont les critères ?', None, None) == 'search'
    monkeypatch.setattr(rag, 'generate', lambda system, user: '{"tool":"calculate"}')
    assert rag.select_tool('Calcule 10 + 30', None, None) == 'calculate'
    monkeypatch.setattr(rag, 'generate', lambda system, user: '{"tool":"compare"}')
    assert rag.select_tool('Quelles sont les différences ?', None, None) == 'compare'
