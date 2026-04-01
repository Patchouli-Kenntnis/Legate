from dotenv import load_dotenv
import os
import json
from openai import OpenAI

MAX_AGENT_ITERATIONS = 32
VERBOSE = 1

load_dotenv()
openai_key = os.getenv("OPENAI_KEY")

client = OpenAI(api_key=openai_key)
GPT_MODEL = "gpt-5.4-pro"



sub_prompt = '''
You're a helper that can execute a series of tasks to accomplish the primary agent's request. You have access to a set of tools that you can use to interact with the system and manage your tasks. Always think step by step and use the tools at your disposal to complete the tasks efficiently.

Prioritize using read_file and write_file and append_file for file operations, use web_search to search for information on the internet if prompted, and only use run_bash for everything else. Always use the provided functions to interact with the system, and do not assume any prior knowledge about the file system or environment. If you need to check if a file exists, read its content, or write to a file, use the appropriate function. For any other operations, use run_bash. Always provide clear and concise commands or file paths when using the functions. 
'''

def subagent_loop(subagent_id: int, user_prompt: str, max_iter: int, tools: list, tool_handlers: dict):
    
    messages = [
        {"role": "system", "content": sub_prompt},
        {"role": "user", "content": user_prompt}
    ]

    for i in range(max_iter):
        if VERBOSE >= 1:
            print(f"> Subagent {subagent_id} Iteration {i+1}")
        response = client.chat.completions.create(
            model=GPT_MODEL,
            messages=messages,
            tools=tools,
        )

        message = response.choices[0].message
        if VERBOSE >= 2:
            print(f"Model response: {message.content}")
        messages.append(message)

        if not message.tool_calls:
            if VERBOSE >= 1:
                print("No tool calls found in the response. Ending loop.")
            return message.content or ""

        for tool_call in message.tool_calls:
            handler = tool_handlers.get(tool_call.function.name)
            if handler:
                args = json.loads(tool_call.function.arguments)
                tool_output = handler(args)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": tool_output,
                })

    if VERBOSE >= 1:
        print("Subagent reached max iterations without a final response.")
    return "Subagent reached max iterations without a final response."

