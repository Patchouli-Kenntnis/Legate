"""User-adjustable runtime settings, persisted to settings.json at the project root.

Values of -1 mean "unlimited" where noted. Settings act as defaults for new
conversations and as live knobs for the compression cascade; config.py keeps
the built-in fallback values.
"""

import os

from pydantic import BaseModel

from config import (
    COMPACT_HARD_CAP, DEFAULT_TOKEN_BUDGET, KEEP_RECENT_BLOCKS,
    MAX_AGENT_ITERATIONS, SPILL_THRESHOLD,
)

SETTINGS_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "settings.json"
)


class Settings(BaseModel):
    max_token_budget: int = DEFAULT_TOKEN_BUDGET   # -1 = unlimited
    max_context_tokens: int = COMPACT_HARD_CAP     # -1 = no hard cap (window-based limit only)
    max_iterations: int = MAX_AGENT_ITERATIONS     # -1 = unlimited
    keep_recent_blocks: int = KEEP_RECENT_BLOCKS   # must be >= 1
    spill_threshold: int = SPILL_THRESHOLD         # chars; must be >= 1000


def fmt_limit(value: int) -> str:
    """Human-readable rendering of a limit value (-1 = unlimited)."""
    return "unlimited" if value < 0 else str(value)


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = _load()
    return _settings


def _load() -> Settings:
    if os.path.isfile(SETTINGS_PATH):
        try:
            with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
                return Settings.model_validate_json(f.read())
        except Exception as e:
            print(f"Warning: invalid settings file, using defaults: {e}")
    return Settings()


def save_settings() -> None:
    with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
        f.write(get_settings().model_dump_json(indent=2))
