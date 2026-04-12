"""Conversation persistence layer.

Defines Pydantic models that describe the on-disk JSON format for saved
conversations and provides ``ConversationManager`` for CRUD operations
against ``~/.legate/conversations/``.
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class ToolCallFunction(BaseModel):
    """The function payload inside a tool call (name + raw JSON arguments)."""

    name: str
    arguments: str


class ToolCall(BaseModel):
    """A single tool invocation requested by the assistant."""

    id: str
    type: str = "function"
    function: ToolCallFunction


class Message(BaseModel):
    """A single message in the conversation history.

    Mirrors the OpenAI chat-completions message schema so that saved
    messages can be round-tripped back into the API via
    ``model_dump(exclude_none=True)``.
    """

    role: Literal["system", "user", "assistant", "tool"]
    content: str | None = None
    tool_calls: list[ToolCall] | None = None
    tool_call_id: str | None = None


class PlannerStep(BaseModel):
    """One step in the agent's planner to-do list.

    Status codes: 0 = incomplete, 1 = complete, -1 = failed.
    """

    text: str
    status: Literal[0, 1, -1]


class AgentState(BaseModel):
    """Runtime resource-tracking state for the primary agent loop."""

    used_tokens: int = 0
    max_token_budget: int = 150_000
    completed_iter: int = 0
    max_iter: int = 32
    context_window: int = 1_050_000


class ConversationData(BaseModel):
    """Top-level model representing a persisted conversation.

    Each conversation is stored as a single JSON file whose structure
    is fully described — and validated — by this model.
    """

    id: str
    title: str
    created_at: datetime
    updated_at: datetime
    model: str
    state: AgentState
    planner: list[PlannerStep]
    messages: list[Message]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def serialize_message(msg) -> Message:
    """Convert an OpenAI ChatCompletionMessage or a plain dict to a Message model."""
    if isinstance(msg, dict):
        return Message(**msg)
    # OpenAI ChatCompletionMessage (Pydantic object)
    data: dict = {}
    data["role"] = msg.role
    data["content"] = msg.content
    if getattr(msg, "tool_call_id", None):
        data["tool_call_id"] = msg.tool_call_id
    if getattr(msg, "tool_calls", None):
        data["tool_calls"] = [
            ToolCall(
                id=tc.id,
                type=tc.type,
                function=ToolCallFunction(
                    name=tc.function.name,
                    arguments=tc.function.arguments,
                ),
            )
            for tc in msg.tool_calls
        ]
    return Message(**data)


# ---------------------------------------------------------------------------
# ConversationManager
# ---------------------------------------------------------------------------

CONVERSATIONS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "conversations")


class ConversationManager:
    """CRUD operations for conversation JSON files on disk."""

    @staticmethod
    def _ensure_dir():
        """Create the conversations directory if it doesn't exist."""
        os.makedirs(CONVERSATIONS_DIR, exist_ok=True)

    @staticmethod
    def new(first_prompt: str, model: str, state: AgentState) -> ConversationData:
        """Create a new ``ConversationData`` with a generated ID and title."""
        now = datetime.now(timezone.utc)
        title = first_prompt[:80].replace("\n", " ").strip()
        return ConversationData(
            id=uuid.uuid4().hex[:12],
            title=title,
            created_at=now,
            updated_at=now,
            model=model,
            state=state,
            planner=[],
            messages=[],
        )

    @staticmethod
    def save(conv: ConversationData) -> None:
        """Write the conversation to disk as ``{id}.json``, updating its timestamp."""
        ConversationManager._ensure_dir()
        conv.updated_at = datetime.now(timezone.utc)
        path = os.path.join(CONVERSATIONS_DIR, f"{conv.id}.json")
        with open(path, "w", encoding="utf-8") as f:
            f.write(conv.model_dump_json(indent=2))

    @staticmethod
    def load(conv_id: str) -> ConversationData:
        """Load and validate a conversation from disk by its ID."""
        path = os.path.join(CONVERSATIONS_DIR, f"{conv_id}.json")
        with open(path, "r", encoding="utf-8") as f:
            return ConversationData.model_validate_json(f.read())

    @staticmethod
    def list_all() -> list[ConversationData]:
        """Return all saved conversations, sorted by most recently updated."""
        ConversationManager._ensure_dir()
        convs: list[ConversationData] = []
        for fname in os.listdir(CONVERSATIONS_DIR):
            if not fname.endswith(".json"):
                continue
            path = os.path.join(CONVERSATIONS_DIR, fname)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    convs.append(ConversationData.model_validate_json(f.read()))
            except Exception as e:
                print(f"Warning: skipping invalid conversation file {fname}: {e}")
        convs.sort(key=lambda c: c.updated_at, reverse=True)
        return convs

    @staticmethod
    def delete(conv_id: str) -> None:
        """Remove a conversation's JSON file from disk."""
        path = os.path.join(CONVERSATIONS_DIR, f"{conv_id}.json")
        if os.path.exists(path):
            os.remove(path)
