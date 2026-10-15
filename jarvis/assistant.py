from __future__ import annotations

import enum
import logging
import re
import threading
import time
from typing import Callable

import numpy as np

from jarvis.brain import DIDNT_CATCH, SOMETHING_WRONG, STILL_WORKING
from jarvis.config import Config
from jarvis.endpointer import Endpointer

log = logging.getLogger(__name__)

_NEW_CONVERSATION = re.compile(r"\b(new conversation|start over)\b", re.IGNORECASE)


def is_new_conversation(text: str) -> bool:
    return bool(_NEW_CONVERSATION.search(text))


def _thread_spawn(fn, *args) -> None:
    threading.Thread(target=fn, args=args, daemon=True).start()


class State(enum.Enum):
    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    SPEAKING = "speaking"


class Assistant:
    def __init__(self, cfg: Config, wake, transcriber, brain, speaker,
                 chime: Callable[[str], None] = lambda name: None, spawn=None,
                 is_speech: Callable[[np.ndarray], bool] | None = None):
        self.cfg = cfg
        self.wake = wake
        self.transcriber = transcriber
        self.brain = brain
        self.speaker = speaker
        self.chime = chime
        self.spawn = spawn or _thread_spawn
        self.is_speech = is_speech
        self.state = State.IDLE
        self.muted = False
        self._endpointer: Endpointer | None = None
        self._push_to_talk = False
        self._lock = threading.RLock()

    # --- inputs ----------------------------------------------------------
    def on_frame(self, frame: np.ndarray) -> None:
        with self._lock:
            if self.muted:
                return
            if self.state == State.IDLE:
                if self.wake.process(frame):
                    log.info("wake word")
                    self._start_listening(push_to_talk=False)
            elif self.state == State.LISTENING and self._endpointer is not None:
                if self._endpointer.feed(frame):
                    self._finish_listening()

    def on_hotkey_down(self) -> None:
        with self._lock:
            if self.muted:
                return
            if self.state == State.IDLE:
                self._start_listening(push_to_talk=True)
            elif self.state == State.SPEAKING:
                self.speaker.stop()
            elif self.state == State.THINKING:
                self.chime("Funk")

    def on_hotkey_up(self) -> None:
        with self._lock:
            if self.state == State.LISTENING and self._push_to_talk and self._endpointer is not None:
                self._endpointer.finish()
                self._finish_listening()

    def toggle_mute(self) -> bool:
        with self._lock:
            self.muted = not self.muted
            if self.muted and self.state == State.LISTENING:
                self._endpointer = None
                self.state = State.IDLE
            return self.muted

    def new_conversation(self) -> None:
        self.brain.new_conversation()

    # --- internals -------------------------------------------------------
    def _start_listening(self, push_to_talk: bool) -> None:
        self.chime("Tink")
        self._push_to_talk = push_to_talk
        self._endpointer = Endpointer(
            frame_ms=self.cfg.frame_samples * 1000 // self.cfg.sample_rate,
            rms_threshold=self.cfg.rms_threshold,
            silence_ms=None if push_to_talk else self.cfg.silence_ms,
            max_ms=self.cfg.max_record_ms,
            no_speech_ms=self.cfg.no_speech_ms,
            is_speech=self.is_speech,
        )
        self.state = State.LISTENING

    def _finish_listening(self) -> None:
        audio = self._endpointer.audio()
        self._endpointer = None
        log.info("recorded %.1f s", len(audio) / self.cfg.sample_rate)
        self.state = State.THINKING
        self.spawn(self._handle, audio)

    def _handle(self, audio: np.ndarray) -> None:
        try:
            started = time.monotonic()
            text = self.transcriber.transcribe(audio).strip()
            log.info("heard: %r (%.1f s)", text, time.monotonic() - started)
            if len(text) < 2:
                reply = DIDNT_CATCH
            elif is_new_conversation(text):
                self.brain.new_conversation()
                reply = "Okay, starting a new conversation."
            else:
                reply = self.brain.ask(text, on_slow=lambda: self.speaker.speak(STILL_WORKING, wait=True))
        except Exception:
            log.exception("handling utterance failed")
            reply = SOMETHING_WRONG
        log.info("reply: %r", reply)
        with self._lock:
            self.state = State.SPEAKING
        try:
            self.speaker.speak(reply, wait=True)
        finally:
            with self._lock:
                self.wake.reset()
                self.state = State.IDLE
