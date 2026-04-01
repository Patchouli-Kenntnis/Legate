from dotenv import load_dotenv
import os
import json
from openai import OpenAI
from tools import TOOLS, TOOL_HANDLERS

MAX_AGENT_ITERATIONS = 32

load_dotenv()
openai_key = os.getenv("OPENAI_KEY")

client = OpenAI(api_key=openai_key)
GPT_MODEL = "gpt-4o"

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

