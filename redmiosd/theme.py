from __future__ import annotations

from PyQt6.QtGui import QColor, QFont, QFontDatabase

ACCENT = "#FF6A2B"
ACCENT_HOVER = "#FF7F47"
TEXT = "#F2F4F7"
TEXT_SOFT = "#C7CCD6"
MUTED = "#8A92A1"
FAINT = "#656D7B"
SURFACE = "#15171C"
BORDER = "#2A2E37"
SUCCESS = "#5BD6A2"
WARNING = "#FFB020"
DANGER = "#FF6B6B"

_families = ["Segoe UI"]


def setup_fonts(app):
    global _families
    available = set(QFontDatabase.families())
    ordered = [
        name for name in ("Segoe UI", "Microsoft YaHei UI", "Microsoft YaHei")
        if name in available
    ]
    if not ordered:
        ordered = ["Segoe UI"]
    _families = ordered
    font = QFont()
    font.setFamilies(ordered)
    font.setPixelSize(13)
    app.setFont(font)


def font(size: int, weight: QFont.Weight = QFont.Weight.Normal) -> QFont:
    f = QFont()
    f.setFamilies(_families)
    f.setPixelSize(size)
    f.setWeight(weight)
    return f


def color(value: str, alpha: int = 255) -> QColor:
    c = QColor(value)
    c.setAlpha(alpha)
    return c


QSS = f"""
QWidget {{
    color: {TEXT};
    background: transparent;
}}
QToolTip {{
    background: #1C1F26;
    color: #D6DAE2;
    border: 1px solid #2A2E37;
    border-radius: 6px;
    padding: 6px 8px;
    font-size: 12px;
}}
QFrame#panel {{
    background: rgba(20, 22, 27, 0.985);
    border: 1px solid rgba(255, 255, 255, 0.075);
    border-radius: 18px;
}}
QLabel#appTitle {{
    font-size: 15px;
    font-weight: 600;
    color: {TEXT};
}}
QLabel#appSubtitle {{
    font-size: 11px;
    color: {MUTED};
}}
QLabel#inputBadge {{
    background: rgba(255, 106, 43, 0.13);
    color: #FFA175;
    border: 1px solid rgba(255, 106, 43, 0.26);
    border-radius: 7px;
    padding: 2px 8px;
    font-size: 10px;
    font-weight: 600;
}}
QPushButton#winBtn {{
    background: transparent;
    border: none;
    border-radius: 7px;
    color: {MUTED};
    font-size: 13px;
    padding: 0;
}}
QPushButton#winBtn:hover {{
    background: rgba(255, 255, 255, 0.08);
    color: {TEXT};
}}
QPushButton#winBtn[close="true"]:hover {{
    background: rgba(255, 92, 92, 0.18);
    color: #FF9A9A;
}}
QPushButton#tab {{
    background: transparent;
    border: none;
    border-bottom: 2px solid transparent;
    color: {MUTED};
    font-size: 13px;
    font-weight: 600;
    padding: 7px 0 9px 0;
}}
QPushButton#tab:hover {{
    color: {TEXT_SOFT};
}}
QPushButton#tab:checked {{
    color: {TEXT};
    border-bottom: 2px solid {ACCENT};
}}
QFrame#divider {{
    background: rgba(255, 255, 255, 0.06);
    border: none;
    min-height: 1px;
    max-height: 1px;
}}
QLabel#metricLabel {{
    font-size: 13px;
    color: {TEXT_SOFT};
}}
QLabel#metricLabel:disabled {{
    color: #5F6672;
}}
QLabel#metricValue {{
    font-size: 14px;
    font-weight: 600;
    color: {TEXT};
}}
QLabel#metricValue:disabled {{
    color: #5F6672;
}}
QLabel#sectionLabel {{
    font-size: 11px;
    font-weight: 600;
    color: {FAINT};
}}
QLabel#hintLabel {{
    font-size: 11px;
    color: {FAINT};
}}
QLabel#statusLabel {{
    font-size: 11px;
    color: {MUTED};
}}
QPushButton#retryBtn {{
    background: transparent;
    border: none;
    color: #FFA175;
    font-size: 11px;
    font-weight: 600;
    padding: 0 2px;
}}
QPushButton#retryBtn:hover {{
    color: #FFC2A3;
}}
QPushButton#linkBtn {{
    background: transparent;
    border: none;
    color: #FFA175;
    font-size: 11px;
    font-weight: 600;
    padding: 0 4px;
}}
QPushButton#linkBtn:hover {{
    color: #FFC2A3;
}}
QPushButton#chip {{
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 9px;
    color: #B7BDC8;
    font-size: 12px;
    font-weight: 600;
    min-height: 34px;
    padding: 0 10px;
}}
QPushButton#chip:hover {{
    background: rgba(255, 255, 255, 0.085);
    color: {TEXT};
}}
QPushButton#chip:checked {{
    background: rgba(255, 106, 43, 0.15);
    border: 1px solid rgba(255, 106, 43, 0.62);
    color: #FFA175;
}}
QPushButton#actionBtn {{
    background: rgba(255, 255, 255, 0.045);
    border: 1px solid rgba(255, 255, 255, 0.07);
    border-radius: 10px;
    color: #D8DCE4;
    font-size: 12px;
    font-weight: 600;
    min-height: 36px;
    padding: 0 14px;
}}
QPushButton#actionBtn:hover {{
    background: rgba(255, 255, 255, 0.075);
    border: 1px solid rgba(255, 255, 255, 0.10);
}}
QPushButton#actionBtn[armed="true"] {{
    background: rgba(255, 176, 32, 0.10);
    border: 1px solid rgba(255, 176, 32, 0.55);
    color: #FFCA70;
}}
QPushButton#quitBtn {{
    background: transparent;
    border: none;
    border-radius: 9px;
    color: {FAINT};
    font-size: 12px;
    min-height: 34px;
}}
QPushButton#quitBtn:hover {{
    background: rgba(255, 92, 92, 0.10);
    color: #FF9A9A;
}}
QLabel#keycap {{
    background: rgba(255, 255, 255, 0.065);
    border: 1px solid rgba(255, 255, 255, 0.09);
    border-radius: 5px;
    color: #AEB4BF;
    font-size: 10px;
    padding: 2px 6px;
}}
QSlider {{
    min-height: 22px;
}}
QSlider::groove:horizontal {{
    height: 6px;
    border-radius: 3px;
    background: rgba(255, 255, 255, 0.09);
}}
QSlider::sub-page:horizontal {{
    border-radius: 3px;
    background: {ACCENT};
}}
QSlider::handle:horizontal {{
    width: 18px;
    height: 18px;
    margin: -6px 0;
    border-radius: 9px;
    background: #F5F6F8;
}}
QSlider::handle:horizontal:hover {{
    background: #FFFFFF;
}}
QSlider::handle:horizontal:pressed {{
    background: #FFD8C6;
}}
QSlider::groove:horizontal:disabled {{
    background: rgba(255, 255, 255, 0.05);
}}
QSlider::sub-page:horizontal:disabled {{
    background: rgba(255, 255, 255, 0.15);
}}
QSlider::handle:horizontal:disabled {{
    background: #444A56;
}}
"""
