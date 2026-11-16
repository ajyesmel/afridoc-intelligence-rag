"""Transparent hit@3 evaluation on a small public synthetic corpus."""
from pathlib import Path
from tempfile import TemporaryDirectory
from app.store import DocumentStore
from app.rag import HybridRetriever, answer_question

QUESTIONS = [
    ('Quel est le délai de traitement du dossier en 2025 ?', 'guide-cooperatives-2025.txt'),
    ('Quel est le montant maximal du financement de 2026 ?', 'guide-cooperatives-2026.txt'),
    ('Comment contester un transfert mobile money ?', 'faq-mobile-money.txt'),
    ('Quelle attestation est recommandée pour une coopérative ?', 'guide-cooperatives-2026.txt'),
]


def main():
    with TemporaryDirectory() as tmp:
        store = DocumentStore(f'sqlite:///{Path(tmp) / "eval.db"}')
        for file in (Path(__file__).parent.parent / 'examples').glob('*.txt'):
            store.add(file.name, file.read_text(encoding='utf-8'))
        searcher = HybridRetriever(store)
        correct = 0
        for question, expected in QUESTIONS:
            result = answer_question(question, searcher, k=3)
            hits = [s['document'] for s in result['sources']]
            is_correct = expected in hits
            correct += is_correct
            print(f'{"PASS" if is_correct else "FAIL"}: {question}\n  attendu : {expected}\n  obtenus : {hits}')
        print(f'Hit@3: {correct}/{len(QUESTIONS)} ({correct/len(QUESTIONS):.0%})')
        print('Ce test mesure seulement le rappel de document sur 4 questions fictives, pas la fidélité factuelle des réponses.')


if __name__ == '__main__':
    main()
