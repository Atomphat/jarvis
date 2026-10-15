import numpy as np
import pytest

from jarvis.audio import split_frames
from jarvis.vad import SpeechDetector


class FakeVad:
    def __init__(self, probs):
        self.probs = list(probs)

    def predict(self, frame):
        return self.probs.pop(0)


def test_threshold():
    d = SpeechDetector(threshold=0.5, model=FakeVad([0.2, 0.8]))
    frame = np.zeros(1280, dtype=np.int16)
    assert d(frame) is False
    assert d(frame) is True


@pytest.mark.integration
def test_real_vad_separates_speech_from_silence(speech):
    d = SpeechDetector()
    silent = [d(f) for f in split_frames(np.zeros(16000, dtype=np.int16))]
    spoken = [d(f) for f in split_frames(speech("What is the capital of France?"))]
    assert not any(silent)
    assert sum(spoken) >= len(spoken) // 3
