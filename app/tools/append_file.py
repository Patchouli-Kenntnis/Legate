import os

DEBUG_PRINT = True


def append_file(path: str, content: str) -> str:
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True) if os.path.dirname(path) else None
        with open(path, "a", encoding="utf-8") as f:
            f.write(content)
        if DEBUG_PRINT:
            print(f"Appended to file: {path}")
        return f"Successfully appended {len(content)} characters to {path}"
    except Exception as e:
        print(f"Error appending to file: {e}")
        return f"Error occurred: {e}"


schema = {
    "type": "function",
    "function": {
        "name": "append_file",
        "description": "Appends text content to a file at the given path, creating the file (and any missing parent directories) if it does not exist.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The absolute or relative path to the file to append to, e.g. 'logs/output.txt'",
                },
                "content": {
                    "type": "string",
                    "description": "The text content to append to the file",
                },
            },
            "required": ["path", "content"],
        },
    }
}

handler = lambda args: append_file(args["path"], args["content"])
