"""QSS theme builder. Auto mode follows Qt's color scheme hint."""
from __future__ import annotations

from PySide6.QtWidgets import QApplication


def is_dark(app: QApplication, pref: str) -> bool:
    if pref == "dark":
        return True
    if pref == "light":
        return False
    # auto: Qt 6.5+ exposes colorScheme; fall back to palette luminance
    try:
        from PySide6.QtCore import Qt
        scheme = app.styleHints().colorScheme()
        return scheme == Qt.ColorScheme.Dark
    except Exception:
        bg = app.palette().window().color()
        return (bg.red() * 0.299 + bg.green() * 0.587 + bg.blue() * 0.114) < 128


def build_qss(dark: bool, accent: str) -> str:
    bg = "#14161B" if dark else "#F4F4F6"
    card = "#1E2128" if dark else "#FFFFFF"
    text = "#F2F3F5" if dark else "#17181C"
    muted = "#9AA0AE" if dark else "#6B7280"
    border = "#2C313B" if dark else "#E5E7EB"
    return f"""
    * {{ font-family: 'Inter', 'Ubuntu', 'Cantarell', sans-serif; }}
    QMainWindow, QWidget#root {{ background: {bg}; color: {text}; }}
    QWidget#card {{ background: {card}; border: 1px solid {border}; border-radius: 16px; }}
    QLabel#title {{ font-size: 20px; font-weight: 800; }}
    QLabel#muted {{ color: {muted}; }}
    QLabel#time {{ font-size: 44px; font-weight: 800; letter-spacing: 1px; }}
    QPushButton {{ border: 1px solid {border}; border-radius: 12px; padding: 9px 16px;
                  background: {card}; color: {text}; font-weight: 600; }}
    QPushButton:hover {{ border-color: {accent}; }}
    QPushButton#primary {{ background: {accent}; color: #14161B; border: none;
                           font-size: 15px; padding: 11px 22px; }}
    QPushButton#ghost {{ background: transparent; border: none; color: {muted}; }}
    QLineEdit, QSpinBox {{ background: {card}; border: 1px solid {border};
                           border-radius: 10px; padding: 8px 10px; color: {text}; }}
    QTabWidget::pane {{ border: none; }}
    QTabBar::tab {{ padding: 8px 18px; margin-right: 6px; border-radius: 10px;
                    color: {muted}; background: transparent; }}
    QTabBar::tab:selected {{ color: {text}; background: {card};
                             border: 1px solid {border}; }}
    QCheckBox, QListWidget {{ color: {text}; }}
    QListWidget {{ background: transparent; border: none; font-size: 14px; }}
    QToolTip {{ background: {card}; color: {text}; border: 1px solid {border}; }}
    """
