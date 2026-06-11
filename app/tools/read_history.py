import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from persist import archive_path

DEBUG_PRINT = True
MAX_RESULT_CHARS = 8_000

_active_conv_id = None


def set_active_conversation(conv_id: str) -> None:
    """Bind the tool to the conversation whose archive should be searched."""
    global _active_conv_id
    _active_conv_id = conv_id


def read_history(query: str = "", start_iter: int = 0, end_iter: int = 0) -> str:
    """Search the archived (evicted/compacted) history of the active conversation."""
    if not _active_conv_id:
        return "No active conversation; history is unavailable."
    path = archive_path(_active_conv_id)
    if not os.path.isfile(path):
        return "No archived history yet — nothing has been evicted or compacted."

    entries = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    matches = []
    for e in entries:
        iteration = e.get("iteration", 0)
        if start_iter and iteration < start_iter:
            continue
        if end_iter and iteration > end_iter:
            continue
        content = e.get("content") or ""
        if query and query.lower() not in content.lower():
            continue
        matches.append((iteration, e.get("role", "?"), content))

    if not matches:
        return "No archived messages matched the given query/range."

    if DEBUG_PRINT:
        print(f"[read_history] {len(matches)} archived messages matched (query={query!r}).")

    parts = []
    used = 0
    for iteration, role, content in matches:
        snippet = f"[iter {iteration}] {role}: {content}"
        if used + len(snippet) > MAX_RESULT_CHARS:
            remaining = len(matches) - len(parts)
            parts.append(f"... ({remaining} more matching messages truncated; narrow your query or range)")
            break
        parts.append(snippet)
        used += len(snippet)
    return "\n\n".join(parts)


schema = {
    "type": "function",
    "function": {
        "name": "read_history",
        "description": (
            "Searches the archived conversation history (messages and tool outputs that were "
            "evicted or compacted out of the live context to save space). Use this to recover "
            "details from earlier in the conversation. Results are capped, so narrow your search "
            "with a query string and/or an iteration range."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Case-insensitive substring to search for in archived message contents.",
                },
                "start_iter": {
                    "type": "integer",
                    "description": "Only include archived messages from this iteration onward (1-based).",
                },
                "end_iter": {
                    "type": "integer",
                    "description": "Only include archived messages up to this iteration (1-based).",
                },
            },
            "required": [],
        },
    }
}

handler = lambda args: read_history(
    query=args.get("query", ""),
    start_iter=args.get("start_iter", 0),
    end_iter=args.get("end_iter", 0),
)
