"""Primary and subagent loops that drive LLM ↔ tool-call execution."""

import json
from openai import OpenAI

from config import (
    OPENAI_KEY, GPT_MODEL, GPT_MODEL_SUB, MAX_AGENT_ITERATIONS, VERBOSE,
)
from prompts import PRIMARY_SYSTEM_PROMPT, SUBAGENT_SYSTEM_PROMPT
from tools import PRIMARY_TOOLS, PRIMARY_TOOL_HANDLERS
from tools.update_planner import get_planner_instance
from persist import (
    ConversationData, ConversationManager, PlannerStep, serialize_message,
)

_client = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=OPENAI_KEY)
    return _client


# ---------------------------------------------------------------------------
# Primary agent loop
# ---------------------------------------------------------------------------

def primary_agent_loop(
    user_prompt: str,
    conv: ConversationData,
    max_iter: int = MAX_AGENT_ITERATIONS,
):
    # Build message list from saved conversation history (as plain dicts for the API)
    messages = [m.model_dump(exclude_none=True) for m in conv.messages]

    # If this is a fresh conversation, prepend system prompt + first user message
    if not messages:
        messages = [
            {"role": "system", "content": PRIMARY_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]
    else:
        # Continuing — add the new user message
        messages.append({"role": "user", "content": user_prompt})

    state = conv.state

    for i in range(max_iter):
        print(f"\n--- Iteration {i+1} ---")

        # Inject current state so the model can plan accordingly
        state_msg = (
            f"[STATE] iteration={state.completed_iter}/{state.max_iter} | "
            f"tokens_used={state.used_tokens}/{state.max_token_budget} | "
            f"context_window={state.context_window}"
        )
        messages.append({"role": "user", "content": state_msg})

        response = _get_client().chat.completions.create(
            model=GPT_MODEL,
            messages=messages,
            tools=PRIMARY_TOOLS,
        )

        message = response.choices[0].message
        print(f"Model response: {message.content}")
        messages.append(message)

        # Update state after each iteration
        if response.usage:
            state.used_tokens += response.usage.total_tokens
        state.completed_iter = i + 1
        print(f"State: tokens={state.used_tokens}/{state.max_token_budget}, iter={state.completed_iter}/{max_iter}")

        # Persist conversation after every iteration
        _save_conversation(conv, messages)

        if state.used_tokens >= state.max_token_budget:
            print("Token budget exceeded. Stopping agent.")
            break

        if not message.tool_calls:
            print("No tool calls found in the response. Ending loop.")
            break

        for tool_call in message.tool_calls:
            handler = PRIMARY_TOOL_HANDLERS.get(tool_call.function.name)
            if handler:
                args = json.loads(tool_call.function.arguments)
                tool_output = handler(args)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": tool_output,
                })

        # Save again after tool outputs
        _save_conversation(conv, messages)


def _save_conversation(conv: ConversationData, messages: list) -> None:
    """Snapshot messages + planner into the ConversationData and persist to disk."""
    conv.messages = [serialize_message(m) for m in messages]
    planner = get_planner_instance()
    conv.planner = [PlannerStep(text=t, status=s) for t, s in planner.to_list()]
    ConversationManager.save(conv)


# ---------------------------------------------------------------------------
# Subagent loop
# ---------------------------------------------------------------------------

def subagent_loop(
    subagent_id: int,
    user_prompt: str,
    max_iter: int,
    tools: list,
    tool_handlers: dict,
):
    messages = [
        {"role": "system", "content": SUBAGENT_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    for i in range(max_iter):
        if VERBOSE >= 1:
            print(f"> Subagent {subagent_id} Iteration {i+1}")
        response = _get_client().chat.completions.create(
            model=GPT_MODEL_SUB,
            messages=messages,
            tools=tools,
        )

        message = response.choices[0].message
        if VERBOSE >= 2:
            print(f"Model response: {message.content}")
        messages.append(message)

        if not message.tool_calls:
            if VERBOSE >= 1:
                print("No tool calls found in the response. Ending loop.")
            return message.content or ""

        for tool_call in message.tool_calls:
            handler = tool_handlers.get(tool_call.function.name)
            if handler:
                args = json.loads(tool_call.function.arguments)
                tool_output = handler(args)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": tool_output,
                })

    if VERBOSE >= 1:
        print("Subagent reached max iterations without a final response.")
    return "Subagent reached max iterations without a final response."

