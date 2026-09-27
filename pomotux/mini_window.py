"""Frameless always-on-top mini player."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from .timer import LABELS, PomodoroTimer
from .widgets import TimerRing, fmt


class MiniWindow(QWidget):
    def __init__(self, timer: PomodoroTimer, accent: str):
        super().__init__(None, Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Tool)
        self.timer = timer
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(220, 300)
        self.expand_cb = None

        lay = QVBoxLayout(self)
        lay.setAlignment(Qt.AlignCenter)
        self.ring = TimerRing(size=170, accent=accent)
        self.lbl = QLabel(LABELS[timer.phase], objectName="muted")
        self.lbl.setAlignment(Qt.AlignCenter)
        lay.addWidget(self.ring, alignment=Qt.AlignCenter)
        lay.addWidget(self.lbl)

        row = QHBoxLayout()
        self.btn_play = QPushButton("⏸" if timer.running else "▶", objectName="primary")
        self.btn_play.setFixedWidth(64)
        self.btn_play.clicked.connect(timer.toggle)
        self.btn_skip = QPushButton("⏭")
        self.btn_skip.clicked.connect(timer.skip)
        self.btn_expand = QPushButton("⛶", objectName="ghost")
        self.btn_expand.clicked.connect(lambda: self.expand_cb() if self.expand_cb else None)
        row.addWidget(self.btn_play); row.addWidget(self.btn_skip); row.addWidget(self.btn_expand)
        lay.addLayout(row)

        timer.ticked.connect(self._tick)
        timer.phase_changed.connect(lambda p: self.lbl.setText(LABELS[timer.phase]))
        self._tick(timer.remaining, timer.phase.value)

        # drag to move (frameless)
        self._drag = None

    def _tick(self, sec: int, _p: str):
        self.ring.set_state(sec, self.timer.progress)
        self.btn_play.setText("⏸" if self.timer.running else "▶")
        self.setWindowTitle(f"PomoTux {fmt(sec)}")

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._drag = e.globalPosition().toPoint() - self.pos()

    def mouseMoveEvent(self, e):
        if self._drag is not None:
            self.move(e.globalPosition().toPoint() - self._drag)

    def mouseReleaseEvent(self, _):
        self._drag = None
