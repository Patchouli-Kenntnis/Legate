import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from settings import get_settings

MAX_CONSOLE_OUTPUT = 200
DEBUG_PRINT = True


def read_file(path: str) -> str:
    try:
        spill_threshold = get_settings().spill_threshold
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        if DEBUG_PRINT:
            print(f"Read file: {path}")
            print(f"Content: {content[:MAX_CONSOLE_OUTPUT]}")
        if len(content) > spill_threshold:
            head = content[: max(spill_threshold - 2_000, 1_000)]
            tail = content[-2_000:]
            return (
                f"{head}\n...\n{tail}\n"
                f"[truncated — file is {len(content)} characters; full content is on disk at {path}; "
                f"read specific ranges or grep via run_bash]"
            )
        return content
    except Exception as e:
        print(f"Error reading file: {e}")
        return f"Error occurred: {e}"


schema = {
    "type": "function",
    "function": {
        "name": "read_file",
        "description": (
            "Reads the text content of a file at the given path and returns it as a string. "
            "Very large files are returned as a head/tail preview with a truncation notice; "
            "use run_bash (e.g. sed/grep) to read specific ranges of large files."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The absolute or relative path to the file to read, e.g. '/etc/hosts' or 'src/main.py'",
                },
            },
            "required": ["path"],
        },
    }
}

handler = lambda args: read_file(args["path"])
