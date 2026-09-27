"""Linux integrations: notify, beep, DND, autostart. Best-effort, never fatal."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from PySide6.QtWidgets import QApplication


def notify(app: QApplication, tray, title: str, body: str, enabled: bool):
    if not enabled:
        return
    try:  # native tray bubble (works on most DEs)
        if tray and tray.isVisible():
            tray.showMessage(title, body, tray.MessageIcon.Information, 5000)
            return
    except Exception:
        pass
    if shutil.which("notify-send"):  # fallback for Wayland w/o tray
        subprocess.Popen(["notify-send", title, body])


def beep(enabled: bool):
    if enabled:
        QApplication.beep()


def set_dnd(on: bool):
    """GNOME Do-Not-Disturb. No-op elsewhere. Never raises."""
    if not shutil.which("gsettings"):
        return
    try:
        subprocess.run(["gsettings", "set", "org.gnome.desktop.notifications",
                        "show-banners", "false" if on else "true"],
                       check=False, capture_output=True)
    except Exception:
        pass


def set_autostart(on: bool):
    desktop = Path.home() / ".config" / "autostart" / "pomotux.desktop"
    if on:
        desktop.parent.mkdir(parents=True, exist_ok=True)
        desktop.write_text(
            "[Desktop Entry]\nType=Application\nName=PomoTux\n"
            "Exec=pomotux\nX-GNOME-Autostart-enabled=true\n")
    else:
        try:
            desktop.unlink()
        except FileNotFoundError:
            pass
