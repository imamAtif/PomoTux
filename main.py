"""PomoTux entry point. Run: .venv/bin/python main.py [--mini]"""
from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from pomotux import __app_id__, __version__
from pomotux.config import Settings
from pomotux.dialogs import OnboardingDialog
from pomotux.main_window import MainWindow
from pomotux.mini_window import MiniWindow
from pomotux.store import Store
from pomotux.timer import PomodoroTimer


def main(argv: list[str]) -> int:
    if "--version" in argv:
        print(__version__)
        return 0
    app = QApplication(argv)
    app.setApplicationName("PomoTux")
    app.setOrganizationName("PomoTux")
    app.setDesktopFileName(__app_id__)

    s = Settings.load()
    store = Store()
    timer = PomodoroTimer(focus_s=s.focus_min * 60, short_s=s.short_min * 60,
                          long_s=s.long_min * 60, long_every=s.long_every)

    win = MainWindow(timer, store, s)
    mini = MiniWindow(timer, s.accent)

    win.mini_cb = lambda: (win.hide(), mini.show())
    mini.expand_cb = lambda: (mini.hide(), win.show(), win.apply_theme())

    if s.first_run:
        dlg = OnboardingDialog(s, win)
        if dlg.exec():
            dlg.apply(s)
            s.save()

    if "--mini" in argv:
        mini.show()
    else:
        win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
