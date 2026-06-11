"""Context compression cascade for the agent loops.

All helpers operate on message lists of plain dicts (OpenAI chat format).
Compression is batched and threshold-gated: old messages are only mutated
when the context crosses a limit, so the message prefix stays byte-stable
between compressions and prompt caching keeps working.
"""

import json

from config import GPT_MODEL_SUB, KEEP_RECENT_BLOCKS, NOTES_MIN_CHARS

EVICTION_MARKER = "[evicted — output archived; use read_history to retrieve]"
EVICTION_MARKER_EPHEMERAL = "[evicted — old output cleared to save context]"

SUMMARY_REQUEST = """The conversation above is about to be compacted to free context space.
Produce a concise but complete summary with these sections:
1. Primary Request — what the user originally asked for.
2. Decisions & Why — key choices made and the reasoning behind them.
3. Key Results / Facts — important findings, data, and outputs so far.
4. Files Touched — files read, written, or modified, with their paths.
5. Errors & Fixes — problems encountered and how they were resolved.
6. Loaded Skills — names of any skills read via read_skill, so they can be re-read.
7. Pending Work — what remains to be done.
Respond with only the summary."""


def split_blocks(messages: list) -> tuple[list, list]:
    """Partition messages into (head, blocks).

    ``head`` is everything before the first assistant message. Each block
    starts at an assistant message and includes every following message
    (tool replies, interleaved user messages) up to the next assistant
    message, so an assistant's tool_calls are never separated from their
    tool results.
    """
    head: list = []
    blocks: list = []
    current: list | None = None
    for m in messages:
        if m.get("role") == "assistant":
            if current is not None:
                blocks.append(current)
            current = [m]
        elif current is None:
            head.append(m)
        else:
            current.append(m)
    if current is not None:
        blocks.append(current)
    return head, blocks


def join_blocks(head: list, blocks: list) -> list:
    out = list(head)
    for b in blocks:
        out.extend(b)
    return out


def strip_state_messages(messages: list) -> list:
    """Remove all [STATE] user messages; the loop appends a fresh one each iteration."""
    return [
        m for m in messages
        if not (
            m.get("role") == "user"
            and isinstance(m.get("content"), str)
            and m["content"].startswith("[STATE]")
        )
    ]


def estimate_tokens(messages: list) -> int:
    """Rough token estimate (~4 chars/token) used between API usage reports."""
    return sum(len(json.dumps(m, default=str)) for m in messages) // 4


def evict_old_tool_outputs(
    messages: list,
    keep_blocks: int = KEEP_RECENT_BLOCKS,
    archive_fn=None,
    marker: str = EVICTION_MARKER,
) -> int:
    """Blank tool-message contents outside the last ``keep_blocks`` iteration blocks.

    Messages are mutated in place but never removed, preserving the
    assistant-tool_calls/tool pairing the API requires. Returns the number
    of tool outputs evicted. ``archive_fn(msg_dict, iteration)`` is called
    with the original message before it is blanked.
    """
    _, blocks = split_blocks(messages)
    old_blocks = blocks[:-keep_blocks] if keep_blocks > 0 else blocks
    evicted = 0
    for block_idx, block in enumerate(old_blocks):
        for m in block:
            if m.get("role") == "tool" and m.get("content") and m["content"] != marker:
                if archive_fn:
                    archive_fn(dict(m), block_idx + 1)
                m["content"] = marker
                evicted += 1
    return evicted


def compact_messages(
    messages: list,
    client,
    planner,
    archive_fn,
    keep_blocks: int = KEEP_RECENT_BLOCKS,
) -> list:
    """Full compaction: archive old blocks and replace them with a summary message.

    The summary is taken from the planner's accumulated notes when they are
    substantial (free), otherwise from one summarization call to the sub
    model. The call is formed as the existing messages plus one final user
    message, so it shares the cached prompt prefix. Returns the new message
    list: system prompt(s) + summary user message + the last ``keep_blocks``
    blocks verbatim.
    """
    head, blocks = split_blocks(messages)
    if len(blocks) <= keep_blocks:
        return messages

    old_blocks, recent_blocks = blocks[:-keep_blocks], blocks[-keep_blocks:]

    # Build the summary before mutating anything.
    notes = planner.notes_text()
    if len(notes) >= NOTES_MIN_CHARS:
        summary = f"Accumulated notes from the work so far:\n{notes}"
    else:
        response = client.chat.completions.create(
            model=GPT_MODEL_SUB,
            messages=messages + [{"role": "user", "content": SUMMARY_REQUEST}],
        )
        summary = response.choices[0].message.content or "(summary unavailable)"

    # Archive everything that leaves the live context.
    for m in head:
        if m.get("role") != "system":
            archive_fn(dict(m), 0)
    for block_idx, block in enumerate(old_blocks):
        for m in block:
            archive_fn(dict(m), block_idx + 1)

    system_msgs = [m for m in head if m.get("role") == "system"]
    plan_text = planner.stringify() or "(empty)"
    compacted_msg = {
        "role": "user",
        "content": (
            f"[COMPACTED HISTORY] Older conversation history was compressed to save context.\n\n"
            f"{summary}\n\n"
            f"Current plan:\n{plan_text}\n\n"
            f"The full older history is archived on disk; use read_history to retrieve details."
        ),
    }
    return system_msgs + [compacted_msg] + [m for b in recent_blocks for m in b]
