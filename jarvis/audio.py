from __future__ import annotations

import queue
import wave
from typing import TYPE_CHECKING, Iterator

import numpy as np

if TYPE_CHECKING:
    from jarvis.endpointer import Endpointer


def rms(frame: np.ndarray) -> float:
    if frame.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(frame.astype(np.float64) ** 2)))


def write_wav(path, audio: np.ndarray, sample_rate: int = 16000) -> None:
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(audio.astype(np.int16).tobytes())


def read_wav(path) -> np.ndarray:
    with wave.open(str(path), "rb") as w:
        if w.getnchannels() != 1 or w.getsampwidth() != 2:
            raise ValueError("expected 16-bit mono wav")
        return np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).copy()


def split_frames(audio: np.ndarray, frame_samples: int = 1280) -> Iterator[np.ndarray]:
    for start in range(0, len(audio) - frame_samples + 1, frame_samples):
        yield audio[start : start + frame_samples]


class MicStream:
    """16 kHz mono int16 microphone stream delivered as fixed-size frames."""

    def __init__(self, sample_rate: int = 16000, frame_samples: int = 1280):
        import sounddevice as sd

        self.queue: queue.Queue[np.ndarray] = queue.Queue(maxsize=200)
        self._stream = sd.InputStream(
            samplerate=sample_rate,
            channels=1,
            dtype="int16",
            blocksize=frame_samples,
            callback=self._callback,
        )

    def _callback(self, indata, frames, time_info, status) -> None:
        try:
            self.queue.put_nowait(indata[:, 0].copy())
        except queue.Full:
            pass

    def __enter__(self) -> "MicStream":
        self._stream.start()
        return self

    def __exit__(self, *exc) -> None:
        self._stream.stop()
        self._stream.close()

    def read(self, timeout: float = 1.0) -> np.ndarray | None:
        try:
            return self.queue.get(timeout=timeout)
        except queue.Empty:
            return None


def record_utterance(
    endpointer: "Endpointer", sample_rate: int = 16000, frame_samples: int = 1280
) -> np.ndarray:
    with MicStream(sample_rate, frame_samples) as mic:
        while not endpointer.done:
            frame = mic.read(timeout=1.0)
            if frame is not None:
                endpointer.feed(frame)
    return endpointer.audio()
