import json
import os
import stat
import sys

import pytest

from jarvis.brain import NO_INTERNET, SOMETHING_WRONG, TOO_LONG, Brain, friendly_error
from jarvis.config import Config

STUB = '''#!{python}
import json, os, sys, time
with open(os.environ["STUB_ARGS"], "a") as f:
    f.write(json.dumps(sys.argv[1:]) + "\\n")
mode = os.environ.get("STUB_MODE", "ok")
def ok(sid="sess-1", text="Tokyo is the capital of Japan."):
    print(json.dumps({{"type": "result", "is_error": False, "result": text, "session_id": sid}}))
if mode == "ok":
    ok()
elif mode == "sleep":
    time.sleep(float(os.environ["STUB_SLEEP"]))
    ok()
elif mode == "limit":
    print(json.dumps({{"type": "result", "is_error": True, "result": "Claude usage limit reached. Your limit resets at 5pm.", "session_id": "sess-1"}}))
elif mode == "offline":
    sys.stderr.write("Error: getaddrinfo ENOTFOUND api.anthropic.com")
    sys.exit(1)
elif mode == "stdin":
    same = os.path.samestat(os.fstat(0), os.stat("/dev/null"))
    ok(text="devnull" if same else "inherited")
elif mode == "stale":
    if "--resume" in sys.argv:
        print(json.dumps({{"type": "result", "is_error": True, "result": "No conversation found with session ID: old"}}))
    else:
        ok(sid="sess-2")
'''


@pytest.fixture
def stub(tmp_path, monkeypatch):
    path = tmp_path / "claude"
    path.write_text(STUB.format(python=sys.executable))
    path.chmod(path.stat().st_mode | stat.S_IEXEC)
    args_file = tmp_path / "args.jsonl"
    monkeypatch.setenv("STUB_ARGS", str(args_file))

    def calls():
        if not args_file.exists():
            return []
        return [json.loads(l) for l in args_file.read_text().splitlines()]

    return str(path), calls


def make_brain(tmp_path, claude_bin, now=None, **overrides):
    now = now if now is not None else [1000.0]
    cfg = Config(root=tmp_path, **overrides)
    return Brain(claude_bin, cfg, cwd=str(tmp_path), clock=lambda: now[0])


def test_build_args_contains_safety_flags(tmp_path):
    b = make_brain(tmp_path, "claude")
    args = b.build_args("hello", None)
    assert args[:3] == ["claude", "-p", "hello"]
    assert "--resume" not in args
    i = args.index("--allowedTools")
    assert "Read" in args[i + 1 :]
    assert args[args.index("--permission-prompt-tool") + 1] == "mcp__jarvis_confirm__approve"
    assert args[args.index("--permission-mode") + 1] == "default"
    assert args[args.index("--model") + 1] == "sonnet"
    assert args[args.index("--settings") + 1].endswith("claude-settings.json")
    assert "--resume" in b.build_args("hi", "abc")


def test_ask_returns_result_and_resumes_session(tmp_path, stub):
    claude_bin, calls = stub
    b = make_brain(tmp_path, claude_bin)
    assert b.ask("capital of japan?") == "Tokyo is the capital of Japan."
    assert b.ask("and france?") == "Tokyo is the capital of Japan."
    first, second = calls()
    assert "--resume" not in first
    assert second[second.index("--resume") + 1] == "sess-1"


def test_session_expires_after_ttl(tmp_path, stub):
    claude_bin, calls = stub
    now = [1000.0]
    b = make_brain(tmp_path, claude_bin, now=now)
    b.ask("one")
    now[0] += 4 * 3600 + 1
    b.ask("two")
    assert "--resume" not in calls()[1]


def test_new_conversation_drops_session(tmp_path, stub):
    claude_bin, calls = stub
    b = make_brain(tmp_path, claude_bin)
    b.ask("one")
    b.new_conversation()
    b.ask("two")
    assert "--resume" not in calls()[1]


def test_stale_session_retries_fresh(tmp_path, stub, monkeypatch):
    claude_bin, calls = stub
    (tmp_path / "state.json").write_text(json.dumps({"session_id": "old", "last_used": 1000.0}))
    monkeypatch.setenv("STUB_MODE", "stale")
    b = make_brain(tmp_path, claude_bin)
    assert b.ask("hello") == "Tokyo is the capital of Japan."
    assert len(calls()) == 2
    assert json.loads((tmp_path / "state.json").read_text())["session_id"] == "sess-2"


def test_usage_limit_is_spoken(tmp_path, stub, monkeypatch):
    claude_bin, _ = stub
    monkeypatch.setenv("STUB_MODE", "limit")
    reply = make_brain(tmp_path, claude_bin).ask("hi")
    assert reply == "I've hit your Claude usage limit. It resets at 5pm."


def test_offline_is_spoken(tmp_path, stub, monkeypatch):
    claude_bin, _ = stub
    monkeypatch.setenv("STUB_MODE", "offline")
    assert make_brain(tmp_path, claude_bin).ask("hi") == NO_INTERNET


def test_missing_binary(tmp_path):
    assert make_brain(tmp_path, str(tmp_path / "nope")).ask("hi") == SOMETHING_WRONG


def test_slow_then_answers(tmp_path, stub, monkeypatch):
    claude_bin, _ = stub
    monkeypatch.setenv("STUB_MODE", "sleep")
    monkeypatch.setenv("STUB_SLEEP", "1.5")
    slow = []
    b = make_brain(tmp_path, claude_bin, claude_timeout_s=0.5, claude_extra_wait_s=5)
    assert b.ask("hi", on_slow=lambda: slow.append(1)) == "Tokyo is the capital of Japan."
    assert slow == [1]


def test_gives_up_after_extra_wait(tmp_path, stub, monkeypatch):
    claude_bin, _ = stub
    monkeypatch.setenv("STUB_MODE", "sleep")
    monkeypatch.setenv("STUB_SLEEP", "10")
    b = make_brain(tmp_path, claude_bin, claude_timeout_s=0.3, claude_extra_wait_s=0.3)
    assert b.ask("hi", on_slow=lambda: None) == TOO_LONG


def test_friendly_error_generic():
    assert friendly_error("segfault") == SOMETHING_WRONG


def test_claude_gets_closed_stdin(tmp_path, stub, monkeypatch):
    # claude -p waits 3 s for piped stdin; Jarvis must hand it /dev/null.
    claude_bin, _ = stub
    monkeypatch.setenv("STUB_MODE", "stdin")
    r, w = os.pipe()
    saved = os.dup(0)
    os.dup2(r, 0)
    try:
        reply = make_brain(tmp_path, claude_bin).ask("hi")
    finally:
        os.dup2(saved, 0)
        for fd in (r, w, saved):
            os.close(fd)
    assert reply == "devnull"


def test_friendly_error_ignores_words_inside_long_tool_lists():
    message = "Error: MCP tool x not found. Available MCP tools: " + ", ".join(
        f"mcp__claude_ai_Vercel__tool_{i}" for i in range(40)
    ) + ", mcp__claude_ai_Vercel__update_session_network_policy, mcp__x__get_rate_limit"
    assert friendly_error(message) == SOMETHING_WRONG
