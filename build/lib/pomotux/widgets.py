"""Custom painted widgets: progress ring + 7-day bars. No extra deps."""
from __future__ import annotations

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QWidget


def fmt(sec: int) -> str:
    return f"{sec // 60:02d}:{sec % 60:02d}"


class TimerRing(QWidget):
    """Circular progress with centered MM:SS. Set via set_state()."""

    def __init__(self, size=280, accent="#F2B705", parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self._progress = 0.0
        self._sec = 25 * 60
        self._accent = QColor(accent)
        self._dark = True

    def set_state(self, sec: int, progress: float):
        self._sec, self._progress = sec, progress
        self.update()

    def set_accent(self, accent: str):
        self._accent = QColor(accent)
        self.update()

    def set_dark(self, dark: bool):
        self._dark = dark
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        track = QColor("#2C313B") if self._dark else QColor("#E5E7EB")
        rect = QRectF(18, 18, self.width() - 36, self.height() - 36)

        p.setPen(QPen(track, 14, Qt.SolidLine, Qt.RoundCap))
        p.drawEllipse(rect)
        if self._progress > 0:
            p.setPen(QPen(self._accent, 14, Qt.SolidLine, Qt.RoundCap))
            # -90° = top; Qt spans clockwise in 1/16°
            p.drawArc(rect, -90 * 16, -int(self._progress * 360 * 16))

        p.setPen(self._accent if self._dark else QColor("#17181C"))
        p.setFont(QFont("Inter, Ubuntu", 40, QFont.Bold))
        p.drawText(self.rect(), Qt.AlignCenter, fmt(self._sec))


class WeekBars(QWidget):
    """7 vertical bars for focus counts. values oldest→newest."""

    def __init__(self, accent="#F2B705", parent=None):
        super().__init__(parent)
        self.setMinimumHeight(120)
        self._vals = [0] * 7
        self._accent = QColor(accent)
        self._dark = True

    def set_values(self, vals: list[int], dark: bool):
        self._vals, self._dark = list(vals), dark
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        n, w, h = 7, self.width(), self.height()
        mx = max(1, max(self._vals))
        bw = min(34, w // (n * 2))
        muted = QColor("#9AA0AE")
        p.setFont(QFont("Inter, Ubuntu", 9))
        for i, v in enumerate(self._vals):
            x = int((i + 0.5) * w / n - bw / 2)
            bh = int((h - 34) * v / mx) if v else 4
            y = h - 22 - bh
            p.setPen(Qt.NoPen)
            p.setBrush(self._accent if v else QColor("#2C313B" if self._dark else "#E5E7EB"))
            p.drawRoundedRect(x, y, bw, bh, 6, 6)
            p.setPen(muted)
            p.drawText(x - 12, h - 18, bw + 24, 16, Qt.AlignCenter, str(v))
