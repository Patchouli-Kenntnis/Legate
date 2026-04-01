DEBUG_PRINT = True

_subagent_counter = 1


def create_subagent(user_prompt: str) -> str:
    global _subagent_counter

    # Deferred to avoid circular import: tools/__init__.py → create_subagent → agent → tools
    from tools import SUBAGENT_TOOLS, SUBAGENT_TOOL_HANDLERS
    from agent import subagent_loop, MAX_AGENT_ITERATIONS

    _subagent_counter += 1
    subagent_id = _subagent_counter

    if DEBUG_PRINT:
        print(f"[create_subagent] Spawning subagent {subagent_id} with prompt: {user_prompt!r}")

    try:
        result = subagent_loop(subagent_id, user_prompt, MAX_AGENT_ITERATIONS, SUBAGENT_TOOLS, SUBAGENT_TOOL_HANDLERS)
        if DEBUG_PRINT:
            print(f"[create_subagent] Subagent {subagent_id} finished.")
        return f"Subagent {subagent_id} result:\n{result}"
    except Exception as e:
        print(f"[create_subagent] Error in subagent {subagent_id}: {e}")
        return f"Subagent {subagent_id} failed with error: {e}"


schema = {
    "type": "function",
    "function": {
        "name": "create_subagent",
        "description": (
            "Spawns a subagent that runs its own independent agent loop to handle a delegated task in its own isolated context. "
            "The subagent has access to all tools other than creating its own subagents, including internet search, file I/O, and bash execution. Always provide clear and concise instructions when creating a subagent, and keep track of their results to integrate back into your overall plan. "
            "Use this to parallelize work, delegate complex subtasks, or isolate concerns. "
            "Returns the subagent's final response when it finishes."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "user_prompt": {
                    "type": "string",
                    "description": "The task or instruction to give the subagent",
                },
            },
            "required": ["user_prompt"],
        },
    }
}

handler = lambda args: create_subagent(args["user_prompt"])
