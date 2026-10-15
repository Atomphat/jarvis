from __future__ import annotations

import logging
from typing import Callable

log = logging.getLogger(__name__)

RIGHT_OPTION_KEYCODE = 61
OPTION_FLAG = 1 << 19  # NSEventModifierFlagOption
_FLAGS_CHANGED_MASK = 1 << 12  # NSEventMaskFlagsChanged


class RightOptionHotkey:
    def __init__(self, on_down: Callable[[], None], on_up: Callable[[], None]):
        self.on_down = on_down
        self.on_up = on_up
        self._down = False
        self._monitor = None

    def handle_flags(self, keycode: int, flags: int) -> None:
        if keycode != RIGHT_OPTION_KEYCODE:
            return
        pressed = bool(flags & OPTION_FLAG)
        if pressed and not self._down:
            self._down = True
            self.on_down()
        elif not pressed and self._down:
            self._down = False
            self.on_up()

    def start(self) -> None:
        from AppKit import NSEvent

        def handler(event):
            try:
                self.handle_flags(int(event.keyCode()), int(event.modifierFlags()))
            except Exception:
                log.exception("hotkey handler failed")

        self._monitor = NSEvent.addGlobalMonitorForEventsMatchingMask_handler_(_FLAGS_CHANGED_MASK, handler)
        if self._monitor is None:
            log.warning("global key monitor not installed; grant Accessibility permission")
