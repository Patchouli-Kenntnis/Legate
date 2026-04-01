import os

DEBUG_PRINT = True


def write_file(path: str, content: str) -> str:
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True) if os.path.dirname(path) else None
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        if DEBUG_PRINT:
            print(f"Wrote file: {path}")
        return f"Successfully wrote {len(content)} characters to {path}"
    except Exception as e:
        print(f"Error writing file: {e}")
        return f"Error occurred: {e}"


schema = {
    "type": "function",
    "function": {
        "name": "write_file",
        "description": "Writes text content to a file at the given path, creating the file (and any missing parent directories) if it does not exist, or overwriting it if it does.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The absolute or relative path to the file to write, e.g. 'output/result.txt'",
                },
                "content": {
                    "type": "string",
                    "description": "The text content to write to the file",
                },
            },
            "required": ["path", "content"],
        },
    }
}

handler = lambda args: write_file(args["path"], args["content"])
