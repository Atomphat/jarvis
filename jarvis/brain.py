from __future__ import annotations

import json
import logging
import re
import subprocess
import time
from typing import Callable

from jarvis.config import Config

log = logging.getLogger(__name__)

DIDNT_CATCH = "Sorry, I didn't catch that."
SOMETHING_WRONG = "Sorry, something went wrong."
NO_INTERNET = "I can't reach the internet right now."
TOO_LONG = "Sorry, that took too long, so I stopped."
STILL_WORKING = "Still working on it."

_NETWORK_WORDS = ("enotfound", "econnrefused", "econnreset", "getaddrinfo", "fetch failed",
                  "network", "offline", "etimedout")
_RESET = re.compile(r"resets?\s+(?:at\s+)?([^.\n]+)", re.IGNORECASE)


def friendly_error(message: str) -> str:
    message = message.strip()[:300]  # the cause is up front; long tail lists are noise
    low = message.lower()
    if "limit" in low:
        m = _RESET.search(message)
        suffix = f" It resets at {m.group(1).strip()}." if m else ""
        return "I've hit your Claude usage limit." + suffix
    if any(w in low for w in _NETWORK_WORDS):
        return NO_INTERNET
    return SOMETHING_WRONG


class Brain:
    def __init__(self, claude_bin: str, cfg: Config, cwd: str, clock: Callable[[], float] = time.time):
        self.claude_bin = claude_bin
        self.cfg = cfg
        self.cwd = cwd
        self.clock = clock

    # --- session -------------------------------------------------------
    def _load_session(self) -> str | None:
        try:
            data = json.loads(self.cfg.state_path.read_text())
        except (OSError, ValueError):
            return None
        if self.clock() - float(data.get("last_used", 0)) > self.cfg.session_ttl_s:
            return None
        return data.get("session_id")

    def _save_session(self, session_id: str) -> None:
        self.cfg.state_path.write_text(json.dumps({"session_id": session_id, "last_used": self.clock()}))

    def new_conversation(self) -> None:
        self.cfg.state_path.unlink(missing_ok=True)

    # --- calling claude ------------------------------------------------
    def build_args(self, text: str, session_id: str | None) -> list[str]:
        args = [self.claude_bin, "-p", text, "--output-format", "json",
                "--model", self.cfg.claude_model,
                "--permission-mode", "default",
                "--append-system-prompt", self.cfg.system_prompt,
                "--mcp-config", str(self.cfg.mcp_config_path),
                "--settings", str(self.cfg.claude_settings_path),
                "--permission-prompt-tool", "mcp__jarvis_confirm__approve"]
        if session_id:
            args += ["--resume", session_id]
        args += ["--allowedTools", *self.cfg.allowed_tools]
        return args

    def ask(self, text: str, on_slow: Callable[[], None] | None = None) -> str:
        session_id = self._load_session()
        reply, stale = self._run(text, session_id, on_slow)
        if stale:
            log.info("stored session %s unknown to claude; starting fresh", session_id)
            self.new_conversation()
            reply, _ = self._run(text, None, on_slow)
        return reply

    def _run(self, text: str, session_id: str | None, on_slow) -> tuple[str, bool]:
        try:
            proc = subprocess.Popen(self.build_args(text, session_id), cwd=self.cwd,
                                    stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE, text=True)
        except OSError:
            log.exception("could not start claude")
            return SOMETHING_WRONG, False
        try:
            out, err = proc.communicate(timeout=self.cfg.claude_timeout_s)
        except subprocess.TimeoutExpired:
            if on_slow:
                on_slow()
            try:
                out, err = proc.communicate(timeout=self.cfg.claude_extra_wait_s)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.communicate()
                log.warning("claude timed out")
                return TOO_LONG, False
        return self._interpret(out, err, session_id)

    def _interpret(self, out: str, err: str, session_id: str | None) -> tuple[str, bool]:
        try:
            data = json.loads(out)
        except ValueError:
            data = None
        if isinstance(data, dict):
            result = (data.get("result") or "").strip()
            if session_id and data.get("is_error") and "no conversation found" in result.lower():
                return "", True
            if data.get("session_id"):
                self._save_session(data["session_id"])
            if not data.get("is_error") and result:
                return result, False
            log.warning("claude error: %s | %s", result, err.strip()[-500:])
            return friendly_error(f"{result} {err}"), False
        log.warning("claude bad output: %s | %s", out.strip()[-300:], err.strip()[-500:])
        return friendly_error(f"{err} {out}"), False
