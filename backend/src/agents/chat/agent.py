"""Chat agent — LangGraph ReAct agent for freeform conversation with tools."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from typing_extensions import Annotated, TypedDict

from src.agents.chat.prompts import SYSTEM_PROMPT
from src.agents.chat.schemas import ChatResponse
from src.agents.chat.tools import _make_tools
from src.services.llm_config import LLMConfig

logger = logging.getLogger(__name__)

MAX_ITERATIONS = 5


class ChatState(TypedDict):
    """State for the Chat agent graph."""

    messages: Annotated[list[BaseMessage], add_messages]
    tool_calls_made: list[dict[str, Any]]


class ChatAgent:
    """LangGraph ReAct agent for freeform chat with career history tools.

    Unlike the single-node agents (Job Analyst, Resume Writer, Fact Checker),
    this agent uses a ReAct loop: agent → tools → agent, up to MAX_ITERATIONS.
    """

    def __init__(
        self,
        llm_config: LLMConfig,
        context: dict[str, Any],
    ) -> None:
        self._tools = _make_tools(context)
        self._model: BaseChatModel = llm_config.get_chat_model(
            "chat_agent", temperature=0.3, streaming=False
        )
        self._model_with_tools = self._model.bind_tools(self._tools)
        self._graph = self._build_graph()

    def _build_graph(self) -> Any:  # noqa: ANN401
        """Build the ReAct loop graph."""
        graph = StateGraph(ChatState)

        graph.add_node("agent", self._agent_node)
        graph.add_node("tools", ToolNode(self._tools))

        graph.set_entry_point("agent")
        graph.add_conditional_edges(
            "agent",
            self._should_continue,
            {"tools": "tools", "end": END},
        )
        graph.add_edge("tools", "agent")

        return graph.compile()

    def _should_continue(self, state: ChatState) -> str:
        """Decide whether to call tools or finish."""
        messages = state["messages"]
        last_message = messages[-1]

        # Check iteration count to prevent infinite loops
        tool_calls_count = len(state.get("tool_calls_made", []))
        if tool_calls_count >= MAX_ITERATIONS:
            return "end"

        # If the last message has tool calls, route to tools
        if isinstance(last_message, AIMessage) and last_message.tool_calls:
            return "tools"

        return "end"

    async def _agent_node(self, state: ChatState) -> dict[str, Any]:
        """Run the LLM and return its response."""
        messages = state["messages"]
        response = await self._model_with_tools.ainvoke(messages)

        # Track tool calls for reporting
        tool_calls_made = list(state.get("tool_calls_made", []))
        if isinstance(response, AIMessage) and response.tool_calls:
            for tc in response.tool_calls:
                tool_calls_made.append({
                    "name": tc["name"],
                    "args": tc["args"],
                })

        return {
            "messages": [response],
            "tool_calls_made": tool_calls_made,
        }

    async def chat(
        self,
        user_message: str,
        history: list[dict[str, str]] | None = None,
    ) -> ChatResponse:
        """Process a user message and return the assistant's response.

        Args:
            user_message: The user's message text.
            history: Optional prior conversation messages as
                     [{"role": "user"|"assistant", "content": "..."}].

        Returns:
            ChatResponse with the assistant's reply and tool usage summary.
        """
        messages: list[BaseMessage] = [SystemMessage(content=SYSTEM_PROMPT)]

        # Add conversation history
        if history:
            for msg in history:
                if msg["role"] == "user":
                    messages.append(HumanMessage(content=msg["content"]))
                elif msg["role"] == "assistant":
                    messages.append(AIMessage(content=msg["content"]))

        messages.append(HumanMessage(content=user_message))

        initial_state: ChatState = {
            "messages": messages,
            "tool_calls_made": [],
        }

        result = await self._graph.ainvoke(initial_state)

        # Extract the final assistant message
        final_messages = result.get("messages", [])
        assistant_reply = ""
        for msg in reversed(final_messages):
            if isinstance(msg, AIMessage) and msg.content and not msg.tool_calls:
                assistant_reply = str(msg.content)
                break

        if not assistant_reply:
            # Fallback: get content from last AIMessage even if it had tool calls
            for msg in reversed(final_messages):
                if isinstance(msg, AIMessage) and msg.content:
                    assistant_reply = str(msg.content)
                    break

        if not assistant_reply:
            assistant_reply = "I'm sorry, I couldn't generate a response."

        tool_calls_made = result.get("tool_calls_made", [])

        logger.info(
            "Chat response: tools_used=%d, reply_length=%d",
            len(tool_calls_made),
            len(assistant_reply),
        )

        return ChatResponse(
            message=assistant_reply,
            tool_calls_made=tool_calls_made,
        )

    @staticmethod
    def create_context(
        db: Any,  # noqa: ANN401
        user_id: uuid.UUID,
        llm_config: Any,  # noqa: ANN401
        session_id: uuid.UUID | None = None,
    ) -> dict[str, Any]:
        """Build the context dict needed by tools."""
        return {
            "db": db,
            "user_id": user_id,
            "llm_config": llm_config,
            "session_id": str(session_id) if session_id else None,
        }
