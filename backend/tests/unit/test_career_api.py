"""Tests for career history CRUD API endpoints (Phase 2.4)."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SAMPLE_ENTRY = {
    "entry_type": "work_experience",
    "title": "Senior Software Engineer",
    "organization": "Acme Corp",
    "start_date": "2020-01",
    "end_date": "2023-06",
    "bullet_points": [
        "Built scalable APIs",
        "Led migration to microservices",
    ],
    "tags": ["Python", "FastAPI", "AWS"],
}


async def _create_entry(
    client: AsyncClient, auth_headers: dict[str, str], data: dict | None = None
) -> dict:
    """Helper to create an entry and return the response JSON."""
    resp = await client.post(
        "/api/v1/career/entries",
        headers=auth_headers,
        json=data or SAMPLE_ENTRY,
    )
    assert resp.status_code == 201
    return resp.json()


# ---------------------------------------------------------------------------
# CRUD Tests
# ---------------------------------------------------------------------------


class TestCreateEntry:
    @pytest.mark.asyncio
    async def test_create_entry(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        data = await _create_entry(client, auth_headers)

        assert data["title"] == "Senior Software Engineer"
        assert data["organization"] == "Acme Corp"
        assert data["entry_type"] == "work_experience"
        assert data["source"] == "user_provided"
        assert len(data["bullet_points"]) == 2
        assert "Python" in data["tags"]
        assert data["id"]  # UUID string

    @pytest.mark.asyncio
    async def test_create_minimal_entry(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        resp = await client.post(
            "/api/v1/career/entries",
            headers=auth_headers,
            json={"entry_type": "education", "title": "B.S. Computer Science"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "B.S. Computer Science"
        assert data["organization"] is None
        assert data["bullet_points"] == []
        assert data["tags"] == []

    @pytest.mark.asyncio
    async def test_create_requires_auth(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/api/v1/career/entries",
            json=SAMPLE_ENTRY,
        )
        assert resp.status_code == 403


class TestListEntries:
    @pytest.mark.asyncio
    async def test_list_empty(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        resp = await client.get("/api/v1/career/entries", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_list_with_entries(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        await _create_entry(client, auth_headers)
        await _create_entry(
            client,
            auth_headers,
            {"entry_type": "education", "title": "B.S. CS"},
        )

        resp = await client.get("/api/v1/career/entries", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2

    @pytest.mark.asyncio
    async def test_list_isolates_users(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        """Entries from one user shouldn't appear for another."""
        await _create_entry(client, auth_headers)

        # Register a second user
        resp = await client.post(
            "/api/v1/auth/register",
            json={
                "name": "Other User",
                "email": f"other-{uuid.uuid4().hex[:8]}@test.com",
                "password": "testpass123",
            },
        )
        other_headers = {
            "Authorization": f"Bearer {resp.json()['access_token']}"
        }

        resp = await client.get("/api/v1/career/entries", headers=other_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_list_requires_auth(self, client: AsyncClient) -> None:
        resp = await client.get("/api/v1/career/entries")
        assert resp.status_code == 403


class TestGetEntry:
    @pytest.mark.asyncio
    async def test_get_entry(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        created = await _create_entry(client, auth_headers)
        entry_id = created["id"]

        resp = await client.get(
            f"/api/v1/career/entries/{entry_id}", headers=auth_headers
        )
        assert resp.status_code == 200
        assert resp.json()["id"] == entry_id
        assert resp.json()["title"] == "Senior Software Engineer"

    @pytest.mark.asyncio
    async def test_get_nonexistent(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        fake_id = str(uuid.uuid4())
        resp = await client.get(
            f"/api/v1/career/entries/{fake_id}", headers=auth_headers
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_other_users_entry(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        """Cannot access another user's entry."""
        created = await _create_entry(client, auth_headers)
        entry_id = created["id"]

        resp = await client.post(
            "/api/v1/auth/register",
            json={
                "name": "Other",
                "email": f"other-{uuid.uuid4().hex[:8]}@test.com",
                "password": "testpass123",
            },
        )
        other_headers = {
            "Authorization": f"Bearer {resp.json()['access_token']}"
        }

        resp = await client.get(
            f"/api/v1/career/entries/{entry_id}", headers=other_headers
        )
        assert resp.status_code == 404


class TestUpdateEntry:
    @pytest.mark.asyncio
    async def test_update_entry(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        created = await _create_entry(client, auth_headers)
        entry_id = created["id"]

        resp = await client.put(
            f"/api/v1/career/entries/{entry_id}",
            headers=auth_headers,
            json={"title": "Staff Engineer", "tags": ["Python", "Go"]},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "Staff Engineer"
        assert data["tags"] == ["Python", "Go"]
        # Unchanged fields preserved
        assert data["organization"] == "Acme Corp"

    @pytest.mark.asyncio
    async def test_update_source(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        created = await _create_entry(client, auth_headers)
        entry_id = created["id"]

        resp = await client.put(
            f"/api/v1/career/entries/{entry_id}",
            headers=auth_headers,
            json={"source": "user_confirmed"},
        )
        assert resp.status_code == 200
        assert resp.json()["source"] == "user_confirmed"

    @pytest.mark.asyncio
    async def test_update_nonexistent(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        fake_id = str(uuid.uuid4())
        resp = await client.put(
            f"/api/v1/career/entries/{fake_id}",
            headers=auth_headers,
            json={"title": "New Title"},
        )
        assert resp.status_code == 404


class TestDeleteEntry:
    @pytest.mark.asyncio
    async def test_delete_entry(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        created = await _create_entry(client, auth_headers)
        entry_id = created["id"]

        resp = await client.delete(
            f"/api/v1/career/entries/{entry_id}", headers=auth_headers
        )
        assert resp.status_code == 204

        # Verify gone
        resp = await client.get(
            f"/api/v1/career/entries/{entry_id}", headers=auth_headers
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_nonexistent(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        fake_id = str(uuid.uuid4())
        resp = await client.delete(
            f"/api/v1/career/entries/{fake_id}", headers=auth_headers
        )
        assert resp.status_code == 404


class TestConfirmAll:
    @pytest.mark.asyncio
    async def test_confirm_all(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        # Create entries with parsed_resume source by creating and then updating
        entry = await _create_entry(client, auth_headers)
        entry_id = entry["id"]
        await client.put(
            f"/api/v1/career/entries/{entry_id}",
            headers=auth_headers,
            json={"source": "parsed_resume"},
        )

        resp = await client.post(
            "/api/v1/career/entries/confirm-all", headers=auth_headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["confirmed"] == 1

        # Verify source changed
        resp = await client.get(
            f"/api/v1/career/entries/{entry_id}", headers=auth_headers
        )
        assert resp.json()["source"] == "user_confirmed"

    @pytest.mark.asyncio
    async def test_confirm_all_no_parsed(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        await _create_entry(client, auth_headers)  # source=user_provided

        resp = await client.post(
            "/api/v1/career/entries/confirm-all", headers=auth_headers
        )
        assert resp.status_code == 200
        assert resp.json()["confirmed"] == 0
