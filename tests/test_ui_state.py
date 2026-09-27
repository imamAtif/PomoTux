"""Pause indication and window wiring (offscreen)."""
from pomotux.config import Settings
from pomotux.main_window import MainWindow
from pomotux.mini_window import MiniWindow
from pomotux.store import Store
from pomotux.timer import Phase, PomodoroTimer


def _windows(tmp_path, app):
    s = Settings(break_overlay=False, notify=False, sound=False)
    store = Store(tmp_path / "ui.db")
    timer = PomodoroTimer(focus_s=1500, short_s=300, long_s=900)
    return MainWindow(timer, store, s), MiniWindow(timer, s.accent), timer


def test_pause_indication_main_and_mini(tmp_path, app):
    win, mini, timer = _windows(tmp_path, app)
    assert win.lbl_state.text() == "Ready"
    assert win.ring._paused and mini.ring._paused

    timer.start()
    timer._on_second()
    assert win.lbl_state.text() == "Focusing"
    assert not win.ring._paused and not mini.ring._paused

    timer.pause()
    timer.ticked.emit(timer.remaining, timer.phase.value)
    assert win.lbl_state.text() == "Paused"
    assert mini.lbl.text() == "Paused"
    assert "(paused)" in win.tray.toolTip()
    assert win.ring._paused and mini.ring._paused


def test_pause_mid_break(tmp_path, app):
    win, mini, timer = _windows(tmp_path, app)
    timer.set_phase(Phase.SHORT)
    timer.start()
    timer._on_second()
    timer.pause()
    timer.ticked.emit(timer.remaining, timer.phase.value)
    assert win.lbl_state.text() == "Paused"
    assert mini.lbl.text() == "Paused"
    timer.toggle()  # resume updates instantly
    assert win.lbl_state.text() == "On short break"
    assert not win.ring._paused


def test_mini_close_quits_app(tmp_path, app):
    from pomotux.mini_window import MiniWindow
    mini = MiniWindow(PomodoroTimer(), "#F2B705")
    called = []
    mini.quit_cb = lambda: called.append(True)
    mini.show()
    app.processEvents()
    mini.close()
    app.processEvents()
    assert called == [True]


def test_finish_logs_session(tmp_path, app):
    win, _mini, timer = _windows(tmp_path, app)
    win.ed_task.setText("UI task")
    win._add_task()
    win._task_selected(0)
    win._on_finished("focus")
    assert win.store.today_focus() == 1
    assert "Today: 1" in win.lbl_today.text()
