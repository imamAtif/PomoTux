"""Hosts-file site blocker: pure logic plus window wiring (root mocked)."""
from pomotux import platform_linux as plat
from pomotux.config import Settings
from pomotux.dialogs import SettingsDialog
from pomotux.main_window import MainWindow
from pomotux.store import Store
from pomotux.timer import Phase, PomodoroTimer


def test_blocker_toggle_overrides_list(tmp_path, app):
    s = Settings(blocker_enabled=True, blocked_hosts=["youtube.com"])
    dlg = SettingsDialog(s, Store(tmp_path / "d.db"))
    assert dlg.cb_block.isChecked()
    dlg.cb_block.setChecked(False)  # list stays, blocking stops
    dlg.ed_hosts.setText("youtube.com")
    dlg.apply(s)
    assert s.blocked_hosts == ["youtube.com"]
    assert s.blocker_enabled is False


def test_variants_expand_www():
    assert plat.blocked_variants(["YouTube.com ", ""]) == ["www.youtube.com", "youtube.com"]
    assert plat.blocked_variants(["www.x.com"]) == ["www.x.com", "x.com"]


def test_update_hosts_add_remove_idempotent():
    base = "127.0.0.1 localhost\n"
    blocked = plat.update_hosts(base, ["youtube.com"], True)
    assert "127.0.0.1 youtube.com" in blocked
    assert "127.0.0.1 www.youtube.com" in blocked
    assert "127.0.0.1 localhost" in blocked
    assert plat.update_hosts(blocked, ["youtube.com"], True) == blocked  # no dupes
    assert plat.update_hosts(blocked, ["youtube.com"], False) == base  # clean removal


def test_set_hosts_noop_needs_no_auth(tmp_path, monkeypatch):
    f = tmp_path / "hosts"
    f.write_text("127.0.0.1 localhost\n")
    monkeypatch.setattr(plat.shutil, "which", lambda *a: (_ for _ in ()).throw(
        AssertionError("must not escalate when nothing changes")))
    assert plat.set_hosts_blocked([], False, str(f)) is True


def test_set_hosts_writes_and_escalates(tmp_path, monkeypatch):
    f = tmp_path / "hosts"
    f.write_text("127.0.0.1 localhost\n")
    calls = []
    monkeypatch.setattr(plat.shutil, "which", lambda binary: "/usr/bin/pkexec")

    class Proc:
        returncode = 0

    def fake_run(argv, **kw):
        calls.append((argv, kw["input"]))
        Path = __import__("pathlib").Path
        target = Path(argv[-1])
        target.chmod(0o644)  # real pkexec runs as root: always writable
        target.write_bytes(kw["input"])
        return Proc()

    monkeypatch.setattr(plat.subprocess, "run", fake_run)
    # tmp file is directly writable: no escalation needed
    assert plat.set_hosts_blocked(["youtube.com"], True, str(f)) is True
    assert calls == [] and "youtube.com" in f.read_text()

    f.chmod(0o444)
    assert plat.set_hosts_blocked(["x.com"], True, str(f)) is True
    assert calls and b"x.com" in calls[0][1]
    f.chmod(0o644)


def test_toggle_off_ignores_list(tmp_path, app, monkeypatch):
    s = Settings(blocker_enabled=False, blocked_hosts=["youtube.com"])
    store = Store(tmp_path / "t.db")
    timer = PomodoroTimer(focus_s=60, short_s=60, long_s=60)
    win = MainWindow(timer, store, s)
    monkeypatch.setattr(plat, "set_hosts_blocked", lambda *a: (_ for _ in ()).throw(
        AssertionError("must not touch hosts when toggle is off")))
    timer.start()
    assert win._sites_blocked is False


def test_helper_source_resolves_in_checkout():
    src = plat.block_helper_source()
    assert src is not None and (src / "pomotux-hosts").is_file()


def test_helper_source_resolves_in_frozen_bundle(tmp_path, monkeypatch):
    bundle = tmp_path / "PomoTux-bundle"
    data = bundle / "pomotux" / "block-helper"
    data.mkdir(parents=True)
    (data / "pomotux-hosts").write_text("#!/bin/sh\n")
    (data / "io.github.pomotux.rules").write_text("// rule\n")
    monkeypatch.setattr(plat.sys, "frozen", True, raising=False)
    monkeypatch.setattr(plat.sys, "executable", str(bundle / "PomoTux"))
    assert plat.block_helper_source() == data


