# Jarvis

An always-on English voice assistant for macOS. Say **"Hey Jarvis"** (or hold
**Right Option**), ask a question or give a task, and Jarvis answers out loud.

The thinking is done by [Claude Code](https://claude.com/claude-code) running
headless (`claude -p`), so Jarvis can look things up, read files, check
websites and use your Claude connectors (Gmail, Google Calendar).

## Safety

- Read-only tools (reading files, web search, checking a website, reading
  email) run without asking.
- Anything that changes something (writing files, running commands, sending
  email, adding events) goes through Claude Code's `--permission-prompt-tool`:
  Jarvis asks *"…Should I?"* and only proceeds if you answer **yes** within
  10 seconds. Silence, "no", or anything hedged ("not yet", "sure, wait") is a
  no.

## Privacy

Wake-word detection, voice-activity detection and speech-to-text all run on
your Mac. Only the transcribed text is sent to Claude. Logs (text only) are
kept in `logs/` for 7 days.

## How it works

| Part | Module | Uses |
|---|---|---|
| Wake word | `jarvis/wakeword.py` | openWakeWord `hey_jarvis` |
| End of speech | `jarvis/endpointer.py`, `jarvis/vad.py` | Silero VAD |
| Speech to text | `jarvis/stt.py` | whisper.cpp (`whisper-cli`, `ggml-base.en.bin`) |
| Brain | `jarvis/brain.py` | `claude -p` with session resume |
| Yes/no gate | `jarvis/confirm.py`, `jarvis/confirm_server.py` | MCP server |
| Voice | `jarvis/tts.py` | macOS `say` |
| Hotkey | `jarvis/hotkey.py` | AppKit global event monitor |
| Menu bar | `jarvis/app.py` | rumps |

## Setup

Requires macOS, Python 3.11, and a logged-in Claude Code CLI.

```bash
git clone https://github.com/Atomphat/jarvis ~/jarvis && cd ~/jarvis
python3.11 -m venv .venv
.venv/bin/pip install -r requirements.lock

# whisper.cpp
.venv/bin/pip install cmake
git clone --depth 1 --branch v1.9.5 https://github.com/ggml-org/whisper.cpp .tools/whisper.cpp
(cd .tools/whisper.cpp && ../../.venv/bin/cmake -B build -DCMAKE_BUILD_TYPE=Release \
  && ../../.venv/bin/cmake --build build -j 4 --target whisper-cli)
mkdir -p ~/.local/bin && ln -sf "$PWD/.tools/whisper.cpp/build/bin/whisper-cli" ~/.local/bin/whisper-cli

# models
mkdir -p models
curl -L -o models/ggml-base.en.bin https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.en.bin
.venv/bin/python -c "import openwakeword.utils as u; u.download_models(model_names=['hey_jarvis'])"

# run once from the terminal, or install as a login item
.venv/bin/python -m jarvis.app
scripts/install-app.sh
```

macOS will ask for **Microphone** access, and the hotkey needs **Accessibility**
(System Settings → Privacy & Security). The voice is set in `jarvis/config.py`.

## Tests

```bash
.venv/bin/pytest              # everything
.venv/bin/pytest -m "not integration"   # skip tests that need models / say
```
