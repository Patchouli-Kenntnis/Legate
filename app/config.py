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
DEFAULT_TOKEN_BUDGET = 150_000
VERBOSE = 1

# --- Context compression ---
MAX_OUTPUT_TOKENS = 16_000   # reserved for the model's reply when sizing the context
COMPACT_BUFFER = 12_000      # safety margin below the hard window edge
COMPACT_HARD_CAP = 120_000   # never let the live context grow past this many tokens
KEEP_RECENT_BLOCKS = 3       # iteration blocks kept verbatim during eviction/compaction
SPILL_THRESHOLD = 16_000     # chars; tool outputs above this are spilled to disk
NOTES_MIN_CHARS = 400        # min accumulated notes size to skip the LLM summary call
