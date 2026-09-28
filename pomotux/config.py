"""App settings: defaults, JSON load/save. No third-party deps."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path


def _config_path() -> Path:
    return Path.home() / ".config" / "pomotux" / "settings.json"


@dataclass
class Settings:
    focus_min: int = 25
    short_min: int = 5
    long_min: int = 15
    long_every: int = 4  # focus sessions before a long break

    auto_start_breaks: bool = True
    auto_start_focus: bool = True

    theme: str = "auto"  # auto | dark | light
    accent: str = "#F2B705"  # Tux yellow

    sound: bool = True
    notify: bool = True
    minimize_to_tray: bool = False  # X quits; enable to hide instead

    # Custom alert files. Empty means the bundled chime.
    break_sound: str = ""
    focus_sound: str = ""

    # Focus extras (all opt-in via onboarding, toggleable later)
    dnd: bool = False
    break_overlay: bool = True
    blocker_enabled: bool = False
    blocked_hosts: list[str] = field(default_factory=list)

    daily_goal: int = 8
    autostart: bool = False
    first_run: bool = True

    # In-app shortcuts (QKeySequence strings, editable in Settings)
    shortcut_toggle: str = "Space"
    shortcut_skip: str = "N"
    shortcut_mini: str = "M"

    def path(self) -> Path:
        return _config_path()

    @classmethod
    def load(cls) -> "Settings":
        p = _config_path()
        if not p.exists():
            return cls()
        try:
            data = json.loads(p.read_text())
        except (OSError, ValueError):
            return cls()
        valid = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in data.items() if k in valid})

    def save(self) -> None:
        p = self.path()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(asdict(self), indent=2))
