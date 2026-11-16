"""Offline contract exercise of graph assembly and LCEL execution.

Real third-party package execution must additionally be validated by CI after
installing pinned-compatible LangGraph and LangChain dependencies.
"""
from __future__ import annotations
import sys
import types


def install_test_graph(monkeypatch):
    START, END = '__start__', '__end__'
    class Graph:
        def __init__(self, schema):
            self.nodes, self.edges, self.conditionals = {}, {}, {}
        def add_node(self, name, function): self.nodes[name] = function
        def add_edge(self, before, after): self.edges[before] = after
        def add_conditional_edges(self, before, router, mapping):
            self.conditionals[before] = router, mapping
        def compile(self): return self
        def invoke(self, data):
            state = dict(data)
            current = START
            for _ in range(25):
                if current == END: return state
                if current != START:
                    state.update(self.nodes[current](dict(state)))
                if current in self.conditionals:
                    router, mapping = self.conditionals[current]
                    current = mapping[router(state)]
                else:
                    current = self.edges[current]
            raise AssertionError('Graph did not terminate')
    langgraph = types.ModuleType('langgraph')
    graph_module = types.ModuleType('langgraph.graph')
    graph_module.StateGraph, graph_module.START, graph_module.END = Graph, START, END
    monkeypatch.setitem(sys.modules, 'langgraph', langgraph)
    monkeypatch.setitem(sys.modules, 'langgraph.graph', graph_module)


def test_real_rag_graph_nodes_execute_with_framework_contract(tmp_path, monkeypatch):
    install_test_graph(monkeypatch)
    from app.store import DocumentStore
    from app.rag import agent_query, HybridRetriever
    store = DocumentStore(f'sqlite:///{tmp_path / "rag.db"}')
    store.add('faq.txt', 'Le financement des coopératives agricoles est de 250000 FCFA.')
    retriever = HybridRetriever(store)
    search = agent_query('Quel financement pour les coopératives ?', retriever)
    assert search['sources'] and search['steps'][0]['selected'] == 'search'
    compare_missing = agent_query('Compare les conditions', retriever)
    assert compare_missing['steps'][0]['status'] == 'needs_sources'
    calc = agent_query('Calcule 10000 + 5000', retriever)
    assert '15000' in calc['answer'] and calc['sources'] == []
