MAX_CONSOLE_OUTPUT = 200
DEBUG_PRINT = True


def read_file(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        if DEBUG_PRINT:
            print(f"Read file: {path}")
            print(f"Content: {content[:MAX_CONSOLE_OUTPUT]}")
        return content
    except Exception as e:
        print(f"Error reading file: {e}")
        return f"Error occurred: {e}"


schema = {
    "type": "function",
    "function": {
        "name": "read_file",
        "description": "Reads the full text content of a file at the given path and returns it as a string.",
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
