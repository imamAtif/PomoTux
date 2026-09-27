"""Pomodoro state machine: phases, skip, toggle feedback."""
from pomotux.timer import LABELS, Phase, PomodoroTimer


def test_full_cycle():
    t = PomodoroTimer(focus_s=2, short_s=1, long_s=1, long_every=2)
    done = []
    t.finished.connect(done.append)
    t.start()
    t._on_second()
    t._on_second()  # focus (2s) completes
    assert done == ["focus"] and t.phase == Phase.SHORT
    t.start()  # auto-paused after advance; restart short break
    t._on_second()
    assert t.phase == Phase.FOCUS  # back to focus, 1 completed
    assert LABELS[Phase.FOCUS] == "Focus"


def test_long_break_every_n():
    t = PomodoroTimer(focus_s=1, short_s=1, long_s=1, long_every=2)
    t.start()
    for _ in range(2):  # finish 1st focus -> short
        t._on_second()
    assert t.phase == Phase.SHORT
    t.skip()  # end short early -> focus
    assert t.phase == Phase.FOCUS
    t.start()
    t._on_second()  # finish 2nd focus -> long
    assert t.phase == Phase.LONG


def test_toggle_emits_tick_immediately():
    t = PomodoroTimer(focus_s=60, short_s=60, long_s=60)
    seen = []
    t.ticked.connect(lambda sec, phase: seen.append((sec, phase)))
    t.toggle()  # start
    assert t.running and seen == [(60, "focus")]
    t.toggle()  # pause
    assert not t.running and len(seen) == 2


def test_set_minutes_resets_when_paused():
    t = PomodoroTimer()
    t.set_minutes(50, 10, 20, 4)
    assert t.durations[Phase.FOCUS] == 50 * 60
    assert t.remaining == 50 * 60 and t.long_every == 4
