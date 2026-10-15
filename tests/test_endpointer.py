import numpy as np

from jarvis.endpointer import Endpointer

LOUD = np.full(1280, 3000, dtype=np.int16)
QUIET = np.zeros(1280, dtype=np.int16)


def feed_all(ep, frames):
    for f in frames:
        if ep.feed(f):
            return True
    return False


def test_stops_after_one_second_of_silence_following_speech():
    ep = Endpointer(silence_ms=1000)
    assert not feed_all(ep, [LOUD] * 5)
    assert not feed_all(ep, [QUIET] * 12)  # 960 ms
    assert ep.feed(QUIET)  # 1040 ms
    assert ep.heard
    assert len(ep.audio()) == 1280 * 18


def test_gives_up_when_nobody_speaks():
    ep = Endpointer(no_speech_ms=5000)
    assert feed_all(ep, [QUIET] * 63)  # 5040 ms
    assert not ep.heard


def test_hard_cap():
    ep = Endpointer(max_ms=30000)
    assert feed_all(ep, [LOUD] * 400)
    assert len(ep.audio()) == 1280 * 375  # 30 000 ms / 80 ms


def test_push_to_talk_ignores_silence_until_finish():
    ep = Endpointer(silence_ms=None)
    assert not feed_all(ep, [LOUD] * 3 + [QUIET] * 100)
    ep.finish()
    assert ep.done
    assert ep.feed(LOUD)  # stays done, audio unchanged
    assert len(ep.audio()) == 1280 * 103


def test_audio_empty_before_any_frame():
    ep = Endpointer()
    assert ep.audio().dtype == np.int16
    assert len(ep.audio()) == 0


def test_custom_speech_detector_overrides_loudness():
    # quiet frames the detector calls speech must count as speech
    flags = iter([True] * 5 + [False] * 13)
    ep = Endpointer(is_speech=lambda frame: next(flags))
    assert not feed_all(ep, [QUIET] * 17)
    assert ep.heard
    assert ep.feed(QUIET)
