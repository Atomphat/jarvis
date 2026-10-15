from __future__ import annotations

import re
import subprocess
import tempfile
from pathlib import Path

import numpy as np

from jarvis.audio import write_wav

_MARKERS = re.compile(r"\[[^\]]*\]|\([^)]*\)")


def clean_transcript(raw: str) -> str:
    return " ".join(_MARKERS.sub(" ", raw).split())


class Transcriber:
    def __init__(self, whisper_bin: str, model_path: Path, threads: int = 4, min_samples: int = 8000):
        self.whisper_bin = whisper_bin
        self.model_path = Path(model_path)
        self.threads = threads
        self.min_samples = min_samples  # 0.5 s at 16 kHz

    def transcribe(self, audio: np.ndarray) -> str:
        if len(audio) < self.min_samples:
            return ""
        with tempfile.TemporaryDirectory() as tmp:
            wav = Path(tmp) / "utterance.wav"
            write_wav(wav, audio)
            proc = subprocess.run(
                [
                    self.whisper_bin,
                    "-m", str(self.model_path),
                    "-f", str(wav),
                    "-l", "en",
                    "-nt",
                    "-np",
                    "-t", str(self.threads),
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )
        if proc.returncode != 0:
            raise RuntimeError(f"whisper-cli failed: {proc.stderr.strip()[-500:]}")
        return clean_transcript(proc.stdout)
