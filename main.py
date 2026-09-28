"""PomoTux entry point. Run: .venv/bin/python main.py [--mini]"""
from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QLockFile
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import QApplication, QMessageBox

from pomotux import __app_id__, __version__
from pomotux.config import Settings
from pomotux.dialogs import OnboardingDialog
from pomotux.main_window import MainWindow
from pomotux.mini_window import MiniWindow
from pomotux.store import Store
from pomotux.timer import PomodoroTimer

_SERVER = "pomotux"


def _wake_existing() -> bool:
    """Ping a running instance to show itself. True when one answered."""
    sock = QLocalSocket()
    sock.connectToServer(_SERVER)
    if not sock.waitForConnected(1000):
        return False
    sock.write(b"show")
    sock.waitForBytesWritten(1000)
    return True


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv
    if "--version" in argv:
        print(__version__)
        return 0
    app = QApplication(argv)
    app.setQuitOnLastWindowClosed(False)
    app.setApplicationName("PomoTux")
    app.setOrganizationName("PomoTux")
    app.setDesktopFileName(__app_id__)

    lock_dir = Path.home() / ".local" / "share" / "pomotux"
    lock_dir.mkdir(parents=True, exist_ok=True)
    lock = QLockFile(str(lock_dir / "pomotux.lock"))
    lock.setStaleLockTime(0)
    if not lock.tryLock(100):
        if _wake_existing():
            return 0
        QMessageBox.information(None, "PomoTux", "PomoTux is already running.")
        return 0
    QLocalServer.removeServer(_SERVER)  # stale socket from a crash
    server = QLocalServer()
    server.listen(_SERVER)

    s = Settings.load()
    store = Store()
    timer = PomodoroTimer(focus_s=s.focus_min * 60, short_s=s.short_min * 60,
                          long_s=s.long_min * 60, long_every=s.long_every)

    win = MainWindow(timer, store, s)
    mini = MiniWindow(timer, s.accent)

    def _on_wake():
        sock = server.nextPendingConnection()
        if sock is not None:
            sock.readAll()
            sock.deleteLater()
        win.present()
        mini.hide()

    server.newConnection.connect(_on_wake)

    win.mini_cb = lambda: (win.hide(), mini.show())
    mini.expand_cb = lambda: (mini.hide(), win.show(), win.apply_theme())
    mini.quit_cb = win.close_app

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
