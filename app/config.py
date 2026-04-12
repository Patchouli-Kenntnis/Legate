"""Shared configuration: environment variables, model settings, agent limits."""

from dotenv import load_dotenv
import os

load_dotenv()

# --- OpenAI ---
OPENAI_KEY = os.getenv("OPENAI_KEY")

# --- Models ---
GPT_MODEL = "gpt-5.4"
GPT_MODEL_SUB = "gpt-5.4-pro"
GPT_MODEL_CONTEXT_WINDOW = {
    "gpt-5.4": 1_050_000,
    "gpt-5.4-pro": 1_050_000,
}

# --- Agent limits ---
MAX_AGENT_ITERATIONS = 32
VERBOSE = 1
