import numpy as np
import pytest

from jarvis.config import Config, find_bin
from jarvis.stt import Transcriber, clean_transcript


def test_clean_removes_markers_and_whitespace():
    assert clean_transcript(" [BLANK_AUDIO]\n Hello   there. (music)\n") == "Hello there."


def test_clean_empty():
    assert clean_transcript("\n  [BLANK_AUDIO] \n") == ""


def test_too_short_audio_returns_empty_without_running_whisper():
    t = Transcriber(whisper_bin="/nonexistent/whisper", model_path=Config().whisper_model)
    assert t.transcribe(np.zeros(4000, dtype=np.int16)) == ""


def test_whisper_failure_raises(tmp_path):
    t = Transcriber(whisper_bin="/usr/bin/false", model_path=tmp_path / "missing.bin")
    with pytest.raises(RuntimeError):
        t.transcribe(np.zeros(16000, dtype=np.int16))


@pytest.mark.integration
def test_transcribes_real_speech(speech):
    cfg = Config()
    t = Transcriber(find_bin("whisper-cli"), cfg.whisper_model)
    text = t.transcribe(speech("What is the capital of Japan?")).lower()
    assert "capital" in text and "japan" in text
