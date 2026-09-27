"""Linux integrations: notify, sound, DND, autostart. Best-effort, never fatal."""
from __future__ import annotations

import shlex
import shutil
import subprocess
import sys
import tempfile
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


def play_file(clip, enabled: bool):
    """Play any audio file. Non-blocking, never raises."""
    if not enabled:
        return
    clip = Path(str(clip)).expanduser()
    if not clip.is_file():
        return
    for binary, args in _PLAYERS:
        if shutil.which(binary):
            try:
                subprocess.Popen([binary, *[a.format(f=str(clip)) for a in args]],
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                pass
            return


def play_sound(name: str, enabled: bool):
    """Play a bundled chime (break_start/focus_start)."""
    play_file(_SOUNDS / f"{name}.wav", enabled)


def play_alert(custom: str, fallback: str, enabled: bool):
    """Play the user's file when set, otherwise the bundled chime."""
    if custom and Path(custom).expanduser().is_file():
        play_file(custom, enabled)
    else:
        play_sound(fallback, enabled)


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


START_MARK = "# pomotux block start (managed by PomoTux, do not edit)"
END_MARK = "# pomotux block end"
_HELPER = "/usr/bin/pomotux-hosts"  # one-time sudo setup, then silent
MANUAL_UNBLOCK = "sudo sed -i '/# pomotux block start/,/# pomotux block end/d' /etc/hosts"


def blocked_variants(hosts: list[str]) -> list[str]:
    """Each host plus its www counterpart, normalized and deduplicated."""
    out = set()
    for h in hosts:
        h = h.strip().lower().rstrip(".")
        if not h:
            continue
        out.add(h)
        out.add(h[4:] if h.startswith("www.") else "www." + h)
    return sorted(out)


def update_hosts(text: str, hosts: list[str], blocked: bool) -> str:
    """Add/remove the managed block. Pure function, safe to test."""
    kept, skipping = [], False
    for ln in text.splitlines():
        stripped = ln.strip()
        if stripped == START_MARK:
            skipping = True
            continue
        if stripped == END_MARK:
            skipping = False
            continue
        if not skipping:
            kept.append(ln)
    if blocked and hosts:
        kept.append(START_MARK)
        kept += [f"127.0.0.1 {h}" for h in blocked_variants(hosts)]
        kept.append(END_MARK)
    out = "\n".join(kept)
    return out + "\n" if text.endswith("\n") and out else out


def has_managed_block(hosts_file: str = "/etc/hosts") -> bool:
    try:
        return START_MARK in Path(hosts_file).read_text()
    except OSError:
        return False


def helper_installed() -> bool:
    return Path(_HELPER).is_file()


def block_helper_source() -> Path | None:
    """Dir holding pomotux-hosts + rule for the setup button (any package)."""
    candidates = []
    if getattr(sys, "frozen", False):
        # PyInstaller bundle (tarball/AppImage): datas sit beside the binary.
        candidates.append(Path(sys.executable).parent / "pomotux" / "block-helper")
    else:
        candidates.append(Path(__file__).parent.parent / "packaging" / "block-helper")
    for d in candidates:
        if (d / "pomotux-hosts").is_file() and (d / "io.github.pomotux.rules").is_file():
            return d
    return None


def install_block_helper(srcdir: Path) -> bool:
    """One-click setup: stage files where root can read them, install via
    a single pkexec prompt. Needed for AppImage/tarball (deb/rpm do it)."""
    host, rule = Path(srcdir) / "pomotux-hosts", Path(srcdir) / "io.github.pomotux.rules"
    if not (host.is_file() and rule.is_file()) or not shutil.which("pkexec"):
        return False
    # Stage under /tmp: root cannot read user FUSE mounts (AppImage).
    tmp = Path(tempfile.mkdtemp(prefix="pomotux-helper-"))
    try:
        tmp.chmod(0o755)
        for src, mode in ((host, 0o755), (rule, 0o644)):
            dest = tmp / src.name
            shutil.copy(src, dest)
            dest.chmod(mode)
        script = (f"install -Dm755 {shlex.quote(str(tmp / host.name))} {_HELPER} && "
                  f"install -Dm644 {shlex.quote(str(tmp / rule.name))} "
                  "/usr/share/polkit-1/rules.d/io.github.pomotux.rules")
        r = subprocess.run(["pkexec", "sh", "-c", script],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           check=False)
        return r.returncode == 0 and helper_installed()
    except Exception:
        return False
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def set_hosts_blocked(hosts: list[str], blocked: bool,
                      hosts_file: str = "/etc/hosts") -> bool:
    """Apply/remove the DNS block. Asks for root only when a change is needed."""
    try:
        current = Path(hosts_file).read_text()
    except OSError:
        return False
    updated = update_hosts(current, hosts, blocked)
    if updated == current:
        return True  # already in the desired state, no auth needed
    try:
        Path(hosts_file).write_text(updated)
        return True
    except OSError:
        pass
    if not shutil.which("pkexec"):
        return False
    try:
        if Path(_HELPER).is_file():
            # Silent after the one-time sudo setup (polkit rule).
            clean = [h.strip() for h in hosts if h.strip()]
            argv = ["pkexec", _HELPER, "clear"] if not (blocked and clean) \
                else ["pkexec", _HELPER, "block", *clean]
            r = subprocess.run(argv, stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL, check=False)
        else:
            # No helper: fall back to a per-change password prompt.
            r = subprocess.run(["pkexec", "tee", hosts_file], input=updated.encode(),
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                               check=False)
        return r.returncode == 0
    except Exception:
        return False
