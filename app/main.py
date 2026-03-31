from dotenv import load_dotenv
import os

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

# test the model with a simple prompt
prompt = "explain quicksort"
inputs = processor(prompt, return_tensors="pt").to(model.device)
outputs = model.generate(**inputs, max_new_tokens=50000)
print(processor.batch_decode(outputs, skip_special_tokens=True)[0])

