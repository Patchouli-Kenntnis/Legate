from dotenv import load_dotenv
import os
import json
import tomllib
from openai import OpenAI
from tools import PRIMARY_TOOLS, PRIMARY_TOOL_HANDLERS

MAX_AGENT_ITERATIONS = 32

load_dotenv()
openai_key = os.getenv("OPENAI_KEY")

client = OpenAI(api_key=openai_key)
GPT_MODEL = "gpt-5.4"

# --- Load skills catalog at startup ---
SKILLS_CATALOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "skills", "SKILLS.toml")

def load_skills_catalog() -> str:
    """Read SKILLS.toml and return a formatted listing for the system prompt."""
    try:
        with open(SKILLS_CATALOG_PATH, "rb") as f:
            catalog = tomllib.load(f)
        entries = catalog.get("skills", [])
        if not entries:
            return "No skills available."
        lines = []
        for entry in entries:
            lines.append(f"- {entry['name']}: {entry['intro']}")
        return "\n".join(lines)
    except Exception as e:
        print(f"Warning: could not load skills catalog: {e}")
        return "Skills catalog unavailable."

skills_listing = load_skills_catalog()


sys_prompt = f'''
You're a coordinator that dispatch subagents to execute a series of tasks to accomplish a user's request. You have access to a set of tools that you can use to interact with the system and manage your tasks. Always think step by step and use the tools at your disposal to complete the tasks efficiently.

You have access to a shared planner instance that can hold a list of steps for you to complete. You can add steps to the planner, mark them as complete, or retrieve the current plan. Use the 'update_planner' function to interact with the planner. Always keep the planner updated with your current tasks and their statuses. 

Additionally, you can spawn subagents to handle delegated tasks in their own isolated contexts using the 'create_subagent' function. Use subagents to parallelize work, delegate complex subtasks, or isolate concerns. Always provide clear and concise instructions when creating a subagent, and keep track of their results to integrate back into your overall plan.

After getting result from subagents, always update the planner with the current status of your tasks.

## Skills

You and your subagents have access to a library of skills — predefined knowledge modules with domain-specific best practices. Before starting a task, review the available skills below and instruct your subagents to load any relevant ones using the 'read_skill' tool. When delegating to a subagent, mention which skills it should read first.

Available skills:
{skills_listing}
'''

def primary_agent_loop(user_prompt: str, max_iter: int = MAX_AGENT_ITERATIONS):
    
    messages = [
        {"role": "system", "content": sys_prompt},
        {"role": "user", "content": user_prompt}
    ]

    for i in range(max_iter):
        print(f"\n--- Iteration {i+1} ---")
        response = client.chat.completions.create(
            model=GPT_MODEL,
            messages=messages,
            tools=PRIMARY_TOOLS,
        )

        message = response.choices[0].message
        print(f"Model response: {message.content}")
        messages.append(message)

        if not message.tool_calls:
            print("No tool calls found in the response. Ending loop.")
            break

        for tool_call in message.tool_calls:
            handler = PRIMARY_TOOL_HANDLERS.get(tool_call.function.name)
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
        primary_agent_loop(user_input, MAX_AGENT_ITERATIONS)

