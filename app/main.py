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

def main_loop(prompt: str, max_iter: int = MAX_AGENT_ITERATIONS):
    messages = [
        {"role": "system", "content": "You are a helpful assistant that can execute bash commands using the run_bash function."},
        {"role": "user", "content": prompt},
    ]

    for i in range(max_iter):
        print(f"\n--- Iteration {i+1} ---")
        response = client.chat.completions.create(
            model=GPT_MODEL,
            messages=messages,
            tools=[run_bash_schema],
        )

        message = response.choices[0].message
        print(f"Model response: {message.content}")
        messages.append(message)

        if not message.tool_calls:
            print("No tool calls found in the response. Ending loop.")
            break

        for tool_call in message.tool_calls:
            if tool_call.function.name == "run_bash":
                args = json.loads(tool_call.function.arguments)
                command_output = run_bash(args["command"])
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": command_output,
                })
if __name__ == "__main__":
    prompt = "List the files in the current directory and then print 'Hello World'"
    while True:
        user_input = input("Enter your prompt: ")
        main_loop(user_input, MAX_AGENT_ITERATIONS)

