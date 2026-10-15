import numpy as np
import pytest

from jarvis.audio import split_frames
from jarvis.wakeword import WakeWordDetector


class FakeModel:
    def __init__(self, scores):
        self.scores = list(scores)
        self.resets = 0

    def predict(self, frame):
        return {"hey_jarvis_v0.1": self.scores.pop(0)}

    def reset(self):
        self.resets += 1


def test_process_uses_threshold():
    d = WakeWordDetector(threshold=0.5, model=FakeModel([0.1, 0.7]))
    frame = np.zeros(1280, dtype=np.int16)
    assert d.process(frame) is False
    assert d.process(frame) is True


def test_reset_delegates():
    model = FakeModel([])
    WakeWordDetector(model=model).reset()
    assert model.resets == 1


def _padded(audio):
    pad = np.zeros(16000, dtype=np.int16)
    return np.concatenate([pad, audio, pad])


@pytest.mark.integration
def test_detects_hey_jarvis(speech):
    d = WakeWordDetector()
    audio = _padded(speech("Hey Jarvis"))
    assert any(d.process(f) for f in split_frames(audio))


@pytest.mark.integration
def test_ignores_other_speech(speech):
    d = WakeWordDetector()
    audio = _padded(speech("The weather is nice today, let's go for a walk."))
    assert not any(d.process(f) for f in split_frames(audio))
