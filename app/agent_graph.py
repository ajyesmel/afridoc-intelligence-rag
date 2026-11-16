"""LangGraph orchestration for traceable, bounded document tools.

No arbitrary Python execution, network browsing or mutation tools are offered to
this graph. It only handles retrieval, comparison and a restricted calculator.
"""
from __future__ import annotations
import os
import re
from typing import Any, TypedDict


class RAGState(TypedDict, total=False):
    question: str
    source_a: str | None
    source_b: str | None
    route: str
    answer: str
    sources: list[dict]
    steps: list[dict]


def create_graph(retriever):
    """Build a LangGraph state machine. A new instance scopes tools to one store."""
    from langgraph.graph import StateGraph, START, END
    from .rag import select_tool, safe_calculate, _evidence, _synthesis

    def planner(s: RAGState) -> dict:
        route = select_tool(s['question'], s.get('source_a'), s.get('source_b'))
        return {'route': route, 'steps': [{'tool': 'planner', 'selected': route,
            'llm_routing_enabled': os.getenv('ENABLE_LLM_TOOL_ROUTER', '').lower() == 'true'}]}

    def search(s: RAGState) -> dict:
        hits = retriever.search(s['question'])
        return {'sources': _evidence(hits), 'steps': s['steps'] + [{'tool': 'search', 'hits': len(hits)}]}

    def compare(s: RAGState) -> dict:
        source_a, source_b = s.get('source_a'), s.get('source_b')
        if not source_a or not source_b:
            return {'answer': 'Précisez source_a et source_b pour comparer deux documents.',
                    'sources': [], 'steps': [{'tool': 'compare', 'status': 'needs_sources'}]}
        a = retriever.search(s['question'], k=3, sources=[source_a])
        b = retriever.search(s['question'], k=3, sources=[source_b])
        return {'sources': _evidence(a + b), 'steps': s['steps'] + [
            {'tool': 'search', 'document': source_a, 'hits': len(a)},
            {'tool': 'search', 'document': source_b, 'hits': len(b)},
            {'tool': 'compare', 'status': 'completed' if a and b else 'partial_evidence'}]}

    def calculator(s: RAGState) -> dict:
        expressions = re.findall(r'\d+(?:\.\d+)?(?:\s*[+*/-]\s*\d+(?:\.\d+)?)+', s['question'])
        if expressions:
            try:
                value = safe_calculate(expressions[0])
                return {'answer': f'Résultat du calcul {expressions[0]} = {value:g}.',
                        'sources': [], 'steps': [{'tool': 'calculator', 'status': 'completed'}]}
            except (ValueError, SyntaxError, ZeroDivisionError, OverflowError):
                pass
        hits = retriever.search(s['question'])
        return {'sources': _evidence(hits), 'steps': s['steps'] + [
            {'tool': 'calculator', 'status': 'unsupported_expression'}]}

    def synthesis(s: RAGState) -> dict:
        if s.get('answer'):
            return {}
        query = s['question']
        if s['route'] == 'compare':
            query = f"Compare les documents {s.get('source_a')} et {s.get('source_b')}. {query}"
        return {'answer': _synthesis(query, s.get('sources', []))}

    def validate(s: RAGState) -> dict:
        if s['route'] == 'calculate' and s.get('answer'):
            return {}
        if s['route'] == 'compare' and not (s.get('source_a') and s.get('source_b')):
            return {}
        return {'steps': s.get('steps', []) + [{'tool': 'citation_validation',
            'allowed': [x['ref'] for x in s.get('sources', [])]}]}

    graph = StateGraph(RAGState)
    graph.add_node('planner', planner)
    graph.add_node('search', search)
    graph.add_node('compare', compare)
    graph.add_node('calculator', calculator)
    graph.add_node('synthesis', synthesis)
    graph.add_node('citation_validation', validate)
    graph.add_edge(START, 'planner')
    graph.add_conditional_edges('planner', lambda s: s['route'],
                                {'search': 'search', 'compare': 'compare', 'calculate': 'calculator'})
    for tool in ('search', 'compare', 'calculator'):
        graph.add_edge(tool, 'synthesis')
    graph.add_edge('synthesis', 'citation_validation')
    graph.add_edge('citation_validation', END)
    return graph.compile()


def run_agent_graph(question: str, retriever, source_a: str | None = None,
                    source_b: str | None = None) -> dict[str, Any]:
    """Dispatch to LangGraph when available; keep offline light-mode operational."""
    try:
        graph = create_graph(retriever)
    except ModuleNotFoundError as exc:
        if exc.name not in {'langgraph', 'langchain_core', 'langchain'}:
            raise
        from .rag import _legacy_agent_query
        return _legacy_agent_query(question, retriever, source_a, source_b)
    final = graph.invoke({'question': question, 'source_a': source_a,
                          'source_b': source_b, 'steps': [], 'sources': []})
    return {'mode': 'agentic', 'answer': final['answer'],
            'sources': final.get('sources', []), 'steps': final.get('steps', [])}
