import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from planner import planner as Planner

DEBUG_PRINT = True

_planner_instance = Planner()


def get_planner_instance():
    """Return the shared planner singleton for save/restore."""
    return _planner_instance


def set_planner_state(data: list) -> None:
    """Restore the planner singleton's todolist from serialized data."""
    _planner_instance.from_list(data)


def set_planner_notes(notes: list) -> None:
    """Restore the planner singleton's notes from serialized data."""
    _planner_instance.notes = list(notes)


def reset_planner() -> None:
    """Clear the planner singleton for a fresh conversation."""
    _planner_instance.todolist = []
    _planner_instance.notes = []


def update_planner(action: str, steps_text: str = "", step_index: int = -1, new_status: int = 0, note_text: str = "") -> str:
    """
    Interact with the shared planner instance.

    Actions:
      - "add_steps":    Parse and append steps from a numbered list string.
      - "update_state": Set the status of a step by its 1-based index.
      - "get_state":    Return the current plan as a formatted string.
    """
    if action == "add_steps":
        if not steps_text:
            return "Error: 'steps_text' is required for action 'add_steps'."
        _planner_instance.add_steps(steps_text)
        if DEBUG_PRINT:
            print(f"[update_planner] Added steps:\n{steps_text}")
        return f"Steps added. Current plan:\n{_planner_instance.stringify()}"

    elif action == "update_state":
        if step_index < 1:
            return "Error: 'step_index' must be a 1-based integer >= 1 for action 'update_state'."
        if new_status not in (0, 1, -1):
            return "Error: 'new_status' must be 0 (incomplete), 1 (complete), or -1 (failed)."
        zero_based = step_index - 1
        if zero_based >= len(_planner_instance.todolist):
            return f"Error: step_index {step_index} is out of range. Plan has {len(_planner_instance.todolist)} steps."
        _planner_instance.update_state(zero_based, new_status)
        status_label = {0: "incomplete", 1: "complete", -1: "failed"}[new_status]
        if DEBUG_PRINT:
            print(f"[update_planner] Step {step_index} marked {status_label}.")
        return f"Step {step_index} marked {status_label}. Current plan:\n{_planner_instance.stringify()}"

    elif action == "add_note":
        if not note_text:
            return "Error: 'note_text' is required for action 'add_note'."
        _planner_instance.add_note(note_text)
        if DEBUG_PRINT:
            print(f"[update_planner] Added note: {note_text[:120]}")
        return f"Note recorded ({len(_planner_instance.notes)} total)."

    elif action == "get_state":
        state = _planner_instance.stringify()
        notes = _planner_instance.notes_text()
        if notes:
            state = f"{state}\n\nNotes:\n{notes}" if state else f"Notes:\n{notes}"
        if DEBUG_PRINT:
            print(f"[update_planner] Retrieved state.")
        return state if state else "The plan is currently empty."

    else:
        return f"Error: Unknown action '{action}'. Valid actions are 'add_steps', 'update_state', 'add_note', 'get_state'."


schema = {
    "type": "function",
    "function": {
        "name": "update_planner",
        "description": (
            "Manages the agent's shared planner instance. Use 'add_steps' to populate the plan "
            "with a numbered list of steps, 'update_state' to mark a step as complete, incomplete, "
            "or failed, 'add_note' to record an important finding or decision (notes survive "
            "context compaction), and 'get_state' to retrieve the current plan and notes."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["add_steps", "update_state", "add_note", "get_state"],
                    "description": (
                        "'add_steps': append steps from a numbered-list string. "
                        "'update_state': change the status of a specific step. "
                        "'add_note': record a key finding or decision that should survive compaction. "
                        "'get_state': return the full current plan and notes."
                    ),
                },
                "steps_text": {
                    "type": "string",
                    "description": (
                        "Required for 'add_steps'. A newline-separated numbered list, "
                        "e.g. '1. Fetch data\\n2. Parse results\\n3. Write report'."
                    ),
                },
                "step_index": {
                    "type": "integer",
                    "description": (
                        "Required for 'update_state'. The 1-based index of the step to update."
                    ),
                },
                "new_status": {
                    "type": "integer",
                    "enum": [0, 1, -1],
                    "description": (
                        "Required for 'update_state'. "
                        "0 = incomplete, 1 = complete, -1 = failed."
                    ),
                },
                "note_text": {
                    "type": "string",
                    "description": (
                        "Required for 'add_note'. A concise statement of a key finding, decision, "
                        "or result worth preserving across context compaction."
                    ),
                },
            },
            "required": ["action"],
        },
    },
}

handler = lambda args: update_planner(
    action=args["action"],
    steps_text=args.get("steps_text", ""),
    step_index=args.get("step_index", -1),
    new_status=args.get("new_status", 0),
    note_text=args.get("note_text", ""),
)
