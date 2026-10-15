"""Config load/save: env > ~/.config/du/config.toml > defaults."""
from __future__ import annotations
import os
import tomllib
from pathlib import Path

DEFAULT_BASE_URL = "https://du-api.dev.umuganda.digital"
CONFIG_PATH = Path.home() / ".config" / "du" / "config.toml"

def _read_file(path: Path) -> dict[str, str]:
    try:
        with path.open("rb") as fh:
            data = tomllib.load(fh)
    except (FileNotFoundError, tomllib.TOMLDecodeError, OSError):
        return {}
    out: dict[str, str] = {}
    if isinstance(data.get("base_url"), str):
        out["base_url"] = data["base_url"]
    if isinstance(data.get("api_key"), str):
        out["api_key"] = data["api_key"]
    return out

def load_config(base_url_override: str | None = None, api_key_override: str | None = None) -> dict[str, str]:
    filed = _read_file(CONFIG_PATH)
    base = base_url_override if base_url_override is not None else os.environ.get("DU_BASE_URL", filed.get("base_url", DEFAULT_BASE_URL))
    key = api_key_override if api_key_override is not None else os.environ.get("DU_API_KEY", filed.get("api_key", ""))
    return {"base_url": base.rstrip("/"), "api_key": key}

def _q(v: str) -> str:
    return '"' + v.replace("\\", "\\\\").replace('"', '\\"') + '"'

def save_config(base_url: str | None, api_key: str | None) -> Path:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    prev = _read_file(CONFIG_PATH)
    if base_url is not None:
        prev["base_url"] = base_url.rstrip("/")
    if api_key is not None:
        prev["api_key"] = api_key
    lines = []
    if "base_url" in prev:
        lines.append(f"base_url = {_q(prev['base_url'])}")
    if "api_key" in prev:
        lines.append(f"api_key = {_q(prev['api_key'])}")
    text = "\n".join(lines) + ("\n" if lines else "")
    fd = os.open(CONFIG_PATH, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        with os.fdopen(fd, "w") as fh:
            fh.write(text)
    except OSError:
        pass
    try:
        os.chmod(CONFIG_PATH, 0o600)
    except OSError:
        pass
    return CONFIG_PATH

def clear_config() -> None:
    try:
        CONFIG_PATH.unlink()
    except FileNotFoundError:
        pass
