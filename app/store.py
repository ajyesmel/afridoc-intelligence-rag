"""Portable SQLAlchemy-backed document store (SQLite local / PostgreSQL cloud)."""
from __future__ import annotations
import hashlib
import os
import uuid
from pathlib import Path
from sqlalchemy import create_engine, MetaData, Table, Column, String, Text, Integer, ForeignKey, select, delete
from sqlalchemy.engine import Engine

metadata = MetaData()
documents = Table('documents', metadata,
    Column('id', String(36), primary_key=True), Column('name', String(255), unique=True, nullable=False),
    Column('sha256', String(64), nullable=False), Column('created_at', String(40), nullable=False))
chunks = Table('chunks', metadata,
    Column('id', String(36), primary_key=True), Column('document_id', String(36), ForeignKey('documents.id'), nullable=False),
    Column('ordinal', Integer, nullable=False), Column('body', Text, nullable=False))


def _engine(url: str) -> Engine:
    if url.startswith('sqlite:///') and not url.endswith(':memory:'):
        Path(url.removeprefix('sqlite:///')).parent.mkdir(parents=True, exist_ok=True)
    return create_engine(url, pool_pre_ping=True)


class DocumentStore:
    def __init__(self, db_url: str | None = None):
        self.engine = _engine(db_url or os.getenv('DATABASE_URL', 'sqlite:///./data/afridoc.db'))
        metadata.create_all(self.engine)

    def add(self, name: str, content: str) -> dict:
        from datetime import datetime, timezone
        from .rag import split_text
        name = name.strip().split('/')[-1].split('\\')[-1]
        if not name or len(name) > 255 or not content.strip() or len(content) > 1_000_000:
            raise ValueError('Nom invalide, contenu vide ou texte trop long (limite : 1 million de caractères).')
        digest = hashlib.sha256(content.encode('utf-8')).hexdigest()
        parts = split_text(content)
        with self.engine.begin() as cn:
            old = cn.execute(select(documents).where(documents.c.name == name)).mappings().first()
            if old and old['sha256'] == digest:
                count = len(cn.execute(select(chunks.c.id).where(chunks.c.document_id == old['id'])).all())
                return {'id': old['id'], 'name': name, 'chunks': count, 'deduplicated': True}
            if old:
                cn.execute(delete(chunks).where(chunks.c.document_id == old['id']))
                cn.execute(delete(documents).where(documents.c.id == old['id']))
            did = str(uuid.uuid4())
            cn.execute(documents.insert().values(id=did, name=name, sha256=digest,
                created_at=datetime.now(timezone.utc).isoformat()))
            cn.execute(chunks.insert(), [dict(id=str(uuid.uuid4()), document_id=did, ordinal=i, body=p) for i,p in enumerate(parts)])
        return {'id': did, 'name': name, 'chunks': len(parts), 'deduplicated': False}

    def list_documents(self) -> list[dict]:
        with self.engine.connect() as cn:
            return [dict(x) for x in cn.execute(select(documents).order_by(documents.c.name)).mappings()]

    def all_chunks(self, sources: list[str] | None = None, limit: int = 10000) -> list[dict]:
        stmt = select(chunks.c.id, chunks.c.body, chunks.c.ordinal, documents.c.name.label('document')).join(
            documents, chunks.c.document_id == documents.c.id).limit(limit)
        if sources is not None:
            stmt = stmt.where(documents.c.name.in_(sources))
        with self.engine.connect() as cn:
            return [dict(x) for x in cn.execute(stmt).mappings()]

    def delete(self, document_id: str) -> bool:
        with self.engine.begin() as cn:
            exists = cn.execute(select(documents.c.id).where(documents.c.id == document_id)).first()
            if not exists:
                return False
            cn.execute(delete(chunks).where(chunks.c.document_id == document_id))
            cn.execute(delete(documents).where(documents.c.id == document_id))
        return True
