from jarvis.hotkey import OPTION_FLAG, RIGHT_OPTION_KEYCODE, RightOptionHotkey


def make():
    events = []
    hk = RightOptionHotkey(on_down=lambda: events.append("down"), on_up=lambda: events.append("up"))
    return hk, events


def test_press_and_release():
    hk, events = make()
    hk.handle_flags(RIGHT_OPTION_KEYCODE, OPTION_FLAG)
    hk.handle_flags(RIGHT_OPTION_KEYCODE, 0)
    assert events == ["down", "up"]


def test_other_keys_ignored():
    hk, events = make()
    hk.handle_flags(58, OPTION_FLAG)  # left option
    hk.handle_flags(56, 0)            # shift
    assert events == []


def test_repeated_down_fires_once():
    hk, events = make()
    hk.handle_flags(RIGHT_OPTION_KEYCODE, OPTION_FLAG)
    hk.handle_flags(RIGHT_OPTION_KEYCODE, OPTION_FLAG | 1)
    assert events == ["down"]


def test_release_without_press_ignored():
    hk, events = make()
    hk.handle_flags(RIGHT_OPTION_KEYCODE, 0)
    assert events == []
