"""Primary and subagent loops that drive LLM ↔ tool-call execution."""

import itertools
import json
from openai import OpenAI

from config import (
    OPENAI_KEY, GPT_MODEL, GPT_MODEL_SUB, GPT_MODEL_CONTEXT_WINDOW,
    MAX_AGENT_ITERATIONS, VERBOSE,
    MAX_OUTPUT_TOKENS, COMPACT_BUFFER,
)
from settings import fmt_limit, get_settings
from prompts import PRIMARY_SYSTEM_PROMPT, SUBAGENT_SYSTEM_PROMPT
from tools import PRIMARY_TOOLS, PRIMARY_TOOL_HANDLERS
from tools.update_planner import get_planner_instance
from tools.read_history import set_active_conversation
from context import (
    EVICTION_MARKER_EPHEMERAL, compact_messages, estimate_tokens,
    evict_old_tool_outputs, strip_state_messages,
)
from persist import (
    ConversationData, ConversationManager, PlannerStep, append_archive,
    serialize_message,
)

_client = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=OPENAI_KEY)
    return _client


def _effective_limit(context_window: int) -> int:
    """Token ceiling for the live context: window minus reply room and buffer, hard-capped.

    A max_context_tokens setting of -1 disables the hard cap; the window-based
    limit always applies.
    """
    limit = context_window - MAX_OUTPUT_TOKENS - COMPACT_BUFFER
    cap = get_settings().max_context_tokens
    if cap > 0:
        limit = min(limit, cap)
    return limit


def _as_dict(message) -> dict:
    """Normalize an OpenAI ChatCompletionMessage (or dict) to a plain dict."""
    return serialize_message(message).model_dump(exclude_none=True)


# ---------------------------------------------------------------------------
# Primary agent loop
# ---------------------------------------------------------------------------

def primary_agent_loop(
    user_prompt: str,
    conv: ConversationData,
    max_iter: int = MAX_AGENT_ITERATIONS,
):
    set_active_conversation(conv.id)

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
    limit = _effective_limit(state.context_window)
    keep_blocks = get_settings().keep_recent_blocks
    archive_fn = lambda msg, iteration: append_archive(conv.id, {"iteration": iteration, **msg})

    iterations = range(max_iter) if max_iter >= 0 else itertools.count()
    for i in iterations:
        print(f"\n--- Iteration {i+1} ---")

        # Compression cascade — batched and threshold-gated so the message
        # prefix stays stable (and prompt-cacheable) between compressions.
        if state.context_tokens >= limit:
            evicted = evict_old_tool_outputs(messages, keep_blocks, archive_fn)
            print(f"Context over limit ({state.context_tokens} >= {limit}): evicted {evicted} old tool outputs.")
            if estimate_tokens(messages) >= limit:
                messages = compact_messages(
                    messages, _get_client(), get_planner_instance(), archive_fn, keep_blocks,
                )
                print("Compacted older history into a summary message.")
            state.context_tokens = estimate_tokens(messages)

        # Inject current state so the model can plan accordingly (only the
        # latest [STATE] message is kept in context)
        messages = strip_state_messages(messages)
        state_msg = (
            f"[STATE] iteration={state.completed_iter}/{fmt_limit(state.max_iter)} | "
            f"tokens_used={state.used_tokens}/{fmt_limit(state.max_token_budget)} | "
            f"context_tokens={state.context_tokens} | "
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
        messages.append(_as_dict(message))

        # Update state after each iteration
        if response.usage:
            state.used_tokens += response.usage.total_tokens
            # prompt + completion of this call ≈ the next call's context size
            state.context_tokens = response.usage.total_tokens
        state.completed_iter = i + 1
        print(f"State: tokens={state.used_tokens}/{fmt_limit(state.max_token_budget)}, "
              f"context={state.context_tokens}, iter={state.completed_iter}/{fmt_limit(max_iter)}")

        # Persist conversation after every iteration
        _save_conversation(conv, messages)

        if state.max_token_budget > 0 and state.used_tokens >= state.max_token_budget:
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
    conv.notes = list(planner.notes)
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

    limit = _effective_limit(GPT_MODEL_CONTEXT_WINDOW[GPT_MODEL_SUB])
    context_tokens = 0

    for i in range(max_iter):
        if VERBOSE >= 1:
            print(f"> Subagent {subagent_id} Iteration {i+1}")

        # Subagent contexts are ephemeral: evict old tool outputs without archiving.
        if context_tokens >= limit:
            evicted = evict_old_tool_outputs(
                messages, get_settings().keep_recent_blocks,
                archive_fn=None, marker=EVICTION_MARKER_EPHEMERAL,
            )
            if VERBOSE >= 1:
                print(f"> Subagent {subagent_id}: context over limit, evicted {evicted} old tool outputs.")
            context_tokens = estimate_tokens(messages)

        response = _get_client().chat.completions.create(
            model=GPT_MODEL_SUB,
            messages=messages,
            tools=tools,
        )

        message = response.choices[0].message
        if VERBOSE >= 2:
            print(f"Model response: {message.content}")
        messages.append(_as_dict(message))
        if response.usage:
            context_tokens = response.usage.total_tokens

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
