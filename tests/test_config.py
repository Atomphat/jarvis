import json

import pytest

from jarvis.config import Config, find_bin, write_runtime_files


def test_find_bin_finds_say():
    assert find_bin("say").endswith("/say")


def test_find_bin_missing_raises():
    with pytest.raises(FileNotFoundError):
        find_bin("definitely-not-a-real-binary-xyz")


def test_config_paths(tmp_path):
    cfg = Config(root=tmp_path)
    assert cfg.whisper_model == tmp_path / "models" / "ggml-base.en.bin"
    assert cfg.state_path == tmp_path / "state.json"
    assert cfg.logs_dir == tmp_path / "logs"


def test_allowlist_is_read_only():
    cfg = Config()
    assert "Read" in cfg.allowed_tools
    assert "Bash" not in cfg.allowed_tools
    assert not any(t in cfg.allowed_tools for t in ("Write", "Edit"))


def test_write_runtime_files(tmp_path):
    cfg = Config(root=tmp_path)
    write_runtime_files(cfg, python_bin="/x/python")
    mcp = json.loads(cfg.mcp_config_path.read_text())
    server = mcp["mcpServers"]["jarvis_confirm"]
    assert server["command"] == "/x/python"
    assert server["args"] == ["-m", "jarvis.confirm_server"]
    assert server["env"]["PYTHONPATH"] == str(tmp_path)
    settings = json.loads(cfg.claude_settings_path.read_text())
    assert settings["disableAllHooks"] is True
    assert settings["enabledPlugins"]["superpowers@claude-plugins-official"] is False
    assert settings["syncClaudeAiPlugins"] is False
    assert settings["language"] == "english"
