from jarvis.tts import Speaker, available_voices

SAY_LIST = """Ava (Premium)       en_US    # Hello! My name is Ava.
Samantha            en_US    # Hello! My name is Samantha.
Kanya               th_TH    # สวัสดี! ฉันชื่อกันยา
"""


class FakeProc:
    def __init__(self, args, **kw):
        self.args = args
        self.terminated = False
        self.waited = False

    def wait(self):
        self.waited = True

    def poll(self):
        return 0 if self.terminated else None

    def terminate(self):
        self.terminated = True


class FakePopen:
    def __init__(self):
        self.procs = []

    def __call__(self, args, **kw):
        p = FakeProc(args)
        self.procs.append(p)
        return p


def test_available_voices_parses_names_with_spaces(monkeypatch):
    class R:
        stdout = SAY_LIST

    monkeypatch.setattr("jarvis.tts.subprocess.run", lambda *a, **k: R())
    assert available_voices() == {"Ava (Premium)", "Samantha", "Kanya"}


def test_falls_back_when_voice_missing():
    s = Speaker("Ava (Premium)", "Samantha", voices={"Samantha"}, popen=FakePopen())
    assert s.voice == "Samantha"


def test_speak_builds_command_and_waits():
    popen = FakePopen()
    s = Speaker("Ava (Premium)", "Samantha", rate=185, voices={"Ava (Premium)"}, popen=popen)
    s.speak("Hello there")
    p = popen.procs[0]
    assert p.args == ["say", "-v", "Ava (Premium)", "-r", "185", "Hello there"]
    assert p.waited


def test_stop_terminates_current_speech():
    popen = FakePopen()
    s = Speaker("Samantha", "Samantha", voices={"Samantha"}, popen=popen)
    s.speak("long text", wait=False)
    s.stop()
    assert popen.procs[0].terminated


def test_speak_ignores_empty_text():
    popen = FakePopen()
    Speaker("Samantha", "Samantha", voices={"Samantha"}, popen=popen).speak("   ")
    assert popen.procs == []
