from __future__ import annotations

import numpy as np


class WakeWordDetector:
    def __init__(self, threshold: float = 0.5, model=None):
        if model is None:
            from openwakeword.model import Model

            model = Model(wakeword_models=["hey_jarvis"], inference_framework="onnx")
        self._model = model
        self.threshold = threshold

    def score(self, frame: np.ndarray) -> float:
        predictions = self._model.predict(frame)
        return max(
            (float(v) for k, v in predictions.items() if k.startswith("hey_jarvis")),
            default=0.0,
        )

    def process(self, frame: np.ndarray) -> bool:
        return self.score(frame) >= self.threshold

    def reset(self) -> None:
        self._model.reset()
