"""Linux integrations: notify, sound, DND, autostart. Best-effort, never fatal."""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

_SOUNDS = Path(__file__).parent / "sounds"
if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    # PyInstaller bundle: datas land under <bundle>/pomotux/sounds
    _SOUNDS = Path(sys._MEIPASS) / "pomotux" / "sounds"

# Ordered by latency/quality: paplay is sample-accurate, canberra is the
# GNOME default, aplay is the ALSA fallback. First one found wins.
_PLAYERS = (
    ("paplay", ["{f}"]),
    ("canberra-gtk-play", ["-f", "{f}"]),
    ("aplay", ["-q", "{f}"]),
)


def notify(tray, title: str, body: str, enabled: bool):
    if not enabled:
        return
    # notify-send first: it reaches the notification center even when no
    # system tray exists (stock GNOME). Tray bubble is the fallback.
    if shutil.which("notify-send"):
        subprocess.Popen(["notify-send", "-a", "PomoTux", title, body],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    elif tray is not None:
        try:
            if tray.isVisible():
                tray.showMessage(title, body, tray.MessageIcon.Information, 5000)
        except Exception:
            pass


def play_sound(name: str, enabled: bool):
    """Play a bundled chime (break_start/focus_start). Non-blocking."""
    if not enabled:
        return
    clip = _SOUNDS / f"{name}.wav"
    if not clip.exists():
        return
    for binary, args in _PLAYERS:
        if shutil.which(binary):
            try:
                subprocess.Popen([binary, *[a.format(f=str(clip)) for a in args]],
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                pass
            return


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
