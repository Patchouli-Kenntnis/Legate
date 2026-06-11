import os
import subprocess
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from settings import get_settings

MAX_CONSOLE_OUTPUT = 200
DEBUG_PRINT = True

SPILL_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "out"
)


def run_bash(command: str) -> str:
    try:
        spill_threshold = get_settings().spill_threshold
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=120)
        out = (result.stdout + result.stderr).strip()
        if DEBUG_PRINT:
            print(f"Command: {command}")
            print(f"Output: {out[:MAX_CONSOLE_OUTPUT]}")
        if len(out) > spill_threshold:
            os.makedirs(SPILL_DIR, exist_ok=True)
            spill_path = os.path.join(SPILL_DIR, f"tool_output_{uuid.uuid4().hex[:8]}.txt")
            with open(spill_path, "w", encoding="utf-8") as f:
                f.write(out)
            head = out[: max(spill_threshold - 2_000, 1_000)]
            tail = out[-2_000:]
            return (
                f"{head}\n...\n{tail}\n"
                f"[truncated — output is {len(out)} characters; full output saved to {spill_path}; "
                f"read specific ranges or grep it as needed]"
            )
        return out
    except Exception as e:
        print(f"Error occurred while running command: {e}")
        return f"Error occurred: {e}"


schema = {
    "type": "function",
    "function": {
        "name": "run_bash",
        "description": (
            "Executes a bash command and returns the output (stdout + stderr). "
            "Very large outputs are saved to a file on disk and returned as a head/tail preview "
            "with the file path, so you can grep or read specific ranges afterwards."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The bash command to execute, e.g. 'ls -la' or 'echo hello'",
                },
            },
            "required": ["command"],
        },
    }
}

handler = lambda args: run_bash(args["command"])
