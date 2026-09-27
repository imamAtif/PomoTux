"""Pomodoro state machine driven by a 1s QTimer."""
from __future__ import annotations

from enum import Enum

from PySide6.QtCore import QObject, QTimer, Signal


class Phase(str, Enum):
    FOCUS = "focus"
    SHORT = "short"
    LONG = "long"


LABELS = {Phase.FOCUS: "Focus", Phase.SHORT: "Short break", Phase.LONG: "Long break"}


class PomodoroTimer(QObject):
    """Counts down; emits tick + phase changes. Durations settable in seconds."""

    ticked = Signal(int, str)      # remaining_sec, phase value
    phase_changed = Signal(str)    # phase value
    finished = Signal(str)         # phase just completed

    def __init__(self, focus_s=25 * 60, short_s=5 * 60, long_s=15 * 60,
                 long_every=4, parent=None):
        super().__init__(parent)
        self.durations = {Phase.FOCUS: focus_s, Phase.SHORT: short_s, Phase.LONG: long_s}
        self.long_every = long_every
        self.phase = Phase.FOCUS
        self.remaining = focus_s
        self.running = False
        self.completed_focus = 0
        self._qt = QTimer(self)
        self._qt.setInterval(1000)
        self._qt.timeout.connect(self._on_second)

    def set_minutes(self, focus_m: int, short_m: int, long_m: int, long_every: int):
        was_running = self.running
        self.pause()
        self.durations = {Phase.FOCUS: focus_m * 60, Phase.SHORT: short_m * 60,
                          Phase.LONG: long_m * 60}
        self.long_every = max(1, long_every)
        if not was_running:
            self.remaining = self.durations[self.phase]
            self.ticked.emit(self.remaining, self.phase.value)
        else:
            self.start()

    @property
    def total(self) -> int:
        return self.durations[self.phase]

    @property
    def progress(self) -> float:  # 0..1 elapsed
        if self.total <= 0:
            return 0.0
        return 1.0 - max(0, self.remaining) / self.total

    def start(self):
        if self.remaining <= 0:
            self.remaining = self.durations[self.phase]
        self.running = True
        self._qt.start()

    def pause(self):
        self.running = False
        self._qt.stop()

    def toggle(self):
        self.pause() if self.running else self.start()

    def reset(self):
        self.pause()
        self.remaining = self.durations[self.phase]
        self.ticked.emit(self.remaining, self.phase.value)

    def set_phase(self, phase: Phase):
        self.phase = phase
        self.reset()
        self.phase_changed.emit(self.phase.value)

    def skip(self) -> str:
        done = self.phase.value
        self.finished.emit(done)
        self._advance()
        return done

    def _on_second(self):
        if not self.running:
            return
        self.remaining -= 1
        if self.remaining <= 0:
            self.remaining = 0
            self.pause()
            done = self.phase.value
            self.finished.emit(done)
            self._advance()
        else:
            self.ticked.emit(self.remaining, self.phase.value)

    def _advance(self):
        if self.phase == Phase.FOCUS:
            self.completed_focus += 1
            nxt = Phase.LONG if self.completed_focus % self.long_every == 0 else Phase.SHORT
        else:
            nxt = Phase.FOCUS
        self.phase = nxt
        self.remaining = self.durations[nxt]
        self.phase_changed.emit(nxt.value)
        self.ticked.emit(self.remaining, nxt.value)
