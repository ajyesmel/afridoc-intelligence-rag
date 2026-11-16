"""Framework integration contract tests. All tests remain offline and deterministic."""
from pathlib import Path
from app.rag import HybridRetriever, agent_query, answer_question
from app.store import DocumentStore


def test_rag_entry_points_keep_evidence_and_langgraph_trace(tmp_path: Path):
    store = DocumentStore(f'sqlite:///{tmp_path / "rag.db"}')
    store.add('note.txt', 'Les coopératives agricoles de Bouaké peuvent solliciter un financement de 250000 FCFA.')
    retriever = HybridRetriever(store)
    result = answer_question('Quel financement pour les coopératives ?', retriever)
    assert result['sources'] and result['sources'][0]['ref'] == 'S1'
    trace = agent_query('Quel financement pour les coopératives ?', retriever)
    assert trace['sources'] and any(step.get('tool') == 'citation_validation' for step in trace['steps'])


def test_rag_agent_workflow_uses_langgraph_when_available(tmp_path: Path, monkeypatch):
    from app import rag
    store = DocumentStore(f'sqlite:///{tmp_path / "rag.db"}')
    store.add('faq.txt', 'La période de dépôt pour les coopératives est le mois de janvier.')
    calls = []
    def invoked(question, retriever, source_a=None, source_b=None):
        calls.append(question)
        return {'mode': 'agentic', 'answer': 'depuis graphe', 'sources': [], 'steps': []}
    monkeypatch.setattr('app.agent_graph.run_agent_graph', invoked)
    answer = rag.agent_query('Quand déposer le dossier ?', HybridRetriever(store))
    assert calls == ['Quand déposer le dossier ?'] and answer['answer'] == 'depuis graphe'
