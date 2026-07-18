"""Copilot settings — env-driven per §4.6 (provider/model per machine, keys
never committed). Reads the process environment, falling back to the repo-root
``.env`` (stdlib parser — the project deliberately avoids a dotenv dep)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

NIM_BASE_URL = "https://integrate.api.nvidia.com/v1"


def _read_env_file(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    out: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            out[key.strip()] = value.strip()
    return out


@dataclass(frozen=True)
class Settings:
    api_key: str = ""
    base_url: str = NIM_BASE_URL
    model: str = "nvidia/nemotron-3-super-120b-a12b"
    validator_model: str = "nvidia/nemotron-3-nano-30b-a3b"
    serving_path: str = "eval_outputs/serving.json"
    # Nemotron-3 reasons before tool calls (2026-07-18 ledger finding):
    # short budgets truncate the call at finish_reason=length
    max_tokens: int = 4096
    max_iterations: int = 8
    provider: str = field(default="nim")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    env = {**_read_env_file(Path(".env")), **os.environ}
    nvidia_key = env.get("NVIDIA_API_KEY", "")
    openai_key = env.get("OPENAI_API_KEY", "")
    if nvidia_key:  # preferred provider (2026-07-17 decision)
        api_key, base_url, provider = nvidia_key, NIM_BASE_URL, "nim"
    else:  # drop-in fallback per §4.6
        api_key, base_url, provider = openai_key, "https://api.openai.com/v1", "openai"
    # blank .env assignments mean "use the pinned default", not ""
    return Settings(
        api_key=api_key,
        base_url=env.get("COPILOT_BASE_URL") or base_url,
        model=env.get("COPILOT_MODEL") or Settings.model,
        validator_model=env.get("COPILOT_VALIDATOR_MODEL") or Settings.validator_model,
        serving_path=env.get("COPILOT_SERVING") or Settings.serving_path,
        max_tokens=int(env.get("COPILOT_MAX_TOKENS") or Settings.max_tokens),
        max_iterations=int(env.get("COPILOT_MAX_ITERATIONS") or Settings.max_iterations),
        provider=provider,
    )
