from __future__ import annotations

import numpy as np


class SpeechDetector:
    """Silero voice-activity detector (bundled with openWakeWord) as a frame -> bool callable."""

    def __init__(self, threshold: float = 0.5, model=None):
        if model is None:
            from openwakeword.vad import VAD

            model = VAD()
        self._model = model
        self.threshold = threshold

    def __call__(self, frame: np.ndarray) -> bool:
        return float(self._model.predict(frame)) >= self.threshold
