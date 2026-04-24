from __future__ import annotations

import json
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = PROJECT_ROOT / "config.json"

def load_config(path: str | Path = CONFIG_PATH) -> dict[str, Any]:
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file {config_path} does not exist.")

    with config_path.open("r", encoding="utf-8") as file:
        loaded = json.load(file)

    if not isinstance(loaded, dict):
        raise ValueError(f"Config file {config_path} must contain a JSON object.")

    return loaded


def build_known_command_tokens(commands: dict[str, Any]) -> tuple[str, ...]:
    tokens: list[str] = []

    for aliases in commands.values():
        if isinstance(aliases, str):
            aliases = [aliases]

        if not isinstance(aliases, list):
            continue

        for alias in aliases:
            if not isinstance(alias, str):
                continue

            token = alias.strip().split(maxsplit=1)[0]
            if not token:
                continue

            if not token.startswith("/"):
                token = f"/{token.lstrip('/')}"

            token = token.split("@", 1)[0]
            if token not in tokens:
                tokens.append(token)

    return tuple(tokens)
