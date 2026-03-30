"""Career history service — CRUD operations for CareerHistoryEntry."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.career import CareerHistoryEntry
from src.schemas.career import CareerEntryCreate, CareerEntryUpdate


class CareerService:
    """Handles CRUD operations for career history entries."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def list_entries(self, user_id: uuid.UUID) -> list[CareerHistoryEntry]:
        """Return all career entries for a user, ordered by start_date desc."""
        result = await self._db.execute(
            select(CareerHistoryEntry)
            .where(CareerHistoryEntry.user_id == user_id)
            .order_by(CareerHistoryEntry.start_date.desc().nullslast())
        )
        return list(result.scalars().all())

    async def get_entry(
        self, user_id: uuid.UUID, entry_id: uuid.UUID
    ) -> CareerHistoryEntry | None:
        """Return a single entry by ID, only if owned by user."""
        result = await self._db.execute(
            select(CareerHistoryEntry).where(
                CareerHistoryEntry.id == entry_id,
                CareerHistoryEntry.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def create_entry(
        self, user_id: uuid.UUID, data: CareerEntryCreate, source: str = "user_provided"
    ) -> CareerHistoryEntry:
        """Create a new career entry."""
        entry = CareerHistoryEntry(
            user_id=user_id,
            entry_type=data.entry_type,
            title=data.title,
            organization=data.organization,
            start_date=_parse_date(data.start_date),
            end_date=_parse_date(data.end_date),
            bullet_points=data.bullet_points,
            tags=data.tags,
            source=source,
            raw_text=data.raw_text,
        )
        self._db.add(entry)
        await self._db.commit()
        await self._db.refresh(entry)
        return entry

    async def update_entry(
        self, user_id: uuid.UUID, entry_id: uuid.UUID, data: CareerEntryUpdate
    ) -> CareerHistoryEntry | None:
        """Update an existing career entry. Returns None if not found."""
        entry = await self.get_entry(user_id, entry_id)
        if entry is None:
            return None

        update_data = data.model_dump(exclude_unset=True)
        if "start_date" in update_data:
            update_data["start_date"] = _parse_date(update_data["start_date"])
        if "end_date" in update_data:
            update_data["end_date"] = _parse_date(update_data["end_date"])

        for key, value in update_data.items():
            setattr(entry, key, value)

        await self._db.commit()
        await self._db.refresh(entry)
        return entry

    async def delete_entry(self, user_id: uuid.UUID, entry_id: uuid.UUID) -> bool:
        """Delete a career entry. Returns True if deleted, False if not found."""
        entry = await self.get_entry(user_id, entry_id)
        if entry is None:
            return False
        await self._db.delete(entry)
        await self._db.commit()
        return True

    async def confirm_all(self, user_id: uuid.UUID) -> int:
        """Mark all parsed_resume entries as user_confirmed. Returns count."""
        entries = await self.list_entries(user_id)
        count = 0
        for entry in entries:
            if entry.source == "parsed_resume":
                entry.source = "user_confirmed"
                count += 1
        if count:
            await self._db.commit()
        return count


def _parse_date(date_str: str | None) -> object:
    """Parse a YYYY or YYYY-MM date string into a date object, or None."""
    if not date_str:
        return None
    from datetime import date

    parts = date_str.split("-")
    if len(parts) == 1:
        return date(int(parts[0]), 1, 1)
    if len(parts) == 2:
        return date(int(parts[0]), int(parts[1]), 1)
    return date(int(parts[0]), int(parts[1]), int(parts[2]))
