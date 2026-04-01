import subprocess

MAX_LEN = 50000
MAX_CONSOLE_OUTPUT = 200
DEBUG_PRINT = True


def run_bash(command: str) -> str:
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=120)
        out = (result.stdout + result.stderr).strip()[:MAX_LEN]
        if DEBUG_PRINT:
            print(f"Command: {command}")
            print(f"Output: {out[:MAX_CONSOLE_OUTPUT]}")
        return out
    except Exception as e:
        print(f"Error occurred while running command: {e}")
        return f"Error occurred: {e}"


schema = {
    "type": "function",
    "function": {
        "name": "run_bash",
        "description": "Executes a bash command and returns the output (stdout + stderr). Maximum output length is limited to avoid excessive data.",
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
