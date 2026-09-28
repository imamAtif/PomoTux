"""Full dashboard window: timer + tasks + stats + tray."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QIcon, QShortcut, QKeySequence
from PySide6.QtWidgets import (QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
                               QMainWindow, QMenu, QPushButton,
                               QSystemTrayIcon, QTabWidget, QVBoxLayout, QWidget,
                               QLineEdit, QProgressBar)

from . import platform_linux as plat
from .config import Settings
from .dialogs import BreakOverlay, SettingsDialog
from .store import Store
from .theme import build_qss, is_dark
from .timer import LABELS, Phase, PomodoroTimer
from .widgets import TimerRing, WeekBars, fmt


class MainWindow(QMainWindow):
    def __init__(self, timer: PomodoroTimer, store: Store, s: Settings):
        super().__init__()
        self.timer, self.store, self.s = timer, store, s
        self.mini_cb = None  # set by main.py
        self._task_id: int | None = None
        self._dark = True
        self.setWindowTitle("PomoTux")
        self.resize(460, 720)

        root = QWidget(objectName="root")
        self.setCentralWidget(root)
        lay = QVBoxLayout(root)
        lay.setContentsMargins(20, 16, 20, 16)
        lay.setSpacing(12)

        # header
        head = QHBoxLayout()
        title = QLabel("🐧 PomoTux", objectName="title")
        head.addWidget(title)
        head.addStretch()
        self.btn_mini = QPushButton("Mini")
        self.btn_mini.setObjectName("ghost")
        self.btn_mini.clicked.connect(self._to_mini)
        self.btn_settings = QPushButton("⚙")
        self.btn_settings.setObjectName("ghost")
        self.btn_settings.clicked.connect(self._open_settings)
        head.addWidget(self.btn_mini); head.addWidget(self.btn_settings)
        lay.addLayout(head)

        # mode switch
        modes = QHBoxLayout()
        self.mode_btns = {}
        for ph in (Phase.FOCUS, Phase.SHORT, Phase.LONG):
            b = QPushButton(LABELS[ph])
            b.setCheckable(True)
            b.clicked.connect(lambda _=False, p=ph: timer.set_phase(p))
            modes.addWidget(b)
            self.mode_btns[ph] = b
        lay.addLayout(modes)

        # ring card
        card = QWidget(objectName="card")
        cl = QVBoxLayout(card)
        cl.setAlignment(Qt.AlignCenter)
        self.ring = TimerRing(accent=s.accent)
        self.lbl_state = QLabel(objectName="title")
        self.lbl_state.setAlignment(Qt.AlignCenter)
        self.lbl_task = QLabel("No task selected", objectName="muted")
        self.lbl_task.setAlignment(Qt.AlignCenter)
        cl.addWidget(self.ring, alignment=Qt.AlignCenter)
        cl.addWidget(self.lbl_state)
        cl.addWidget(self.lbl_task)
        lay.addWidget(card)

        # controls
        ctrls = QHBoxLayout()
        self.btn_main = QPushButton("Start", objectName="primary")
        self.btn_main.clicked.connect(timer.toggle)
        self.btn_reset = QPushButton("Reset")
        self.btn_reset.clicked.connect(timer.reset)
        self.btn_skip = QPushButton("Skip →")
        self.btn_skip.clicked.connect(timer.skip)
        ctrls.addWidget(self.btn_main)
        ctrls.addWidget(self.btn_reset)
        ctrls.addWidget(self.btn_skip)
        lay.addLayout(ctrls)

        # tabs
        self.tabs = QTabWidget()
        self.tabs.addTab(self._tasks_tab(), "Tasks")
        self.tabs.addTab(self._stats_tab(), "Stats")
        lay.addWidget(self.tabs, stretch=1)

        self._tray()
        self._shortcuts()
        self._sites_blocked = False
        self._block_nagged = False
        timer.ticked.connect(self._on_tick)
        timer.phase_changed.connect(self._on_phase)
        timer.finished.connect(self._on_finished)
        timer.started.connect(self._on_started)
        self._on_phase(timer.phase.value)
        self._on_tick(timer.remaining, timer.phase.value)
        self.refresh_tasks()
        self.refresh_stats()
        self.apply_theme()
        self._heal_stale_block()

    # -- tabs -------------------------------------------------------------
    def _tasks_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        row = QHBoxLayout()
        self.ed_task = QLineEdit(placeholderText="New task… (Enter to add)")
        self.ed_task.returnPressed.connect(self._add_task)
        btn = QPushButton("Add")
        btn.clicked.connect(self._add_task)
        row.addWidget(self.ed_task); row.addWidget(btn)
        lay.addLayout(row)
        self.task_list = QListWidget()
        self.task_list.itemChanged.connect(self._task_toggled)
        self.task_list.currentRowChanged.connect(self._task_selected)
        lay.addWidget(self.task_list)
        del_row = QHBoxLayout()
        self.btn_del = QPushButton("Delete selected")
        self.btn_del.setObjectName("ghost")
        self.btn_del.clicked.connect(self._del_task)
        del_row.addStretch(); del_row.addWidget(self.btn_del)
        lay.addLayout(del_row)
        return w

    def _stats_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        self.lbl_today = QLabel()
        self.bar_goal = QProgressBar(maximum=100)
        self.bars = WeekBars(accent=self.s.accent)
        self.lbl_streak = QLabel(objectName="muted")
        lay.addWidget(self.lbl_today)
        lay.addWidget(self.bar_goal)
        lay.addWidget(QLabel("Last 7 days (focus sessions)"))
        lay.addWidget(self.bars)
        lay.addWidget(self.lbl_streak)
        lay.addStretch()
        return w

    # -- tray / shortcuts -------------------------------------------------
    def _tray(self):
        icon = QIcon.fromTheme("appointment")
        if icon.isNull():  # fallback when no icon theme (e.g. offscreen tests)
            from PySide6.QtGui import QPixmap
            px = QPixmap(32, 32)
            px.fill(Qt.darkYellow)
            icon = QIcon(px)
        self.tray = QSystemTrayIcon(icon, self)
        menu = QMenu()
        for label, fn in (("Show/Hide", self._toggle_vis),
                          ("Start/Pause", self.timer.toggle),
                          ("Skip", self.timer.skip),
                          ("Quit", self.close_app)):
            a = QAction(label, self)
            a.triggered.connect(fn)
            menu.addAction(a)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(
            lambda r: self._toggle_vis() if r == QSystemTrayIcon.Trigger else None)
        self.tray.show()

    def _shortcuts(self):
        for attr, fn in (("shortcut_toggle", self.timer.toggle),
                         ("shortcut_skip", self.timer.skip),
                         ("shortcut_mini", self._to_mini)):
            sc = QShortcut(QKeySequence(getattr(self.s, attr)), self)
            sc.setContext(Qt.ApplicationShortcut)
            sc.activated.connect(fn)
        self._shortcut_objs = self.findChildren(QShortcut)  # keep refs via parent

    def _reload_shortcuts(self):
        for sc in self.findChildren(QShortcut):
            sc.deleteLater()
        self._shortcuts()

    # -- timer slots ------------------------------------------------------
    def _on_tick(self, sec: int, _phase: str):
        self.ring.set_state(sec, self.timer.progress, paused=not self.timer.running)
        name = LABELS[self.timer.phase]
        state = "" if self.timer.running else " (paused)"
        self.tray.setToolTip(f"PomoTux: {name} {fmt(sec)}{state}")
        self.btn_main.setText("Pause" if self.timer.running else "Start")
        self._refresh_state()

    def _refresh_state(self):
        t = self.timer
        if t.running:
            text = {"focus": "Focusing", "short": "On short break",
                    "long": "On long break"}[t.phase.value]
        elif t.remaining >= t.total:
            text = "Ready"
        else:
            text = "Paused"
        self.lbl_state.setText(text)

    def _on_phase(self, phase: str):
        for ph, b in self.mode_btns.items():
            b.setChecked(ph.value == phase)
        self._refresh_state()
        self._block_nagged = False
        if phase != Phase.FOCUS.value and self._sites_blocked:
            plat.set_hosts_blocked(self.s.blocked_hosts, False)
            self._sites_blocked = False

    def _on_started(self):
        # Entering focus run: enforce the site block (prompts for root
        # only when the hosts file actually needs changing).
        if (self.timer.phase == Phase.FOCUS and self.s.blocker_enabled
                and self.s.blocked_hosts and not self._sites_blocked):
            self._sites_blocked = plat.set_hosts_blocked(self.s.blocked_hosts, True)
            if not self._sites_blocked and not self._block_nagged:
                self._block_nagged = True
                plat.notify(self.tray, "PomoTux",
                            "Website blocker needs authorization: sites not blocked",
                            self.s.notify)

    def _on_finished(self, kind: str):
        # log focus sessions (+1 on linked task)
        if kind == Phase.FOCUS.value:
            self.store.log_session(kind, self.timer.durations[Phase.FOCUS], self._task_id)
            if self._task_id:
                self.store.bump_pomodoros(self._task_id)
        else:
            self.store.log_session(kind, 60, None)
        self.refresh_stats()
        if kind == "focus":
            plat.play_alert(self.s.break_sound, "break_start", self.s.sound)
            plat.notify(self.tray, "PomoTux", "Focus done: break time",
                        self.s.notify)
        else:
            plat.play_alert(self.s.focus_sound, "focus_start", self.s.sound)
            plat.notify(self.tray, "PomoTux", "Break over: back to it!",
                        self.s.notify)
        # DND only during focus
        plat.set_dnd(self.s.dnd and self.timer.phase != Phase.FOCUS)
        if kind == "focus" and self.s.break_overlay:
            self.present()
            BreakOverlay("Break time!", self).exec()
            self.present()
        # auto-start chain
        if kind == "focus" and self.s.auto_start_breaks:
            self.timer.start()
        elif kind != "focus" and self.s.auto_start_focus:
            self.timer.start()

    # -- tasks ------------------------------------------------------------
    def refresh_tasks(self):
        self.task_list.blockSignals(True)
        self.task_list.clear()
        for t in self.store.list_tasks(include_done=True):
            it = QListWidgetItem(f"{'✓ ' if t.done else ''}{t.title}  ({t.pomodoros}🍅)")
            it.setData(Qt.UserRole, t.id)
            it.setFlags(it.flags() | Qt.ItemIsUserCheckable)
            it.setCheckState(Qt.Checked if t.done else Qt.Unchecked)
            self.task_list.addItem(it)
        self.task_list.blockSignals(False)
        self._update_task_label()

    def _add_task(self):
        try:
            self.store.add_task(self.ed_task.text())
        except ValueError:
            return
        self.ed_task.clear()
        self.refresh_tasks()

    def _task_toggled(self, item: QListWidgetItem):
        self.store.toggle_task(item.data(Qt.UserRole))
        self.refresh_tasks()

    def _task_selected(self, row: int):
        it = self.task_list.item(row)
        self._task_id = it.data(Qt.UserRole) if it else None
        self._update_task_label()

    def _del_task(self):
        it = self.task_list.currentItem()
        if it:
            self.store.delete_task(it.data(Qt.UserRole))
            self._task_id = None
            self.refresh_tasks()

    def _update_task_label(self):
        t = self.store.get_task(self._task_id) if self._task_id else None
        self.lbl_task.setText(f"🎯 {t.title}" if t else "No task selected")

    # -- stats ------------------------------------------------------------
    def refresh_stats(self):
        today = self.store.today_focus()
        self.lbl_today.setText(f"Today: {today} / {self.s.daily_goal} pomodoros")
        self.bar_goal.setValue(min(100, int(today / max(1, self.s.daily_goal) * 100)))
        self.bars.set_values(self.store.focus_last_7_days(), self._dark)
        self.lbl_streak.setText(f"🔥 {self.store.streak_days()}-day streak")

    # -- misc -------------------------------------------------------------
    def apply_theme(self):
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance()
        self._dark = is_dark(app, self.s.theme)
        app.setStyleSheet(build_qss(self._dark, self.s.accent))
        self.ring.set_accent(self.s.accent)
        self.ring.set_dark(self._dark)
        self.bars.set_accent(self.s.accent)
        self.refresh_stats()

    def _open_settings(self):
        dlg = SettingsDialog(self.s, self.store, self)
        if dlg.exec():
            old_hosts = list(self.s.blocked_hosts)
            dlg.apply(self.s)
            self.s.save()
            plat.set_autostart(self.s.autostart)
            self.timer.set_minutes(self.s.focus_min, self.s.short_min,
                                   self.s.long_min, self.s.long_every)
            self._reload_shortcuts()
            self.apply_theme()
            self.refresh_stats()
            # Re-apply the block if the host list changed mid-focus.
            if self._sites_blocked:
                plat.set_hosts_blocked(old_hosts, False)
                self._sites_blocked = False
            if self.timer.running:
                self._on_started()

    def _to_mini(self):
        if self.mini_cb:
            self.mini_cb()

    def _toggle_vis(self):
        self.setVisible(not self.isVisible())

    def present(self):
        """Bring the dashboard forward (second launch wakes the first)."""
        self.show()
        self.raise_()
        self.activateWindow()

    def close_app(self):
        self._clear_block_or_warn()
        plat.set_dnd(False)
        self.tray.hide()
        from PySide6.QtWidgets import QApplication
        QApplication.quit()

    def _clear_block_or_warn(self) -> bool:
        """Remove any managed block. Warns loudly when root is denied."""
        # No-op (no prompt) when the file is already clean.
        removed = plat.set_hosts_blocked([], False)
        self._sites_blocked = self._sites_blocked and not removed
        if removed or not plat.has_managed_block():
            return True
        plat.notify(self.tray, "PomoTux",
                    "Website block still active (needs root). "
                    f"Remove it with: {plat.MANUAL_UNBLOCK}", True)
        return False

    def _heal_stale_block(self):
        # A kill mid-focus can strand the block. Clear it at launch unless
        # the blocker is on (next focus start then manages it deterministically).
        if (self.s.blocker_enabled and self.s.blocked_hosts) \
                or not plat.has_managed_block():
            return
        plat.notify(self.tray, "PomoTux",
                    "Removing leftover website block: authorization needed", True)
        self._clear_block_or_warn()

    def closeEvent(self, e):
        if self.s.minimize_to_tray and self.tray.isVisible():
            self.hide()
            e.ignore()
        else:
            self.close_app()
            e.accept()
