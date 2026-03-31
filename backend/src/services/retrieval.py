"""Retrieval service — vector search for career entries using pgvector
and embedding generation for entries and job descriptions."""

from __future__ import annotations

import logging
import uuid

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.career import CareerHistoryEntry
from src.models.job import JobDescription
from src.schemas.matching import RankedEntry
from src.services.llm_config import LLMConfig

logger = logging.getLogger(__name__)


class RetrievalService:
    """Handles embedding generation and vector-based retrieval."""

    def __init__(self, db: AsyncSession, llm_config: LLMConfig) -> None:
        self._db = db
        self._embedding_model = llm_config.get_embedding_model()

    async def generate_embedding(self, text: str) -> list[float]:
        """Generate an embedding vector for the given text."""
        vectors = await self._embedding_model.aembed_documents([text])
        return vectors[0]

    async def embed_career_entry(self, entry: CareerHistoryEntry) -> None:
        """Generate and store an embedding for a career entry."""
        parts = [entry.title]
        if entry.organization:
            parts.append(entry.organization)
        if entry.bullet_points:
            parts.extend(entry.bullet_points)
        if entry.tags:
            parts.append(", ".join(entry.tags))
        text = "\n".join(parts)

        embedding = await self.generate_embedding(text)
        entry.embedding = embedding  # type: ignore[assignment]
        await self._db.commit()

    async def embed_job_description(self, jd: JobDescription) -> None:
        """Generate and store an embedding for a job description."""
        embedding = await self.generate_embedding(jd.raw_text)
        jd.embedding = embedding  # type: ignore[assignment]
        await self._db.commit()

    async def embed_all_entries(self, user_id: uuid.UUID) -> int:
        """Generate embeddings for all entries that don't have one yet."""
        result = await self._db.execute(
            select(CareerHistoryEntry).where(
                CareerHistoryEntry.user_id == user_id,
                CareerHistoryEntry.embedding.is_(None),
            )
        )
        entries = list(result.scalars().all())
        for entry in entries:
            await self.embed_career_entry(entry)
        logger.info("Embedded %d career entries for user %s", len(entries), user_id)
        return len(entries)

    async def find_relevant_entries(
        self,
        user_id: uuid.UUID,
        jd_embedding: list[float],
        *,
        entry_types: list[str] | None = None,
        top_k: int = 10,
    ) -> list[RankedEntry]:
        """Find career entries most relevant to a JD using cosine similarity.

        Only entries that have embeddings are considered.
        """
        # Build the query using pgvector's cosine distance operator
        # cosine_distance = 1 - cosine_similarity, so lower is better
        embedding_str = "[" + ",".join(str(v) for v in jd_embedding) + "]"

        conditions = [
            "user_id = :user_id",
            "embedding IS NOT NULL",
        ]
        params: dict = {"user_id": user_id, "top_k": top_k}

        if entry_types:
            conditions.append("entry_type = ANY(:entry_types)")
            params["entry_types"] = entry_types

        where_clause = " AND ".join(conditions)

        query = text(f"""
            SELECT id, entry_type, title, organization, start_date, end_date,
                   bullet_points, tags, source,
                   1 - (embedding <=> '{embedding_str}'::vector) AS similarity
            FROM career_history_entries
            WHERE {where_clause}
            ORDER BY embedding <=> '{embedding_str}'::vector
            LIMIT :top_k
        """)

        result = await self._db.execute(query, params)
        rows = result.fetchall()

        ranked: list[RankedEntry] = []
        for row in rows:
            ranked.append(
                RankedEntry(
                    entry_id=str(row.id),
                    entry_type=row.entry_type,
                    title=row.title,
                    organization=row.organization,
                    start_date=row.start_date.isoformat() if row.start_date else None,
                    end_date=row.end_date.isoformat() if row.end_date else None,
                    bullet_points=row.bullet_points or [],
                    tags=row.tags or [],
                    source=row.source,
                    similarity_score=float(row.similarity),
                )
            )

        return ranked
