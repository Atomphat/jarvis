import pytest

from jarvis.confirm import decide, describe, is_yes


@pytest.mark.parametrize("text", ["Yes", "yes.", "Yeah, do it", "yep", "Sure", "Do it!", "go ahead please"])
def test_yes_variants_allow(text):
    assert is_yes(text)


@pytest.mark.parametrize("text", [
    "", "No", "nope", "no, don't", "Yeah, no", "not yet", "sure, wait", "yes, but cancel that",
    "maybe", "what?", "I said yes", "hmm yes", "yesterday", "surely not",
])
def test_everything_else_denies(text):
    assert not is_yes(text)


def test_describe_bash():
    assert describe("Bash", {"command": "rm -rf build"}) == "I'd like to run this command: rm -rf build. Should I?"


def test_describe_long_bash_is_truncated():
    text = describe("Bash", {"command": "echo " + "x" * 200})
    assert len(text) < 140 and text.endswith("Should I?")


def test_describe_file_change():
    assert describe("Write", {"file_path": "/Users/me/notes/todo.txt", "content": "x"}) == \
        "I'd like to change the file todo.txt. Should I?"


def test_describe_calendar_create_with_time():
    text = describe("mcp__claude_ai_Google_Calendar__create_event",
                    {"summary": "Dentist", "start": {"dateTime": "2026-10-17T14:00:00+07:00"}})
    assert text == "I'd like to add Dentist, on Saturday October 17 at 2:00 PM, to your calendar. Should I?"


def test_describe_send_email():
    text = describe("mcp__claude_ai_Gmail__send_message", {"to": "tom@example.com", "subject": "Lunch"})
    assert text == "I'd like to send an email to tom@example.com about Lunch. Should I?"


def test_describe_generic():
    assert describe("mcp__claude_ai_Gmail__trash_thread", {"id": "1"}) == \
        "I'd like to use trash thread. Should I?"


def test_decide_allow_passes_input_through():
    questions = []
    result = decide("Bash", {"command": "ls"}, ask=lambda q: questions.append(q) or "yes")
    assert result == {"behavior": "allow", "updatedInput": {"command": "ls"}}
    assert questions == ["I'd like to run this command: ls. Should I?"]


def test_decide_deny_on_silence():
    assert decide("Bash", {"command": "ls"}, ask=lambda q: "")["behavior"] == "deny"


def test_decide_deny_when_asking_fails():
    def boom(q):
        raise RuntimeError("mic broken")

    assert decide("Bash", {"command": "ls"}, ask=boom)["behavior"] == "deny"


def test_server_module_exposes_approve_tool():
    import jarvis.confirm_server as server

    assert callable(server.approve)
    assert server.mcp.name == "jarvis_confirm"


def test_server_returns_plain_permission_json(monkeypatch):
    # Claude Code reads the permission decision from the tool result; a structured
    # {"result": "..."} wrapper hides the "behavior" key from it.
    import asyncio
    import json

    import jarvis.confirm_server as server

    monkeypatch.setattr(server, "_ask_user", lambda q: "yes")
    res = asyncio.run(server.mcp.call_tool("approve", {"tool_name": "Write", "input": {"file_path": "/tmp/x"}}))
    assert not res.structured_content
    assert json.loads(res.content[0].text) == {"behavior": "allow", "updatedInput": {"file_path": "/tmp/x"}}
