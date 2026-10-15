import numpy as np

from jarvis.audio import read_wav, rms, split_frames, write_wav


def test_rms_of_silence_is_zero():
    assert rms(np.zeros(1280, dtype=np.int16)) == 0.0


def test_rms_of_empty_is_zero():
    assert rms(np.zeros(0, dtype=np.int16)) == 0.0


def test_rms_of_constant():
    assert rms(np.full(1280, 1000, dtype=np.int16)) == 1000.0


def test_wav_roundtrip(tmp_path):
    audio = (np.arange(16000) % 200 - 100).astype(np.int16)
    path = tmp_path / "a.wav"
    write_wav(path, audio)
    assert np.array_equal(read_wav(path), audio)


def test_split_frames_drops_partial_tail():
    frames = list(split_frames(np.zeros(1280 * 3 + 100, dtype=np.int16)))
    assert len(frames) == 3
    assert all(len(f) == 1280 for f in frames)
