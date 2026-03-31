"""Tests for the Chat agent and chat endpoint."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from src.agents.chat.schemas import ChatResponse


# ---------------------------------------------------------------------------
# Schema tests
# ---------------------------------------------------------------------------


class TestChatSchemas:
    """Tests for chat-related Pydantic schemas."""

    def test_chat_response_basic(self) -> None:
        resp = ChatResponse(message="Hello!", tool_calls_made=[])
        assert resp.message == "Hello!"
        assert resp.tool_calls_made == []

    def test_chat_response_with_tools(self) -> None:
        resp = ChatResponse(
            message="Found 3 entries.",
            tool_calls_made=[
                {"name": "search_career_history", "args": {"query": "Python"}}
            ],
        )
        assert len(resp.tool_calls_made) == 1
        assert resp.tool_calls_made[0]["name"] == "search_career_history"

    def test_chat_response_roundtrip(self) -> None:
        resp = ChatResponse(
            message="Test",
            tool_calls_made=[{"name": "get_session_status", "args": {}}],
        )
        data = resp.model_dump()
        restored = ChatResponse.model_validate(data)
        assert restored.message == "Test"
        assert len(restored.tool_calls_made) == 1


# ---------------------------------------------------------------------------
# Agent unit tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestChatAgent:
    """Tests for the ChatAgent class."""

    @patch("src.agents.chat.agent.StateGraph")
    async def test_chat_simple_response(self, mock_sg_cls: MagicMock) -> None:
        """Agent returns a simple text response."""
        from src.agents.chat.agent import ChatAgent

        mock_llm_config = MagicMock()
        mock_model = MagicMock()
        mock_model.bind_tools.return_value = mock_model
        mock_llm_config.get_chat_model.return_value = mock_model

        # Mock the compiled graph
        mock_graph = MagicMock()
        mock_compiled = AsyncMock()
        mock_compiled.ainvoke.return_value = {
            "messages": [
                SystemMessage(content="system"),
                HumanMessage(content="hello"),
                AIMessage(content="Hi! How can I help?"),
            ],
            "tool_calls_made": [],
        }
        mock_graph.compile.return_value = mock_compiled
        mock_sg_cls.return_value = mock_graph

        context = {"db": MagicMock(), "user_id": "user-1", "llm_config": mock_llm_config}
        agent = ChatAgent(mock_llm_config, context)
        result = await agent.chat("hello")

        assert isinstance(result, ChatResponse)
        assert result.message == "Hi! How can I help?"
        assert result.tool_calls_made == []

    @patch("src.agents.chat.agent.StateGraph")
    async def test_chat_with_tool_calls(self, mock_sg_cls: MagicMock) -> None:
        """Agent returns response with tool call history."""
        from src.agents.chat.agent import ChatAgent

        mock_llm_config = MagicMock()
        mock_model = MagicMock()
        mock_model.bind_tools.return_value = mock_model
        mock_llm_config.get_chat_model.return_value = mock_model

        mock_graph = MagicMock()
        mock_compiled = AsyncMock()
        mock_compiled.ainvoke.return_value = {
            "messages": [
                SystemMessage(content="system"),
                HumanMessage(content="Do I have Python experience?"),
                AIMessage(content="Yes, you have Python experience from TechCo."),
            ],
            "tool_calls_made": [
                {"name": "search_career_history", "args": {"query": "Python"}}
            ],
        }
        mock_graph.compile.return_value = mock_compiled
        mock_sg_cls.return_value = mock_graph

        context = {"db": MagicMock(), "user_id": "user-1", "llm_config": mock_llm_config}
        agent = ChatAgent(mock_llm_config, context)
        result = await agent.chat("Do I have Python experience?")

        assert "Python" in result.message
        assert len(result.tool_calls_made) == 1
        assert result.tool_calls_made[0]["name"] == "search_career_history"

    @patch("src.agents.chat.agent.StateGraph")
    async def test_chat_with_history(self, mock_sg_cls: MagicMock) -> None:
        """Agent processes conversation history."""
        from src.agents.chat.agent import ChatAgent

        mock_llm_config = MagicMock()
        mock_model = MagicMock()
        mock_model.bind_tools.return_value = mock_model
        mock_llm_config.get_chat_model.return_value = mock_model

        mock_graph = MagicMock()
        mock_compiled = AsyncMock()
        mock_compiled.ainvoke.return_value = {
            "messages": [AIMessage(content="Sure, noted.")],
            "tool_calls_made": [],
        }
        mock_graph.compile.return_value = mock_compiled
        mock_sg_cls.return_value = mock_graph

        context = {"db": MagicMock(), "user_id": "user-1", "llm_config": mock_llm_config}
        agent = ChatAgent(mock_llm_config, context)
        result = await agent.chat(
            "Now add Kubernetes to my skills",
            history=[
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi!"},
            ],
        )

        # Verify history was included in the initial state
        call_args = mock_compiled.ainvoke.call_args[0][0]
        messages = call_args["messages"]
        # system + 2 history + 1 new user message = 4
        assert len(messages) == 4
        assert isinstance(messages[0], SystemMessage)
        assert isinstance(messages[1], HumanMessage)
        assert isinstance(messages[2], AIMessage)
        assert isinstance(messages[3], HumanMessage)

    @patch("src.agents.chat.agent.StateGraph")
    async def test_chat_empty_response_fallback(self, mock_sg_cls: MagicMock) -> None:
        """Agent returns fallback when no content in messages."""
        from src.agents.chat.agent import ChatAgent

        mock_llm_config = MagicMock()
        mock_model = MagicMock()
        mock_model.bind_tools.return_value = mock_model
        mock_llm_config.get_chat_model.return_value = mock_model

        mock_graph = MagicMock()
        mock_compiled = AsyncMock()
        mock_compiled.ainvoke.return_value = {
            "messages": [HumanMessage(content="test")],
            "tool_calls_made": [],
        }
        mock_graph.compile.return_value = mock_compiled
        mock_sg_cls.return_value = mock_graph

        context = {"db": MagicMock(), "user_id": "user-1", "llm_config": mock_llm_config}
        agent = ChatAgent(mock_llm_config, context)
        result = await agent.chat("test")

        assert "couldn't generate" in result.message.lower()

    @patch("src.agents.chat.agent.StateGraph")
    async def test_chat_llm_error(self, mock_sg_cls: MagicMock) -> None:
        """Agent propagates LLM errors."""
        from src.agents.chat.agent import ChatAgent

        mock_llm_config = MagicMock()
        mock_model = MagicMock()
        mock_model.bind_tools.return_value = mock_model
        mock_llm_config.get_chat_model.return_value = mock_model

        mock_graph = MagicMock()
        mock_compiled = AsyncMock()
        mock_compiled.ainvoke.side_effect = RuntimeError("LLM timeout")
        mock_graph.compile.return_value = mock_compiled
        mock_sg_cls.return_value = mock_graph

        context = {"db": MagicMock(), "user_id": "user-1", "llm_config": mock_llm_config}
        agent = ChatAgent(mock_llm_config, context)
        with pytest.raises(RuntimeError, match="LLM timeout"):
            await agent.chat("test")


# ---------------------------------------------------------------------------
# Tools tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestChatTools:
    """Tests for the chat agent tools."""

    async def test_search_career_history(self) -> None:
        """search_career_history returns formatted results."""
        from src.agents.chat.tools import _make_tools
        from src.schemas.matching import RankedEntry

        mock_retrieval = MagicMock()
        mock_retrieval.generate_embedding = AsyncMock(return_value=[0.1] * 1536)
        mock_retrieval.embed_all_entries = AsyncMock()
        mock_retrieval.find_relevant_entries = AsyncMock(return_value=[
            RankedEntry(
                entry_id="e1", entry_type="work_experience",
                title="Backend Dev", organization="TechCo",
                start_date="2020-01", end_date="2023-12",
                bullet_points=["Built APIs"], tags=["Python"],
                source="user_confirmed", similarity_score=0.9,
            ),
        ])

        context = {
            "db": MagicMock(),
            "user_id": "user-1",
            "llm_config": MagicMock(),
        }

        tools = _make_tools(context)
        search_tool = tools[0]  # search_career_history

        with patch("src.services.retrieval.RetrievalService", return_value=mock_retrieval):
            result = await search_tool.ainvoke({"query": "Python"})

        assert "Backend Dev" in result
        assert "TechCo" in result

    async def test_search_career_history_no_results(self) -> None:
        """search_career_history handles empty results."""
        from src.agents.chat.tools import _make_tools

        mock_retrieval = MagicMock()
        mock_retrieval.generate_embedding = AsyncMock(return_value=[0.1] * 1536)
        mock_retrieval.embed_all_entries = AsyncMock()
        mock_retrieval.find_relevant_entries = AsyncMock(return_value=[])

        context = {
            "db": MagicMock(),
            "user_id": "user-1",
            "llm_config": MagicMock(),
        }

        tools = _make_tools(context)
        search_tool = tools[0]

        with patch("src.services.retrieval.RetrievalService", return_value=mock_retrieval):
            result = await search_tool.ainvoke({"query": "Kubernetes"})

        assert "No matching" in result

    async def test_add_career_entry(self) -> None:
        """add_career_entry creates an entry in the DB."""
        from src.agents.chat.tools import _make_tools

        mock_db = AsyncMock()
        mock_db.add = MagicMock()

        # After commit + refresh, the entry gets an id
        mock_entry_instance = MagicMock()
        mock_entry_instance.id = "new-entry-id"

        context = {
            "db": mock_db,
            "user_id": "user-1",
            "llm_config": MagicMock(),
        }

        tools = _make_tools(context)
        add_tool = tools[1]  # add_career_entry

        with patch("src.models.career.CareerHistoryEntry", return_value=mock_entry_instance):
            result = await add_tool.ainvoke({
                "title": "ML Engineer",
                "entry_type": "work_experience",
                "bullet_points": ["Trained models"],
                "organization": "AI Corp",
                "tags": ["ML", "Python"],
            })

        assert "ML Engineer" in result

    async def test_get_session_status_no_session(self) -> None:
        """get_session_status reports when no session is active."""
        from src.agents.chat.tools import _make_tools

        context = {
            "db": MagicMock(),
            "user_id": "user-1",
            "llm_config": MagicMock(),
            "session_id": None,
        }

        tools = _make_tools(context)
        status_tool = tools[2]  # get_session_status

        result = await status_tool.ainvoke({})
        assert "No active session" in result


# ---------------------------------------------------------------------------
# Context helper tests
# ---------------------------------------------------------------------------


class TestChatContext:
    """Tests for the create_context helper."""

    def test_create_context_with_session(self) -> None:
        from src.agents.chat.agent import ChatAgent

        import uuid

        ctx = ChatAgent.create_context(
            db=MagicMock(),
            user_id=uuid.uuid4(),
            llm_config=MagicMock(),
            session_id=uuid.uuid4(),
        )
        assert ctx["session_id"] is not None
        assert ctx["db"] is not None

    def test_create_context_without_session(self) -> None:
        from src.agents.chat.agent import ChatAgent

        import uuid

        ctx = ChatAgent.create_context(
            db=MagicMock(),
            user_id=uuid.uuid4(),
            llm_config=MagicMock(),
        )
        assert ctx["session_id"] is None


# ---------------------------------------------------------------------------
# Endpoint tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestChatEndpoint:
    """Tests for the POST /chat/message endpoint."""

    @patch("src.api.chat.ChatAgent")
    @patch("src.api.chat.get_llm_config")
    async def test_chat_message_success(
        self,
        mock_get_config: MagicMock,
        mock_agent_cls: MagicMock,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """POST /chat/message returns a chat response."""
        mock_get_config.return_value = MagicMock()

        mock_agent = MagicMock()
        mock_agent.chat = AsyncMock(return_value=ChatResponse(
            message="Hello! How can I help you?",
            tool_calls_made=[],
        ))
        mock_agent_cls.return_value = mock_agent

        resp = await client.post(
            "/api/v1/chat/message",
            json={"message": "Hello!"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["message"] == "Hello! How can I help you?"
        assert data["tool_calls_made"] == []

    @patch("src.api.chat.ChatAgent")
    @patch("src.api.chat.get_llm_config")
    async def test_chat_message_with_session(
        self,
        mock_get_config: MagicMock,
        mock_agent_cls: MagicMock,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """POST /chat/message accepts an optional session_id."""
        mock_get_config.return_value = MagicMock()

        mock_agent = MagicMock()
        mock_agent.chat = AsyncMock(return_value=ChatResponse(
            message="Session loaded.",
            tool_calls_made=[{"name": "get_session_status", "args": {}}],
        ))
        mock_agent_cls.return_value = mock_agent

        import uuid

        resp = await client.post(
            "/api/v1/chat/message",
            json={
                "message": "What's my session status?",
                "session_id": str(uuid.uuid4()),
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["tool_calls_made"][0]["name"] == "get_session_status"

    @patch("src.api.chat.ChatAgent")
    @patch("src.api.chat.get_llm_config")
    async def test_chat_message_with_history(
        self,
        mock_get_config: MagicMock,
        mock_agent_cls: MagicMock,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """POST /chat/message passes conversation history."""
        mock_get_config.return_value = MagicMock()

        mock_agent = MagicMock()
        mock_agent.chat = AsyncMock(return_value=ChatResponse(
            message="Got it.",
            tool_calls_made=[],
        ))
        mock_agent_cls.return_value = mock_agent

        resp = await client.post(
            "/api/v1/chat/message",
            json={
                "message": "Actually, add a Python tag",
                "history": [
                    {"role": "user", "content": "Hi"},
                    {"role": "assistant", "content": "Hello!"},
                ],
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        # Verify history was passed to agent
        call_args = mock_agent.chat.call_args
        assert call_args.kwargs.get("history") is not None
        assert len(call_args.kwargs["history"]) == 2

    @patch("src.api.chat.ChatAgent")
    @patch("src.api.chat.get_llm_config")
    async def test_chat_message_agent_error(
        self,
        mock_get_config: MagicMock,
        mock_agent_cls: MagicMock,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """POST /chat/message returns 422 when agent fails."""
        mock_get_config.return_value = MagicMock()

        mock_agent = MagicMock()
        mock_agent.chat = AsyncMock(side_effect=RuntimeError("LLM error"))
        mock_agent_cls.return_value = mock_agent

        resp = await client.post(
            "/api/v1/chat/message",
            json={"message": "Hello!"},
            headers=auth_headers,
        )
        assert resp.status_code == 422
        assert "Chat agent error" in resp.json()["detail"]

    async def test_chat_message_no_auth(
        self, client: AsyncClient
    ) -> None:
        """POST /chat/message returns 401/403 without auth."""
        resp = await client.post(
            "/api/v1/chat/message",
            json={"message": "Hello!"},
        )
        assert resp.status_code in (401, 403)

    @patch("src.api.chat.get_llm_config")
    async def test_chat_message_invalid_session_id(
        self,
        mock_get_config: MagicMock,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """POST /chat/message returns 400 for invalid session_id format."""
        mock_get_config.return_value = MagicMock()

        resp = await client.post(
            "/api/v1/chat/message",
            json={"message": "Hello!", "session_id": "not-a-uuid"},
            headers=auth_headers,
        )
        assert resp.status_code == 400
        assert "Invalid session_id" in resp.json()["detail"]

    async def test_chat_message_empty_message(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        """POST /chat/message rejects empty messages."""
        resp = await client.post(
            "/api/v1/chat/message",
            json={"message": ""},
            headers=auth_headers,
        )
        assert resp.status_code == 422  # Pydantic validation error
