from __future__ import annotations

from typing import Callable

import numpy as np

from jarvis.audio import rms


class Endpointer:
    """Collects frames for one utterance and decides when it is over."""

    def __init__(
        self,
        frame_ms: int = 80,
        rms_threshold: float = 500.0,
        silence_ms: int | None = 1000,
        max_ms: int = 30000,
        no_speech_ms: int = 5000,
        is_speech: Callable[[np.ndarray], bool] | None = None,
    ):
        self.frame_ms = frame_ms
        self.rms_threshold = rms_threshold
        self.silence_ms = silence_ms
        self.max_ms = max_ms
        self.no_speech_ms = no_speech_ms
        self.is_speech = is_speech or (lambda frame: rms(frame) >= self.rms_threshold)
        self._frames: list[np.ndarray] = []
        self._elapsed = 0
        self._silent = 0
        self.heard = False
        self.done = False

    def feed(self, frame: np.ndarray) -> bool:
        if self.done:
            return True
        self._frames.append(frame)
        self._elapsed += self.frame_ms
        if self.is_speech(frame):
            self.heard = True
            self._silent = 0
        elif self.heard:
            self._silent += self.frame_ms
        if self._elapsed >= self.max_ms:
            self.done = True
        elif self.silence_ms is not None:
            if self.heard and self._silent >= self.silence_ms:
                self.done = True
            elif not self.heard and self._elapsed >= self.no_speech_ms:
                self.done = True
        return self.done

    def finish(self) -> None:
        self.done = True

    def audio(self) -> np.ndarray:
        if not self._frames:
            return np.zeros(0, dtype=np.int16)
        return np.concatenate(self._frames).astype(np.int16)
