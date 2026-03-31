from dotenv import load_dotenv
import os
import subprocess

MAX_LEN = 50000
MAX_CONSOLE_OUTPUT = 200
MAX_AGENT_ITERATIONS = 5
DEBUG_PRINT = True

# read huggingface token from .env file
load_dotenv()
huggingface_key = os.getenv("HF_KEY")

#login to huggingface hub using the token
from huggingface_hub import login
login(token=huggingface_key)

from transformers import AutoProcessor, AutoModelForCausalLM
GEMMA_MODEL_ID = "google/functiongemma-270m-it"

processor = AutoProcessor.from_pretrained(GEMMA_MODEL_ID, device_map="auto")
model = AutoModelForCausalLM.from_pretrained(GEMMA_MODEL_ID, dtype="auto", device_map="auto")

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
        # ESSENTIAL SYSTEM PROMPT:
        # This line activates the model's function calling logic.
        {"role": "developer", "content": "You are a model that can do function calling with the following functions"},
        {"role": "user", "content": prompt},
    ]
    
    for i in range(max_iter):
        print(f"\n--- Iteration {i+1} ---")
        inputs = processor.apply_chat_template(messages, tools=[run_bash_schema], add_generation_prompt=True, return_dict=True, return_tensors="pt")

        outputs = model.generate(**inputs.to(model.device), pad_token_id=processor.eos_token_id, max_new_tokens=MAX_LEN)
        response = processor.batch_decode(outputs, skip_special_tokens=True)[0]
        print(f"Model response: {response}")
        
        start_tag = "<start_function_call>"
        end_tag = "<end_function_call>"
        command_output = None

        if start_tag in response and end_tag in response:
            call_payload = response.split(start_tag, 1)[1].split(end_tag, 1)[0].strip()
            expected_prefix = "call:run_bash{"
            expected_suffix = "}"

            if call_payload.startswith(expected_prefix) and call_payload.endswith(expected_suffix):
                inner = call_payload[len(expected_prefix):-len(expected_suffix)]
                # format: command:<escape>...<escape>
                cmd_prefix = "command:<escape>"
                cmd_suffix = "<escape>"
                if inner.startswith(cmd_prefix) and inner.endswith(cmd_suffix):
                    command = inner[len(cmd_prefix):-len(cmd_suffix)]
                    command_output = run_bash(command)
                    messages.append({"role": "user", "content": f"Command output: {command_output}"})

        if command_output is None:
            print("No command found in the response. Ending loop.")
            break
if __name__ == "__main__":
    prompt = "List the files in the current directory and then print 'Hello World'"
    while True:
        user_input = input("Enter your prompt: ")
        main_loop(user_input, MAX_AGENT_ITERATIONS)

