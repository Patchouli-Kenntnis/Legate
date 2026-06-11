"""Offline checks for the context-compression cascade. Run: python3 tests/test_context.py"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app"))

from context import (
    EVICTION_MARKER, compact_messages, evict_old_tool_outputs, split_blocks,
    strip_state_messages,
)
from planner import planner as Planner
from persist import AgentState, ConversationData, ConversationManager, archive_path, append_archive


def make_block(n: int, tool_content: str = "tool output"):
    """One iteration block: assistant message with a tool call + its tool reply."""
    return [
        {
            "role": "assistant",
            "content": f"assistant turn {n}",
            "tool_calls": [{"id": f"call_{n}", "type": "function",
                            "function": {"name": "read_file", "arguments": "{}"}}],
        },
        {"role": "tool", "tool_call_id": f"call_{n}", "content": f"{tool_content} {n}"},
    ]


def make_messages(num_blocks: int):
    messages = [
        {"role": "system", "content": "system prompt"},
        {"role": "user", "content": "original task"},
    ]
    for n in range(num_blocks):
        messages.append({"role": "user", "content": f"[STATE] iteration={n}"})
        messages.extend(make_block(n))
    return messages


def test_split_blocks():
    messages = make_messages(4)
    head, blocks = split_blocks(messages)
    assert [m["role"] for m in head] == ["system", "user", "user"], "head should stop at first assistant"
    assert len(blocks) == 4
    for block in blocks:
        assert block[0]["role"] == "assistant"
        call_ids = {tc["id"] for tc in block[0].get("tool_calls", [])}
        tool_ids = {m["tool_call_id"] for m in block if m.get("role") == "tool"}
        assert call_ids == tool_ids, "tool replies must stay with their assistant tool_calls"
    flattened = list(head) + [m for b in blocks for m in b]
    assert flattened == messages, "split/join must preserve order and drop nothing"
    print("ok: split_blocks")


def test_strip_state_messages():
    messages = make_messages(4)
    stripped = strip_state_messages(messages)
    assert not any(str(m.get("content", "")).startswith("[STATE]") for m in stripped)
    assert len(messages) - len(stripped) == 4
    assert all(m in messages for m in stripped)
    print("ok: strip_state_messages")


def test_evict_old_tool_outputs():
    messages = make_messages(5)
    before_len = len(messages)
    archived = []
    evicted = evict_old_tool_outputs(messages, keep_blocks=2,
                                     archive_fn=lambda m, it: archived.append((it, m)))
    assert evicted == 3, f"expected 3 evictions, got {evicted}"
    assert len(messages) == before_len, "eviction must never drop messages"
    _, blocks = split_blocks(messages)
    for block in blocks[:-2]:
        for m in block:
            if m["role"] == "tool":
                assert m["content"] == EVICTION_MARKER
    for block in blocks[-2:]:
        for m in block:
            if m["role"] == "tool":
                assert m["content"] != EVICTION_MARKER, "recent blocks must stay verbatim"
    assert [m["content"] for _, m in archived] == ["tool output 0", "tool output 1", "tool output 2"]
    # idempotent: a second run archives/evicts nothing new
    assert evict_old_tool_outputs(messages, keep_blocks=2) == 0
    print("ok: evict_old_tool_outputs")


def test_compact_with_notes():
    messages = make_messages(6)
    p = Planner()
    p.add_steps("1. Step one\n2. Step two")
    p.add_note("decided to use JSONL for the archive " * 20)  # substantial notes -> no LLM call
    archived = []
    compacted = compact_messages(messages, client=None, planner=p,
                                 archive_fn=lambda m, it: archived.append(m), keep_blocks=2)
    assert compacted[0]["role"] == "system" and compacted[0]["content"] == "system prompt"
    assert compacted[1]["role"] == "user" and compacted[1]["content"].startswith("[COMPACTED HISTORY]")
    assert "Step one" in compacted[1]["content"], "plan must be embedded in the summary"
    assert "JSONL" in compacted[1]["content"], "notes must be embedded in the summary"
    _, blocks = split_blocks(compacted)
    assert len(blocks) == 2 and blocks[-1][0]["content"] == "assistant turn 5"
    assert any(m.get("content") == "original task" for m in archived), "non-system head must be archived"
    assert any(m.get("content") == "tool output 0" for m in archived)
    # nothing to do when few blocks
    short = make_messages(2)
    assert compact_messages(short, None, p, lambda m, it: None, keep_blocks=3) is short
    print("ok: compact_messages (notes path)")


def test_persist_roundtrip_and_archive():
    state = AgentState()
    conv = ConversationManager.new("roundtrip test", "gpt-5.4", state)
    conv.notes = ["note one", "note two"]
    ConversationManager.save(conv)
    append_archive(conv.id, {"iteration": 1, "role": "tool", "content": "archived output"})
    append_archive(conv.id, {"iteration": 2, "role": "assistant", "content": "later message"})
    try:
        loaded = ConversationManager.load(conv.id)
        assert loaded.notes == ["note one", "note two"]
        assert loaded.state.context_tokens == 0

        from tools.read_history import read_history, set_active_conversation
        set_active_conversation(conv.id)
        result = read_history(query="archived")
        assert "archived output" in result and "later message" not in result
        result = read_history(start_iter=2)
        assert "later message" in result and "archived output" not in result
    finally:
        ConversationManager.delete(conv.id)
    assert not os.path.exists(archive_path(conv.id)), "delete must remove the archive too"
    print("ok: persistence roundtrip + read_history")


def test_old_conversation_loads():
    # Simulate a pre-change saved file: no 'notes', no 'context_tokens'
    old_json = """{
        "id": "legacy-test", "title": "old", "model": "gpt-5.4",
        "created_at": "2026-01-01T00:00:00Z", "updated_at": "2026-01-01T00:00:00Z",
        "state": {"used_tokens": 5, "max_token_budget": 1000, "completed_iter": 1,
                  "max_iter": 32, "context_window": 1050000},
        "planner": [], "messages": []
    }"""
    conv = ConversationData.model_validate_json(old_json)
    assert conv.notes == [] and conv.state.context_tokens == 0
    print("ok: legacy conversation file loads")


def test_planner_notes_tool():
    from tools.update_planner import reset_planner, update_planner, get_planner_instance
    reset_planner()
    out = update_planner("add_note", note_text="found the bug in parser.py")
    assert "recorded" in out
    assert get_planner_instance().notes == ["found the bug in parser.py"]
    out = update_planner("get_state")
    assert "found the bug" in out
    assert "Error" in update_planner("add_note")  # missing note_text
    reset_planner()
    assert get_planner_instance().notes == []
    print("ok: planner add_note action")


def test_read_file_truncation():
    import tempfile
    from tools.read_file import read_file
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
        f.write("A" * 30_000)
        path = f.name
    try:
        result = read_file(path)
        assert len(result) < 30_000 and "[truncated" in result and path in result
    finally:
        os.unlink(path)
    print("ok: read_file truncation")


def test_settings():
    import settings as settings_mod
    from settings import Settings, fmt_limit

    assert fmt_limit(-1) == "unlimited" and fmt_limit(5000) == "5000"

    # Save/reload roundtrip through the singleton
    settings_mod._settings = Settings(max_token_budget=-1, max_context_tokens=9000)
    try:
        settings_mod.save_settings()
        settings_mod._settings = None
        s = settings_mod.get_settings()
        assert s.max_token_budget == -1 and s.max_context_tokens == 9000
    finally:
        os.unlink(settings_mod.SETTINGS_PATH)
        settings_mod._settings = None

    # Corrupt file falls back to defaults
    with open(settings_mod.SETTINGS_PATH, "w") as f:
        f.write("{not json")
    try:
        s = settings_mod.get_settings()
        assert s.max_token_budget == 150_000
    finally:
        os.unlink(settings_mod.SETTINGS_PATH)
        settings_mod._settings = None
    print("ok: settings persistence and fallback")


def test_effective_limit_settings():
    import settings as settings_mod
    from settings import Settings
    from agent import _effective_limit

    settings_mod._settings = Settings(max_context_tokens=50_000)
    assert _effective_limit(1_050_000) == 50_000, "hard cap should apply"
    settings_mod._settings = Settings(max_context_tokens=-1)
    assert _effective_limit(1_050_000) == 1_050_000 - 16_000 - 12_000, "-1 disables the hard cap"
    settings_mod._settings = None
    print("ok: effective limit honors settings")


def test_agent_imports():
    import agent  # smoke test: full wiring imports cleanly
    assert callable(agent.primary_agent_loop) and callable(agent.subagent_loop)
    print("ok: agent module imports")


if __name__ == "__main__":
    test_split_blocks()
    test_strip_state_messages()
    test_evict_old_tool_outputs()
    test_compact_with_notes()
    test_persist_roundtrip_and_archive()
    test_old_conversation_loads()
    test_planner_notes_tool()
    test_read_file_truncation()
    test_settings()
    test_effective_limit_settings()
    test_agent_imports()
    print("\nAll offline checks passed.")
