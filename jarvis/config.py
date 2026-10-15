from __future__ import annotations

import json
import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

EXTRA_PATHS = [
    str(Path.home() / ".local/bin"),
    "/usr/local/bin",
    "/opt/homebrew/bin",
    "/usr/bin",
    "/bin",
]

SYSTEM_PROMPT = (
    "You are Jarvis, the user's voice assistant on their Mac. "
    "Your reply is read aloud, so answer in one to three short spoken English sentences. "
    "Never use markdown, lists, tables, URLs or code. "
    "Say numbers, dates and times the way a person would say them. "
    "When a task needs a tool that changes something, just use it; "
    "the system asks the user for permission."
)

READ_ONLY_TOOLS = [
    "Read",
    "Grep",
    "Glob",
    "WebSearch",
    "WebFetch",
    "Bash(curl -sI *)",
    "Bash(curl -s -o /dev/null *)",
    "mcp__claude_ai_Gmail__search_threads",
    "mcp__claude_ai_Gmail__get_thread",
    "mcp__claude_ai_Gmail__get_message",
    "mcp__claude_ai_Gmail__list_labels",
]


def find_bin(name: str) -> str:
    search = os.pathsep.join([os.environ.get("PATH", ""), *EXTRA_PATHS])
    found = shutil.which(name, path=search)
    if not found:
        raise FileNotFoundError(f"{name} not found on PATH")
    return found


@dataclass
class Config:
    root: Path = ROOT
    sample_rate: int = 16000
    frame_samples: int = 1280  # 80 ms, what openWakeWord expects
    wake_threshold: float = 0.5
    rms_threshold: float = 500.0
    silence_ms: int = 1000
    max_record_ms: int = 30000
    no_speech_ms: int = 5000
    confirm_listen_ms: int = 10000
    voice: str = "Reed (English (US))"
    fallback_voice: str = "Fred"
    speech_rate: int = 185
    claude_model: str = "sonnet"
    claude_timeout_s: float = 120
    claude_extra_wait_s: float = 300
    session_ttl_s: float = 4 * 3600
    allowed_tools: list[str] = field(default_factory=lambda: list(READ_ONLY_TOOLS))
    system_prompt: str = SYSTEM_PROMPT

    @property
    def models_dir(self) -> Path:
        return self.root / "models"

    @property
    def whisper_model(self) -> Path:
        return self.models_dir / "ggml-base.en.bin"

    @property
    def logs_dir(self) -> Path:
        return self.root / "logs"

    @property
    def state_path(self) -> Path:
        return self.root / "state.json"

    @property
    def mcp_config_path(self) -> Path:
        return self.root / "mcp.json"

    @property
    def claude_settings_path(self) -> Path:
        return self.root / "claude-settings.json"


def write_runtime_files(cfg: Config, python_bin: str) -> None:
    mcp = {
        "mcpServers": {
            "jarvis_confirm": {
                "command": python_bin,
                "args": ["-m", "jarvis.confirm_server"],
                "env": {"PYTHONPATH": str(cfg.root)},
            }
        }
    }
    cfg.mcp_config_path.write_text(json.dumps(mcp, indent=2))
    settings = {
        "disableAllHooks": True,
        "enabledPlugins": {"superpowers@claude-plugins-official": False},
        "syncClaudeAiPlugins": False,  # claude.ai plugins add seconds of startup per call
        "language": "english",  # the user's own settings ask for Thai replies
    }
    cfg.claude_settings_path.write_text(json.dumps(settings, indent=2))
