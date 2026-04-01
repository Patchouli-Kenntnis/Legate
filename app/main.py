from dotenv import load_dotenv
import os
import subprocess
import json
from openai import OpenAI

MAX_LEN = 50000
MAX_CONSOLE_OUTPUT = 200
MAX_AGENT_ITERATIONS = 5
DEBUG_PRINT = True

load_dotenv()
openai_key = os.getenv("OPENAI_KEY")

client = OpenAI(api_key=openai_key)
GPT_MODEL = "gpt-4o"

# an agent tool to run bash commands
def run_bash(command: str) -> str:
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=120)
        out = (result.stdout + result.stderr).strip()[:MAX_LEN]
        if DEBUG_PRINT:
            print(f"Command: {command}")
            print(f"Output: {out[:MAX_CONSOLE_OUTPUT]}")  # print only the first MAX_CONSOLE_OUTPUT characters
        return out
    
    except Exception as e:
        print(f"Error occurred while running command: {e}")
        return f"Error occurred: {e}"

# an agent tool to read a file
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

# an agent tool to write a file
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

run_bash_schema = {
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

read_file_schema = {
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

write_file_schema = {
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

TOOLS = [run_bash_schema, read_file_schema, write_file_schema]
TOOL_HANDLERS = {
    "run_bash": lambda args: run_bash(args["command"]),
    "read_file": lambda args: read_file(args["path"]),
    "write_file": lambda args: write_file(args["path"], args["content"]),
}

def main_loop(prompt: str, max_iter: int = MAX_AGENT_ITERATIONS):
    messages = [
        {"role": "system", "content": "You are a helpful assistant that can read files, and write files using the provided functions. For other tasks, you can run bash commands using the provided function. Prioritize using read_file and write_file for file operations, and use run_bash for everything else. Always use the provided functions to interact with the system, and do not assume any prior knowledge about the file system or environment. If you need to check if a file exists, read its content, or write to a file, use the appropriate function. For any other operations, use run_bash. Always provide clear and concise commands or file paths when using the functions."},
        {"role": "user", "content": prompt},
    ]

    for i in range(max_iter):
        print(f"\n--- Iteration {i+1} ---")
        response = client.chat.completions.create(
            model=GPT_MODEL,
            messages=messages,
            tools=TOOLS,
        )

        message = response.choices[0].message
        print(f"Model response: {message.content}")
        messages.append(message)

        if not message.tool_calls:
            print("No tool calls found in the response. Ending loop.")
            break

        for tool_call in message.tool_calls:
            handler = TOOL_HANDLERS.get(tool_call.function.name)
            if handler:
                args = json.loads(tool_call.function.arguments)
                tool_output = handler(args)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": tool_output,
                })
if __name__ == "__main__":
    while True:
        user_input = input("Enter your prompt: ")
        main_loop(user_input, MAX_AGENT_ITERATIONS)

