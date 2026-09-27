"""Custom alert sounds: fallback chain and settings wiring (no real playback)."""
from pomotux import platform_linux as plat
from pomotux.config import Settings
from pomotux.dialogs import SettingsDialog
from pomotux.store import Store


def test_alert_uses_custom_file(monkeypatch, tmp_path):
    played = []
    monkeypatch.setattr(plat.subprocess, "Popen",
                        lambda argv, **kw: played.append(argv) or DummyProc())
    monkeypatch.setattr(plat.shutil, "which", lambda binary: f"/usr/bin/{binary}")
    custom = tmp_path / "mine.ogg"
    custom.write_bytes(b"fake")
    plat.play_alert(str(custom), "break_start", True)
    assert played and played[0][1].endswith("mine.ogg")


def test_alert_falls_back_when_custom_missing(monkeypatch):
    played = []
    monkeypatch.setattr(plat.subprocess, "Popen",
                        lambda argv, **kw: played.append(argv) or DummyProc())
    monkeypatch.setattr(plat.shutil, "which", lambda binary: f"/usr/bin/{binary}")
    plat.play_alert("/does/not/exist.ogg", "break_start", True)
    assert played and played[0][1].endswith("break_start.wav")


def test_alert_respects_master_switch(monkeypatch):
    monkeypatch.setattr(plat.subprocess, "Popen", lambda *a, **k: (_ for _ in ()).throw(
        AssertionError("must not spawn when disabled")))
    plat.play_alert("", "break_start", False)
    plat.play_file("/bin/true", False)


def test_settings_dialog_saves_sound_paths(tmp_path, app):
    s = Settings()
    dlg = SettingsDialog(s, Store(tmp_path / "d.db"))
    dlg.ed_break_sound.setText("/music/break.ogg")
    dlg.ed_focus_sound.setText("")  # cleared = bundled default
    dlg.apply(s)
    assert s.break_sound == "/music/break.ogg"
    assert s.focus_sound == ""


class DummyProc:
    pass
