"""Seed a synthetic, reproducible French-African document corpus."""
from pathlib import Path
from app.store import DocumentStore
from app.rag import HybridRetriever, answer_question


def main():
    db = DocumentStore()
    for p in sorted((Path(__file__).parent.parent / 'examples').glob('*.txt')):
        print('Document:', db.add(p.name, p.read_text(encoding='utf-8')))
    result = answer_question('Quelles sont les conditions de financement des coopératives ?', HybridRetriever(db))
    print('\n', result['answer'])


if __name__ == '__main__':
    main()
