from __future__ import annotations

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Callable

log = logging.getLogger(__name__)

YES_PHRASES = ("yes", "yeah", "yep", "sure", "do it", "go ahead")
_NEGATION = re.compile(r"\b(no|nope|not|don't|dont|never|stop|cancel|wait)\b")
DENY = {"behavior": "deny", "message": "The user declined this action."}


def _normalize(text: str) -> str:
    return " ".join(re.sub(r"[^a-z' ]", " ", text.lower()).split())


def is_yes(text: str) -> bool:
    t = _normalize(text)
    if not t or _NEGATION.search(t):
        return False
    return any(t == p or t.startswith(p + " ") for p in YES_PHRASES)


def _short(text: str, limit: int = 80) -> str:
    text = " ".join(str(text).split())
    return text if len(text) <= limit else text[: limit - 3].rstrip() + "..."


def _spoken_time(value) -> str | None:
    if isinstance(value, dict):
        value = value.get("dateTime") or value.get("date")
    if not isinstance(value, str):
        return None
    try:
        dt = datetime.fromisoformat(value)
    except ValueError:
        return None
    day = f"{dt:%A %B} {dt.day}"
    if "T" not in value:
        return day
    hour = dt.hour % 12 or 12
    return f"{day} at {hour}:{dt:%M} {'AM' if dt.hour < 12 else 'PM'}"


def describe(tool_name: str, tool_input: dict) -> str:
    name = tool_name.lower()
    short_name = tool_name.split("__")[-1].lower()
    if name == "bash":
        return f"I'd like to run this command: {_short(tool_input.get('command', ''))}. Should I?"
    if name in ("write", "edit", "multiedit", "notebookedit"):
        file = Path(str(tool_input.get("file_path") or tool_input.get("notebook_path") or "a file")).name
        return f"I'd like to change the file {file}. Should I?"
    if "calendar" in name and any(v in short_name for v in ("create", "update", "delete")):
        verb = "add" if "create" in short_name else "change" if "update" in short_name else "delete"
        what = _short(tool_input.get("summary") or tool_input.get("title") or "an event", 60)
        when = _spoken_time(tool_input.get("start"))
        where = "to" if verb == "add" else "on"
        when_part = f", on {when}," if when else ""
        return f"I'd like to {verb} {what}{when_part} {where} your calendar. Should I?"
    if "gmail" in name and ("send" in short_name or "draft" in short_name):
        to = _short(tool_input.get("to") or "someone", 60)
        subject = _short(tool_input.get("subject") or "no subject", 60)
        action = "send an email" if "send" in short_name else "create an email draft"
        return f"I'd like to {action} to {to} about {subject}. Should I?"
    return f"I'd like to use {short_name.replace('_', ' ')}. Should I?"


def decide(tool_name: str, tool_input: dict, ask: Callable[[str], str]) -> dict:
    question = describe(tool_name, tool_input)
    try:
        answer = ask(question)
    except Exception:
        log.exception("asking the user failed")
        answer = ""
    allowed = is_yes(answer)
    log.info("confirm %s %r -> heard %r -> %s", tool_name, question, answer, "ALLOW" if allowed else "DENY")
    if allowed:
        return {"behavior": "allow", "updatedInput": tool_input}
    return dict(DENY)
