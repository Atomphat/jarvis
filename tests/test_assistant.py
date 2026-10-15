import numpy as np

from jarvis.assistant import Assistant, State, is_new_conversation
from jarvis.brain import DIDNT_CATCH, SOMETHING_WRONG
from jarvis.config import Config

LOUD = np.full(1280, 3000, dtype=np.int16)
QUIET = np.zeros(1280, dtype=np.int16)
WAKE = np.full(1280, 7777, dtype=np.int16)  # FakeWake fires on this frame


class FakeWake:
    def __init__(self):
        self.resets = 0
        self.seen = 0

    def process(self, frame):
        self.seen += 1
        return bool(frame[0] == 7777)

    def reset(self):
        self.resets += 1


class FakeTranscriber:
    def __init__(self, text="what time is it"):
        self.text = text
        self.calls = 0

    def transcribe(self, audio):
        self.calls += 1
        return self.text


class FakeBrain:
    def __init__(self, reply="It is noon.", error=None):
        self.reply, self.error = reply, error
        self.asked, self.new = [], 0

    def ask(self, text, on_slow=None):
        if self.error:
            raise self.error
        self.asked.append(text)
        return self.reply

    def new_conversation(self):
        self.new += 1


class FakeSpeaker:
    def __init__(self):
        self.said, self.stopped = [], 0

    def speak(self, text, wait=True):
        self.said.append(text)

    def stop(self):
        self.stopped += 1


class Deferred:
    def __init__(self):
        self.jobs = []

    def __call__(self, fn, *args):
        self.jobs.append((fn, args))

    def run(self):
        for fn, args in self.jobs:
            fn(*args)


def make(text="what time is it", brain=None, spawn=None):
    chimes = []
    a = Assistant(Config(), FakeWake(), FakeTranscriber(text), brain or FakeBrain(), FakeSpeaker(),
                  chime=chimes.append, spawn=spawn or (lambda fn, *args: fn(*args)))
    return a, chimes


def speak_and_pause(a):
    for f in [LOUD] * 5 + [QUIET] * 13:
        a.on_frame(f)


def test_wake_word_full_round_trip():
    a, chimes = make()
    a.on_frame(WAKE)
    assert a.state == State.LISTENING and chimes == ["Tink"]
    speak_and_pause(a)
    assert a.brain.asked == ["what time is it"]
    assert a.speaker.said == ["It is noon."]
    assert a.state == State.IDLE
    assert a.wake.resets == 1


def test_empty_transcript_says_didnt_catch_and_skips_claude():
    a, _ = make(text="")
    a.on_frame(WAKE)
    speak_and_pause(a)
    assert a.brain.asked == []
    assert a.speaker.said == [DIDNT_CATCH]


def test_hotkey_push_to_talk_ignores_pauses_until_release():
    a, _ = make()
    a.on_hotkey_down()
    for f in [LOUD] * 3 + [QUIET] * 30:
        a.on_frame(f)
    assert a.state == State.LISTENING
    a.on_hotkey_up()
    assert a.brain.asked == ["what time is it"]
    assert a.state == State.IDLE


def test_short_tap_is_didnt_catch():
    a, _ = make()
    a.transcriber.text = ""  # real Transcriber returns "" for < 0.5 s of audio
    a.on_hotkey_down()
    a.on_frame(LOUD)
    a.on_hotkey_up()
    assert a.brain.asked == []
    assert a.speaker.said == [DIDNT_CATCH]


def test_busy_while_thinking():
    spawn = Deferred()
    a, chimes = make(spawn=spawn)
    a.on_frame(WAKE)
    speak_and_pause(a)
    assert a.state == State.THINKING
    a.on_hotkey_down()
    a.on_frame(WAKE)
    assert chimes == ["Tink", "Funk"]
    assert a.state == State.THINKING
    spawn.run()
    assert a.state == State.IDLE


def test_hotkey_while_speaking_stops_speech():
    a, _ = make()
    a.state = State.SPEAKING
    a.on_hotkey_down()
    assert a.speaker.stopped == 1


def test_wake_word_ignored_outside_idle():
    a, _ = make()
    a.state = State.SPEAKING
    a.on_frame(WAKE)
    assert a.wake.seen == 0
    assert a.state == State.SPEAKING


def test_mute_while_listening_drops_recording():
    a, _ = make()
    a.on_frame(WAKE)
    a.on_frame(LOUD)
    assert a.toggle_mute() is True
    assert a.state == State.IDLE
    speak_and_pause(a)
    a.on_hotkey_down()
    assert a.brain.asked == [] and a.state == State.IDLE
    assert a.toggle_mute() is False


def test_new_conversation_phrase():
    a, _ = make(text="Jarvis, new conversation.")
    a.on_frame(WAKE)
    speak_and_pause(a)
    assert a.brain.new == 1 and a.brain.asked == []
    assert a.speaker.said == ["Okay, starting a new conversation."]


def test_brain_crash_is_spoken():
    a, _ = make(brain=FakeBrain(error=RuntimeError("boom")))
    a.on_frame(WAKE)
    speak_and_pause(a)
    assert a.speaker.said == [SOMETHING_WRONG]
    assert a.state == State.IDLE


def test_is_new_conversation():
    assert is_new_conversation("Start over")
    assert is_new_conversation("new conversation please")
    assert not is_new_conversation("tell me about the conversation")


def test_speech_detector_is_used_for_endpointing():
    a = Assistant(Config(), FakeWake(), FakeTranscriber(), FakeBrain(), FakeSpeaker(),
                  spawn=lambda fn, *args: fn(*args), is_speech=lambda frame: frame[0] == 1)
    a.on_frame(WAKE)
    for f in [np.ones(1280, dtype=np.int16)] * 3 + [QUIET] * 13:
        a.on_frame(f)
    assert a.brain.asked == ["what time is it"]
