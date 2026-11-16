"""REST API, explicit security boundary and validation."""
from __future__ import annotations
import hmac
import io
import os
from pathlib import Path
from fastapi import Depends, FastAPI, Header, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from pypdf import PdfReader
from .store import DocumentStore
from .rag import HybridRetriever, answer_question, agent_query


class DocumentIn(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    text: str = Field(min_length=1, max_length=1_000_000)


class QuestionIn(BaseModel):
    question: str = Field(min_length=3, max_length=2000)
    sources: list[str] | None = None
    source_a: str | None = None
    source_b: str | None = None
    k: int = Field(default=4, ge=1, le=10)


def auth(x_api_key: str | None = Header(default=None)) -> None:
    expected = os.getenv('APP_API_KEY', '')
    if not expected:
        raise HTTPException(status_code=503, detail='APP_API_KEY must be configured.')
    if not x_api_key or not hmac.compare_digest(x_api_key, expected):
        raise HTTPException(status_code=401, detail='Invalid API key.')


def create_app() -> FastAPI:
    application = FastAPI(title='AfriDoc Intelligence RAG', version='2.0.0', description='Classic and agentic document RAG. /docs for interactive OpenAPI.')
    store = DocumentStore()
    retriever = HybridRetriever(store)

    @application.get('/healthz')
    def healthz():
        return {'status': 'ok', 'service': 'afridoc'}

    @application.get('/', response_class=HTMLResponse)
    def homepage():
        return (Path(__file__).parent / 'ui.html').read_text(encoding='utf-8')

    @application.post('/v1/documents', status_code=201, dependencies=[Depends(auth)])
    def create_document(payload: DocumentIn):
        try:
            return store.add(payload.name, payload.text)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc

    @application.post('/v1/documents/upload', status_code=201, dependencies=[Depends(auth)])
    async def upload(file: UploadFile = File(...)):
        ext = Path(file.filename or '').suffix.lower()
        if ext not in {'.pdf', '.txt', '.md'}:
            raise HTTPException(415, 'Formats admis : PDF, TXT, MD.')
        raw = await file.read(5_000_001)
        if len(raw) > 5_000_000:
            raise HTTPException(413, 'Taille maximale : 5 Mo.')
        try:
            text = (' '.join(p.extract_text() or '' for p in PdfReader(io.BytesIO(raw)).pages)
                if ext == '.pdf' else raw.decode('utf-8-sig'))
            if not text.strip():
                raise ValueError('Aucun texte exploitable (PDF scanné ?).')
            return store.add(file.filename or 'document', text)
        except (ValueError, UnicodeError, Exception) as exc:
            # Do not leak internal parser exceptions or file paths.
            raise HTTPException(422, 'Fichier illisible ou sans couche texte exploitable.') from exc

    @application.get('/v1/documents', dependencies=[Depends(auth)])
    def get_documents():
        return store.list_documents()

    @application.delete('/v1/documents/{document_id}', dependencies=[Depends(auth)])
    def delete_document(document_id: str):
        if not store.delete(document_id):
            raise HTTPException(404, 'Document introuvable.')
        return {'deleted': True}

    @application.post('/v1/query', dependencies=[Depends(auth)])
    def query(payload: QuestionIn):
        return answer_question(payload.question, retriever, sources=payload.sources, k=payload.k)

    @application.post('/v1/agent/query', dependencies=[Depends(auth)])
    def query_agent(payload: QuestionIn):
        return agent_query(payload.question, retriever, source_a=payload.source_a, source_b=payload.source_b)

    return application


app = create_app()