def test_install_helper_stages_and_runs_pkexec_once(tmp_path, monkeypatch):
    src = tmp_path / "src"
    src.mkdir()
    (src / "pomotux-hosts").write_text("#!/bin/sh\n")
    (src / "io.github.pomotux.rules").write_text("// rule\n")
    monkeypatch.setattr(plat.shutil, "which", lambda binary: "/usr/bin/pkexec")
    monkeypatch.setattr(plat, "_HELPER", str(tmp_path / "installed-helper"))
    calls = []

    class Proc:
        returncode = 0

    def fake_run(argv, **kw):
        calls.append(argv)
        Path = __import__("pathlib").Path
        Path(plat._HELPER).write_text("#!/bin/sh\n")
        return Proc()

    monkeypatch.setattr(plat.subprocess, "run", fake_run)
    assert plat.install_block_helper(src) is True
    assert calls and calls[0][:3] == ["pkexec", "sh", "-c"]
    assert "install -Dm755" in calls[0][3]


def test_install_helper_fails_cleanly(tmp_path):
    assert plat.install_block_helper(tmp_path / "missing") is False


def test_helper_preferred_over_tee(tmp_path, monkeypatch):
    f = tmp_path / "hosts"
    f.write_text("127.0.0.1 localhost\n")
    f.chmod(0o444)  # force the privileged path
    helper = str(__import__("pathlib").Path("packaging/block-helper/pomotux-hosts").absolute())
    monkeypatch.setattr(plat, "_HELPER", helper)
    monkeypatch.setattr(plat.shutil, "which", lambda binary: f"/usr/bin/{binary}")
    calls = []

    class Proc:
        returncode = 0

    monkeypatch.setattr(plat.subprocess, "run",
                        lambda argv, **kw: calls.append(argv) or Proc())
    assert plat.set_hosts_blocked(["YouTube.com "], True, str(f)) is True
    assert calls == [["pkexec", helper, "block", "YouTube.com"]]
    f.chmod(0o644)


def test_has_managed_block(tmp_path):
    f = tmp_path / "hosts"
    f.write_text("127.0.0.1 localhost\n")
    assert plat.has_managed_block(str(f)) is False
    f.write_text(plat.update_hosts(f.read_text(), ["x.com"], True))
    assert plat.has_managed_block(str(f)) is True


def test_clear_warns_when_root_denied(tmp_path, app, monkeypatch):
    s = Settings(blocker_enabled=True, blocked_hosts=["youtube.com"])
    win = MainWindow.__new__(MainWindow)  # helper only needs tray + settings
    win.s = s
    win._sites_blocked = True
    notes = []
    monkeypatch.setattr(plat, "set_hosts_blocked", lambda *a: False)
    monkeypatch.setattr(plat, "has_managed_block", lambda *a: True)
    monkeypatch.setattr(plat, "notify",
                        lambda tray, title, body, enabled: notes.append(body))
    win.tray = None
    assert win._clear_block_or_warn() is False
    assert notes and "sudo sed" in notes[0]


def test_heal_skips_when_blocker_on(tmp_path, app, monkeypatch):
    s = Settings(blocker_enabled=True, blocked_hosts=["youtube.com"])
    store = Store(tmp_path / "h.db")
    timer = PomodoroTimer(focus_s=60, short_s=60, long_s=60)
    monkeypatch.setattr(plat, "has_managed_block", lambda *a: True)
    monkeypatch.setattr(plat, "set_hosts_blocked", lambda *a: (_ for _ in ()).throw(
        AssertionError("heal must not touch a consented block")))
    MainWindow(timer, store, s)  # init runs the heal check


def test_window_blocks_on_focus_unblocks_on_break(tmp_path, app, monkeypatch):
    s = Settings(break_overlay=False, notify=False, sound=False,
                 blocker_enabled=True, blocked_hosts=["youtube.com"])
    store = Store(tmp_path / "b.db")
    timer = PomodoroTimer(focus_s=60, short_s=60, long_s=60)
    win = MainWindow(timer, store, s)
    calls = []
    monkeypatch.setattr(plat, "set_hosts_blocked",
                        lambda hosts, blocked, *a: calls.append((list(hosts), blocked)) or True)
    timer.start()
    assert calls == [(["youtube.com"], True)]
    timer.skip()  # end focus early -> break: block lifted via phase change
    assert calls[-1] == (["youtube.com"], False)
    assert win._sites_blocked is False
