from __future__ import annotations

import logging
import sys
import threading
from pathlib import Path

import rumps

from jarvis.assistant import Assistant, State
from jarvis.audio import MicStream
from jarvis.brain import Brain
from jarvis.config import Config, find_bin, write_runtime_files
from jarvis.hotkey import RightOptionHotkey
from jarvis.log import setup_logging
from jarvis.stt import Transcriber
from jarvis.tts import Speaker, chime
from jarvis.vad import SpeechDetector
from jarvis.wakeword import WakeWordDetector

log = logging.getLogger("jarvis")

ICONS = {State.IDLE: "🟢", State.LISTENING: "🔴", State.THINKING: "🟡", State.SPEAKING: "🟡"}


class JarvisApp(rumps.App):
    def __init__(self, assistant: Assistant):
        super().__init__("Jarvis", title="🟢", quit_button=None)
        self.assistant = assistant
        self.error: str | None = None
        self._notified = False
        self.mute_item = rumps.MenuItem("Mute microphone", callback=self.on_mute)
        self.menu = [
            self.mute_item,
            rumps.MenuItem("New conversation", callback=self.on_new_conversation),
            None,
            rumps.MenuItem("Quit Jarvis", callback=self.on_quit),
        ]
        self.timer = rumps.Timer(self.refresh, 0.3)
        self.timer.start()

    def refresh(self, _) -> None:
        if self.error:
            self.title = "⚠️"
            if not self._notified:
                rumps.notification("Jarvis", "Microphone problem", self.error)
                self._notified = True
        elif self.assistant.muted:
            self.title = "⚪"
        else:
            self.title = ICONS[self.assistant.state]

    def on_mute(self, sender) -> None:
        sender.state = self.assistant.toggle_mute()

    def on_new_conversation(self, _) -> None:
        self.assistant.new_conversation()
        self.assistant.speaker.speak("Okay, starting a new conversation.", wait=False)

    def on_quit(self, _) -> None:
        rumps.quit_application()


def pump_microphone(cfg: Config, assistant: Assistant, app: JarvisApp) -> None:
    try:
        with MicStream(cfg.sample_rate, cfg.frame_samples) as mic:
            while True:
                frame = mic.read(timeout=1.0)
                if frame is not None:
                    assistant.on_frame(frame)
    except Exception as exc:
        log.exception("microphone stream failed")
        app.error = f"Jarvis can't use the microphone: {exc}"


def main() -> None:
    cfg = Config()
    setup_logging("jarvis", cfg.logs_dir)
    write_runtime_files(cfg, sys.executable)
    speaker = Speaker(cfg.voice, cfg.fallback_voice, cfg.speech_rate)
    if speaker.voice != cfg.voice:
        log.warning("voice %r not installed; using %r", cfg.voice, speaker.voice)
    assistant = Assistant(
        cfg,
        wake=WakeWordDetector(cfg.wake_threshold),
        transcriber=Transcriber(find_bin("whisper-cli"), cfg.whisper_model),
        brain=Brain(find_bin("claude"), cfg, cwd=str(Path.home())),
        speaker=speaker,
        chime=chime,
        is_speech=SpeechDetector(),
    )
    app = JarvisApp(assistant)
    hotkey = RightOptionHotkey(assistant.on_hotkey_down, assistant.on_hotkey_up)
    hotkey.start()
    threading.Thread(target=pump_microphone, args=(cfg, assistant, app), daemon=True).start()
    log.info("Jarvis started (voice %s)", speaker.voice)
    app.run()


if __name__ == "__main__":
    main()
