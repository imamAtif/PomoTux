"""Onboarding, settings, break overlay. Kept in one module (all small QDialogs)."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import (QCheckBox, QColorDialog, QComboBox, QDialog, QDialogButtonBox,
                               QFileDialog, QFormLayout, QHBoxLayout, QKeySequenceEdit,
                               QLabel, QLineEdit, QPushButton, QSpinBox, QVBoxLayout,
                               QWidget)

from . import platform_linux as plat
from .config import Settings


class OnboardingDialog(QDialog):
    """First-run opt-ins. Everything off except break overlay."""

    def __init__(self, s: Settings, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Welcome to PomoTux")
        self.setModal(True)
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel("<h2>🐧 Welcome to PomoTux</h2>"))
        lay.addWidget(QLabel("Choose what you want. All can be changed later in Settings."))
        self.cb_dnd = QCheckBox("Auto Do-Not-Disturb during focus (GNOME)")
        self.cb_block = QCheckBox("Enable website blocker (hosts list, editable later)")
        self.cb_overlay = QCheckBox("Fullscreen break reminder")
        self.cb_overlay.setChecked(s.break_overlay)
        self.cb_hosts = QLineEdit("youtube.com, x.com, instagram.com")
        self.cb_hosts.setPlaceholderText("comma-separated hosts (only if blocker on)")
        for w in (self.cb_dnd, self.cb_block, self.cb_overlay, self.cb_hosts):
            lay.addWidget(w)
        btns = QDialogButtonBox(QDialogButtonBox.Ok)
        btns.button(QDialogButtonBox.Ok).setText("Start focusing")
        btns.accepted.connect(self.accept)
        lay.addWidget(btns)

    def apply(self, s: Settings):
        s.dnd = self.cb_dnd.isChecked()
        s.blocker_enabled = self.cb_block.isChecked()
        if s.blocker_enabled:
            s.blocked_hosts = [h.strip() for h in self.cb_hosts.text().split(",") if h.strip()]
        s.break_overlay = self.cb_overlay.isChecked()
        s.first_run = False


class SettingsDialog(QDialog):
    def __init__(self, s: Settings, store, parent=None):
        super().__init__(parent)
        self._s, self._store = s, store
        self.setWindowTitle("Settings")
        self.setMinimumWidth(380)
        lay, form = QVBoxLayout(self), QFormLayout()

        self.sp_focus = QSpinBox(minimum=1, maximum=180, value=s.focus_min)
        self.sp_short = QSpinBox(minimum=1, maximum=60, value=s.short_min)
        self.sp_long = QSpinBox(minimum=1, maximum=90, value=s.long_min)
        self.sp_every = QSpinBox(minimum=1, maximum=12, value=s.long_every)
        self.sp_goal = QSpinBox(minimum=1, maximum=32, value=s.daily_goal)
        form.addRow("Focus (min)", self.sp_focus)
        form.addRow("Short break (min)", self.sp_short)
        form.addRow("Long break (min)", self.sp_long)
        form.addRow("Long break every", self.sp_every)
        form.addRow("Daily goal", self.sp_goal)

        self.cmb_theme = QComboBox()
        self.cmb_theme.addItems(["auto", "dark", "light"])
        self.cmb_theme.setCurrentText(s.theme)
        self.btn_accent = QPushButton(s.accent)
        self.btn_accent.clicked.connect(self._pick_accent)
        form.addRow("Theme", self.cmb_theme)
        form.addRow("Accent", self.btn_accent)

        self.cb_sound = QCheckBox("Sound chime"); self.cb_sound.setChecked(s.sound)
        self.ed_break_sound = self._sound_row(form, "Break starts", s.break_sound, "break_start")
        self.ed_focus_sound = self._sound_row(form, "Focus starts", s.focus_sound, "focus_start")
        self.cb_notify = QCheckBox("Desktop notifications"); self.cb_notify.setChecked(s.notify)
        self.cb_tray = QCheckBox("Minimize to tray"); self.cb_tray.setChecked(s.minimize_to_tray)
        self.cb_dnd = QCheckBox("Auto Do-Not-Disturb"); self.cb_dnd.setChecked(s.dnd)
        self.cb_overlay = QCheckBox("Break overlay"); self.cb_overlay.setChecked(s.break_overlay)
        self.cb_auto = QCheckBox("Autostart on login"); self.cb_auto.setChecked(s.autostart)
        self.cb_ab = QCheckBox("Auto-start breaks"); self.cb_ab.setChecked(s.auto_start_breaks)
        self.cb_af = QCheckBox("Auto-start next focus"); self.cb_af.setChecked(s.auto_start_focus)
        for w in (self.cb_sound, self.cb_notify, self.cb_tray, self.cb_dnd,
                  self.cb_overlay, self.cb_auto, self.cb_ab, self.cb_af):
            form.addRow(w)

        self.key_toggle = QKeySequenceEdit(QKeySequence(s.shortcut_toggle))
        self.key_skip = QKeySequenceEdit(QKeySequence(s.shortcut_skip))
        self.key_mini = QKeySequenceEdit(QKeySequence(s.shortcut_mini))
        form.addRow("Shortcut: play/pause", self.key_toggle)
        form.addRow("Shortcut: skip", self.key_skip)
        form.addRow("Shortcut: mini mode", self.key_mini)

        self.ed_hosts = QLineEdit(", ".join(s.blocked_hosts))
        self.ed_hosts.setPlaceholderText("youtube.com, ... (asks for root on focus start)")
        form.addRow("Blocked hosts", self.ed_hosts)
        lay.addLayout(form)

        row = QHBoxLayout()
        self.btn_export = QPushButton("Export JSON")
        self.btn_import = QPushButton("Import JSON")
        self.btn_export.clicked.connect(self._export)
        self.btn_import.clicked.connect(self._import)
        row.addWidget(self.btn_export); row.addWidget(self.btn_import)
        lay.addLayout(row)

        btns = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept); btns.rejected.connect(self.reject)
        lay.addWidget(btns)

    def _sound_row(self, form: QFormLayout, label: str, current: str, fallback: str) -> QLineEdit:
        """Path field (empty = bundled chime) with Browse and preview."""
        box = QWidget()
        row = QHBoxLayout(box)
        row.setContentsMargins(0, 0, 0, 0)
        edit = QLineEdit(current, placeholderText="Bundled chime")
        browse = QPushButton("Browse")
        browse.clicked.connect(lambda: self._browse_sound(edit))
        preview = QPushButton("▶")
        preview.setFixedWidth(36)
        preview.clicked.connect(lambda: plat.play_alert(edit.text().strip(), fallback, True))
        row.addWidget(edit)
        row.addWidget(browse)
        row.addWidget(preview)
        form.addRow(label, box)
        return edit

    def _browse_sound(self, edit: QLineEdit):
        path, _ = QFileDialog.getOpenFileName(
            self, "Choose alert sound", filter="Audio (*.wav *.ogg *.oga *.mp3 *.flac)")
        if path:
            edit.setText(path)

    def _pick_accent(self):
        c = QColorDialog.getColor()
        if c.isValid():
            self.btn_accent.setText(c.name())

    def _export(self):
        dest, _ = QFileDialog.getSaveFileName(self, "Export backup", "pomotux-backup.json")
        if dest:
            self._store.export_json(Path(dest))

    def _import(self):
        src, _ = QFileDialog.getOpenFileName(self, "Import backup", filter="JSON (*.json)")
        if src:
            try:
                self._store.import_json(Path(src))
            except ValueError:
                pass  # keep silent-light: invalid file ignored

    def apply(self, s: Settings):
        s.focus_min, s.short_min = self.sp_focus.value(), self.sp_short.value()
        s.long_min, s.long_every = self.sp_long.value(), self.sp_every.value()
        s.daily_goal = self.sp_goal.value()
        s.theme = self.cmb_theme.currentText()
        s.accent = self.btn_accent.text()
        s.sound = self.cb_sound.isChecked()
        s.break_sound = self.ed_break_sound.text().strip()
        s.focus_sound = self.ed_focus_sound.text().strip()
        s.notify = self.cb_notify.isChecked()
        s.minimize_to_tray = self.cb_tray.isChecked()
        s.dnd = self.cb_dnd.isChecked()
        s.break_overlay = self.cb_overlay.isChecked()
        s.autostart = self.cb_auto.isChecked()
        s.auto_start_breaks = self.cb_ab.isChecked()
        s.auto_start_focus = self.cb_af.isChecked()
        for attr, edit in (("shortcut_toggle", self.key_toggle),
                           ("shortcut_skip", self.key_skip),
                           ("shortcut_mini", self.key_mini)):
            seq = edit.keySequence().toString()
            if seq:
                setattr(s, attr, seq)
        s.blocked_hosts = [h.strip() for h in self.ed_hosts.text().split(",") if h.strip()]
        s.blocker_enabled = bool(s.blocked_hosts)


class BreakOverlay(QDialog):
    """Fullscreen break reminder. Esc / button dismisses."""

    def __init__(self, text: str, parent=None):
        super().__init__(parent, Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.setModal(False)
        self.setWindowState(Qt.WindowFullScreen)
        lay = QVBoxLayout(self)
        lay.setAlignment(Qt.AlignCenter)
        msg = QLabel(f"<h1>🐧 {text}</h1><p>Stand up · water · look away</p>")
        msg.setAlignment(Qt.AlignCenter)
        btn = QPushButton("Back to PomoTux")
        btn.setObjectName("primary")
        btn.clicked.connect(self.close)
        lay.addWidget(msg); lay.addWidget(btn, alignment=Qt.AlignCenter)
