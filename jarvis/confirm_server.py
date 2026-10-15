from __future__ import annotations

import json

from mcp.server.mcpserver import MCPServer

from jarvis.audio import record_utterance
from jarvis.config import Config, find_bin
from jarvis.confirm import decide
from jarvis.endpointer import Endpointer
from jarvis.log import setup_logging
from jarvis.stt import Transcriber
from jarvis.tts import Speaker, chime
from jarvis.vad import SpeechDetector

cfg = Config()
mcp = MCPServer("jarvis_confirm")
_speaker: Speaker | None = None
_transcriber: Transcriber | None = None
_is_speech: SpeechDetector | None = None


def _ask_user(question: str) -> str:
    global _speaker, _transcriber, _is_speech
    if _speaker is None:
        _speaker = Speaker(cfg.voice, cfg.fallback_voice, cfg.speech_rate)
        _transcriber = Transcriber(find_bin("whisper-cli"), cfg.whisper_model)
        _is_speech = SpeechDetector()
    _speaker.speak(question, wait=True)
    chime("Tink")
    endpointer = Endpointer(
        rms_threshold=cfg.rms_threshold,
        silence_ms=cfg.silence_ms,
        max_ms=cfg.confirm_listen_ms,
        no_speech_ms=cfg.confirm_listen_ms,
        is_speech=_is_speech,
    )
    audio = record_utterance(endpointer, cfg.sample_rate, cfg.frame_samples)
    return _transcriber.transcribe(audio)


@mcp.tool(structured_output=False)
def approve(tool_name: str, input: dict, tool_use_id: str | None = None) -> str:
    """Ask the user out loud whether Jarvis may use this tool."""
    result = decide(tool_name, input, ask=_ask_user)
    if _speaker is not None:
        _speaker.speak("Okay." if result["behavior"] == "allow" else "Okay, I won't.", wait=True)
    return json.dumps(result)


if __name__ == "__main__":
    setup_logging("confirm", cfg.logs_dir)
    mcp.run()
