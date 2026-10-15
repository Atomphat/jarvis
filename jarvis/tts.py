from __future__ import annotations

import re
import subprocess
import threading

_VOICE_LINE = re.compile(r"^(.+?)\s{2,}[a-z]{2,3}_[A-Za-z0-9]+")


def available_voices(say_bin: str = "say") -> set[str]:
    out = subprocess.run([say_bin, "-v", "?"], capture_output=True, text=True).stdout
    voices = set()
    for line in out.splitlines():
        m = _VOICE_LINE.match(line)
        if m:
            voices.add(m.group(1).strip())
    return voices


def chime(name: str) -> None:
    subprocess.Popen(
        ["afplay", f"/System/Library/Sounds/{name}.aiff"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


class Speaker:
    def __init__(
        self,
        voice: str,
        fallback_voice: str,
        rate: int = 185,
        say_bin: str = "say",
        voices: set[str] | None = None,
        popen=subprocess.Popen,
    ):
        known = voices if voices is not None else available_voices(say_bin)
        self.voice = voice if voice in known else fallback_voice
        self.rate = rate
        self.say_bin = say_bin
        self._popen = popen
        self._proc = None
        self._lock = threading.Lock()

    def speak(self, text: str, wait: bool = True) -> None:
        text = text.strip()
        if not text:
            return
        with self._lock:
            self._proc = self._popen(
                [self.say_bin, "-v", self.voice, "-r", str(self.rate), text],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            proc = self._proc
        if wait:
            proc.wait()

    def stop(self) -> None:
        with self._lock:
            if self._proc is not None and self._proc.poll() is None:
                self._proc.terminate()
