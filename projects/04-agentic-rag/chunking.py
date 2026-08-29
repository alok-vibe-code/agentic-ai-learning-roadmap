"""Deterministic word-window chunking for the bundled knowledge base."""

from __future__ import annotations

import json
from pathlib import Path

from models import Chunk, Document


def load_documents(path: str | Path) -> list[Document]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, list) or not raw:
        raise ValueError("Knowledge base must contain at least one document.")

    documents: list[Document] = []
    seen_ids: set[str] = set()

    for item in raw:
        required = {"id", "title", "source_url", "tags", "text"}
        missing = required.difference(item)
        if missing:
            raise ValueError(
                f"Document {item.get('id', '<unknown>')} is missing: {sorted(missing)}"
            )

        document_id = str(item["id"]).strip()
        if not document_id:
            raise ValueError("Document ID cannot be empty.")
        if document_id in seen_ids:
            raise ValueError(f"Duplicate document ID: {document_id}")
        seen_ids.add(document_id)

        text = str(item["text"]).strip()
        if not text:
            raise ValueError(f"Document {document_id} has empty text.")

        documents.append(
            Document(
                id=document_id,
                title=str(item["title"]).strip(),
                source_url=str(item["source_url"]).strip(),
                tags=tuple(str(tag).casefold() for tag in item["tags"]),
                text=text,
            )
        )

    return documents


def chunk_document(
    document: Document,
    chunk_size: int = 70,
    overlap: int = 15,
) -> list[Chunk]:
    if chunk_size < 10:
        raise ValueError("chunk_size must be >= 10 words.")
    if overlap < 0:
        raise ValueError("overlap cannot be negative.")
    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size.")

    words = document.text.split()
    if not words:
        return []

    chunks: list[Chunk] = []
    step = chunk_size - overlap
    start = 0
    position = 0

    while start < len(words):
        end = min(start + chunk_size, len(words))
        text = " ".join(words[start:end]).strip()
        if text:
            chunks.append(
                Chunk(
                    id=f"{document.id}::chunk-{position}",
                    document_id=document.id,
                    title=document.title,
                    source_url=document.source_url,
                    tags=document.tags,
                    text=text,
                    position=position,
                )
            )
        if end >= len(words):
            break
        position += 1
        start += step

    return chunks


def build_chunks(
    documents: list[Document],
    chunk_size: int = 70,
    overlap: int = 15,
) -> list[Chunk]:
    chunks: list[Chunk] = []
    for document in documents:
        chunks.extend(
            chunk_document(
                document,
                chunk_size=chunk_size,
                overlap=overlap,
            )
        )
    if not chunks:
        raise ValueError("Chunking produced no chunks.")
    return chunks
