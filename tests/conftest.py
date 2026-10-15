import subprocess

import numpy as np
import pytest


@pytest.fixture
def speech(tmp_path):
    from jarvis.audio import read_wav  # imported lazily: jarvis.audio arrives in Task 2

    counter = {"n": 0}

    def make(text: str, voice: str = "Samantha") -> np.ndarray:
        counter["n"] += 1
        aiff = tmp_path / f"s{counter['n']}.aiff"
        wav = tmp_path / f"s{counter['n']}.wav"
        subprocess.run(["say", "-v", voice, "-o", str(aiff), text], check=True)
        subprocess.run(
            ["afconvert", "-f", "WAVE", "-d", "LEI16@16000", "-c", "1", str(aiff), str(wav)],
            check=True,
        )
        return read_wav(wav)

    return make
