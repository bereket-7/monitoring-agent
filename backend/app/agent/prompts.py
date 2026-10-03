"""Load versioned agent prompts from the /prompts directory."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

_PROMPTS_ROOT = Path(__file__).resolve().parents[3] / "prompts"


@lru_cache(maxsize=16)
def load_prompt(name: str) -> str:
    """Load a prompt file by stem name (e.g. 'system')."""
    path = _PROMPTS_ROOT / f"{name}.md"
    if not path.is_file():
        raise FileNotFoundError(f"Prompt file not found: {path}")
    return path.read_text(encoding="utf-8").strip()


def system_prompt() -> str:
    return load_prompt("system")


def investigation_prompt() -> str:
    return load_prompt("investigation")


def recommendation_prompt() -> str:
    return load_prompt("recommendation")


def build_system_messages() -> list[dict[str, str]]:
    """Assemble system/developer instructions for the LLM."""
    return [
        {"role": "system", "content": system_prompt()},
        {"role": "system", "content": investigation_prompt()},
        {"role": "system", "content": recommendation_prompt()},
    ]
