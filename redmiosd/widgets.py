from __future__ import annotations

import math

from PyQt6.QtCore import (
    QEasingCurve, QPointF, QPropertyAnimation, QRectF, Qt, QTimer,
    pyqtProperty, pyqtSignal,
)
from PyQt6.QtGui import (
    QColor, QFont, QIcon, QLinearGradient, QPainter, QPen, QPixmap,
)
from PyQt6.QtWidgets import (
    QAbstractButton, QApplication, QHBoxLayout, QLabel, QPushButton,
    QSizePolicy, QSlider, QStyle, QStyleOptionSlider, QVBoxLayout, QWidget,
)

from . import theme


def logo_pixmap(size: int = 64) -> QPixmap:
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    inset = size * 0.06
    rect = QRectF(inset, inset, size - inset * 2, size - inset * 2)
    grad = QLinearGradient(rect.topLeft(), rect.bottomRight())
    grad.setColorAt(0.0, QColor("#FF8447"))
    grad.setColorAt(1.0, QColor("#F4561B"))
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(grad)
    p.drawRoundedRect(rect, size * 0.28, size * 0.28)

    white = QColor("#FFFFFF")
    pen = QPen(white, max(1.4, size * 0.055))
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    screen = QRectF(size * 0.26, size * 0.31, size * 0.48, size * 0.31)
    p.drawRoundedRect(screen, size * 0.045, size * 0.045)
    p.drawLine(QPointF(size * 0.5, size * 0.62), QPointF(size * 0.5, size * 0.70))
    p.drawLine(QPointF(size * 0.39, size * 0.70), QPointF(size * 0.61, size * 0.70))
    p.end()
    return pm


def app_icon() -> QIcon:
    icon = QIcon()
    for size in (16, 24, 32, 48, 64, 128, 256):
        icon.addPixmap(logo_pixmap(size))
    return icon


class IconWidget(QWidget):
    def __init__(self, kind: str, color: str = theme.MUTED, size: int = 20, parent=None):
        super().__init__(parent)
        self.kind = kind
        self._color = QColor(color)
        self.setFixedSize(size, size)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

    def set_color(self, value: str):
        self._color = QColor(value)
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        scale = self.width() / 20.0
        p.scale(scale, scale)
        draw_color = QColor(self._color)
        if not self.isEnabled():
            draw_color = QColor(theme.FAINT)
            draw_color.setAlpha(150)
        pen = QPen(draw_color, 1.55)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        c = QPointF(10, 10)

        if self.kind == "sun":
            p.drawEllipse(c, 3.3, 3.3)
            for i in range(8):
                angle = i * math.pi / 4
                inner = QPointF(10 + math.cos(angle) * 6.0, 10 + math.sin(angle) * 6.0)
                outer = QPointF(10 + math.cos(angle) * 8.1, 10 + math.sin(angle) * 8.1)
                p.drawLine(inner, outer)
        elif self.kind == "contrast":
            p.drawEllipse(c, 6.8, 6.8)
            p.setBrush(draw_color)
            p.setPen(Qt.PenStyle.NoPen)
            p.drawPie(QRectF(3.2, 3.2, 13.6, 13.6), 90 * 16, 180 * 16)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(pen)
            p.drawEllipse(c, 6.8, 6.8)
        elif self.kind == "volume":
            p.setBrush(draw_color)
            p.setPen(Qt.PenStyle.NoPen)
            p.drawPolygon([
                QPointF(3.2, 8.0), QPointF(6.2, 8.0), QPointF(9.6, 5.0),
                QPointF(9.6, 15.0), QPointF(6.2, 12.0), QPointF(3.2, 12.0),
            ])
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(pen)
            p.drawArc(QRectF(8.0, 6.2, 5.0, 7.6), -55 * 16, 110 * 16)
            p.drawArc(QRectF(8.0, 3.6, 8.4, 12.8), -50 * 16, 100 * 16)
        elif self.kind == "sliders":
            for y, x in ((5.0, 13.0), (10.0, 7.0), (15.0, 11.0)):
                p.drawLine(QPointF(3.0, y), QPointF(17.0, y))
                p.setBrush(QColor("#15171C"))
                p.drawEllipse(QPointF(x, y), 2.0, 2.0)
                p.setBrush(Qt.BrushStyle.NoBrush)
        elif self.kind in ("r", "g", "b"):
            p.setPen(draw_color)
            p.setFont(theme.font(11, QFont.Weight.DemiBold))
            p.drawText(
                QRectF(0, 0, 20, 20),
                int(Qt.AlignmentFlag.AlignCenter),
                self.kind.upper(),
            )
        elif self.kind == "keyboard":
            p.drawRoundedRect(QRectF(2.5, 5.5, 15.0, 9.0), 2.2, 2.2)
            for x in (5.5, 8.0, 10.5, 13.0):
                p.drawPoint(QPointF(x, 8.5))
            p.drawLine(QPointF(6.0, 11.8), QPointF(14.0, 11.8))
        p.end()


class JumpSlider(QSlider):
    def __init__(self, parent=None):
        super().__init__(Qt.Orientation.Horizontal, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def _value_at(self, x: float) -> int:
        opt = QStyleOptionSlider()
        self.initStyleOption(opt)
        style = self.style()
        groove = style.subControlRect(
            QStyle.ComplexControl.CC_Slider, opt, QStyle.SubControl.SC_SliderGroove, self,
        )
        handle = style.subControlRect(
            QStyle.ComplexControl.CC_Slider, opt, QStyle.SubControl.SC_SliderHandle, self,
        )
        span = max(1, groove.width() - handle.width())
        pos = int(x - groove.x() - handle.width() / 2)
        return QStyle.sliderValueFromPosition(self.minimum(), self.maximum(), pos, span)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.isEnabled():
            self.setSliderDown(True)
            self.setValue(self._value_at(event.position().x()))
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.isSliderDown():
            self.setValue(self._value_at(event.position().x()))
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.isSliderDown():
            self.setValue(self._value_at(event.position().x()))
            self.setSliderDown(False)
            event.accept()
            return
        super().mouseReleaseEvent(event)


class MetricRow(QWidget):
    valueCommitted = pyqtSignal(int)

    def __init__(self, icon: str, label: str, suffix: str = "%", accent: str | None = None, parent=None):
        super().__init__(parent)
        self.suffix = suffix
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(70)
        self._timer.timeout.connect(lambda: self.valueCommitted.emit(self.slider.value()))

        self.icon = IconWidget(icon, theme.MUTED, 20)
        self.label = QLabel(label)
        self.label.setObjectName("metricLabel")
        self.value_label = QLabel(f"0{suffix}")
        self.value_label.setObjectName("metricValue")
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.value_label.setFixedWidth(48)

        top = QHBoxLayout()
        top.setContentsMargins(0, 0, 0, 0)
        top.setSpacing(9)
        top.addWidget(self.icon)
        top.addWidget(self.label)
        top.addStretch(1)
        top.addWidget(self.value_label)

        self.slider = JumpSlider()
        self.slider.setRange(0, 100)
        self.slider.setPageStep(5)
        self.slider.setSingleStep(1)
        if accent:
            self.slider.setStyleSheet(
                f"QSlider::sub-page:horizontal {{ background: {accent}; border-radius: 3px; }}"
                "QSlider::sub-page:horizontal:disabled { background: rgba(255, 255, 255, 0.15); }"
            )
        self.slider.valueChanged.connect(self._on_change)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        layout.addLayout(top)
        layout.addWidget(self.slider)

    def _on_change(self, value: int):
        self.value_label.setText(f"{value}{self.suffix}")
        self._timer.start()

    def set_value(self, value: int):
        self.slider.blockSignals(True)
        self.slider.setValue(value)
        self.slider.blockSignals(False)
        self.value_label.setText(f"{value}{self.suffix}")

    def set_limits(self, maximum: int, value: int):
        self.slider.setRange(0, max(1, maximum))
        self.set_value(max(0, min(value, maximum)))

    def set_editable(self, editable: bool):
        self.slider.setEnabled(editable)
        self.label.setEnabled(editable)
        self.icon.setEnabled(editable)
        self.value_label.setEnabled(editable)


class ToggleSwitch(QAbstractButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setFixedSize(44, 24)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._offset = 0.0
        self._animation = QPropertyAnimation(self, b"offset", self)
        self._animation.setDuration(150)
        self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.toggled.connect(self._animate)

    @pyqtProperty(float)
    def offset(self):
        return self._offset

    @offset.setter
    def offset(self, value: float):
        self._offset = value
        self.update()

    def _animate(self, checked: bool):
        if self.isVisible():
            self._animation.stop()
            self._animation.setStartValue(self._offset)
            self._animation.setEndValue(1.0 if checked else 0.0)
            self._animation.start()
        else:
            self.offset = 1.0 if checked else 0.0

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        track_rect = QRectF(0, 0, 44, 24)
        off = QColor(255, 255, 255, 32)
        on = QColor(theme.ACCENT)
        t = self._offset
        fill = QColor(
            int(off.red() + (on.red() - off.red()) * t),
            int(off.green() + (on.green() - off.green()) * t),
            int(off.blue() + (on.blue() - off.blue()) * t),
            int(off.alpha() + (on.alpha() - off.alpha()) * t),
        )
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(fill)
        p.drawRoundedRect(track_rect, 12, 12)
        knob_x = 3.0 + 20.0 * t
        p.setBrush(QColor("#FFFFFF"))
        p.drawEllipse(QRectF(knob_x, 3.0, 18.0, 18.0))
        p.end()


class InputTile(QAbstractButton):
    confirmed = pyqtSignal(int)

    def __init__(self, value: int, label: str, parent=None):
        super().__init__(parent)
        self.value = value
        self.label_text = label
        self.current = False
        self.armed = False
        self._hover = False
        self.setFixedHeight(88)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAccessibleName(label)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(3200)
        self._timer.timeout.connect(self.disarm)
        self.clicked.connect(self._on_click)

    def _on_click(self):
        if self.current:
            return
        if self.armed:
            self.disarm()
            self.confirmed.emit(self.value)
        else:
            self.armed = True
            self._timer.start()
            self.update()

    def disarm(self):
        if self.armed:
            self.armed = False
            self.update()

    def set_current(self, current: bool):
        self.current = current
        self.disarm()
        self.update()

    def enterEvent(self, event):
        self._hover = True
        self.update()

    def leaveEvent(self, event):
        self._hover = False
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(0.75, 0.75, self.width() - 1.5, self.height() - 1.5)
        base = QColor(255, 255, 255, 12)
        border = QColor(255, 255, 255, 22)
        if self._hover and not self.current:
            base = QColor(255, 255, 255, 21)
            border = QColor(255, 255, 255, 34)
        if self.armed:
            base = QColor(255, 176, 32, 22)
            border = QColor(255, 176, 32, 130)
        if self.current:
            base = QColor(255, 106, 43, 30)
            border = QColor(255, 106, 43, 150)
        p.setPen(QPen(border, 1.0))
        p.setBrush(base)
        p.drawRoundedRect(rect, 12, 12)

        title_color = QColor(theme.TEXT) if not self.current else QColor("#FFAC82")
        p.setPen(title_color)
        p.setFont(theme.font(13, QFont.Weight.DemiBold))
        p.drawText(
            QRectF(16, 17, self.width() - 32, 20),
            int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
            self.label_text,
        )
        if self.current:
            subtitle = "当前输入"
            sub_color = QColor("#FF9A6B")
        elif self.armed:
            subtitle = "再次点击以切换"
            sub_color = QColor(theme.WARNING)
        else:
            subtitle = "点击切换"
            sub_color = QColor(theme.FAINT)
        p.setPen(sub_color)
        p.setFont(theme.font(11))
        p.drawText(
            QRectF(16, 49, self.width() - 32, 17),
            int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
            subtitle,
        )
        p.end()


class ConfirmButton(QPushButton):
    confirmed = pyqtSignal()

    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.normal_text = text
        self.setObjectName("actionBtn")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("需连续点击两次确认")
        self._armed = False
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(4200)
        self._timer.timeout.connect(self.disarm)
        self.clicked.connect(self._on_click)

    def _on_click(self):
        if self._armed:
            self.disarm()
            self.confirmed.emit()
        else:
            self._armed = True
            self.setProperty("armed", "true")
            self.setText("再次点击确认")
            self._repolish()
            self._timer.start()

    def disarm(self):
        if self._armed:
            self._armed = False
            self._timer.stop()
            self.setProperty("armed", "false")
            self.setText(self.normal_text)
            self._repolish()

    def _repolish(self):
        self.style().unpolish(self)
        self.style().polish(self)


class StatusDot(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(8, 8)
        self._color = QColor(theme.MUTED)

    def set_color(self, value: str):
        self._color = QColor(value)
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(self._color)
        p.drawEllipse(QRectF(1, 1, 6, 6))
        p.end()


class MiniOsd(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.Tool
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowTransparentForInput
            | Qt.WindowType.WindowDoesNotAcceptFocus
            | Qt.WindowType.NoDropShadowWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setFixedSize(300, 84)
        self._title = ""
        self._value = 0
        self._maximum = 100
        self._hold = QTimer(self)
        self._hold.setSingleShot(True)
        self._hold.setInterval(1250)
        self._hold.timeout.connect(self._fade_out)
        self._fade = QPropertyAnimation(self, b"windowOpacity", self)
        self._fade.setDuration(140)
        self._fade.finished.connect(self._on_fade_finished)

    def show_metric(self, title: str, value: int, maximum: int, screen):
        self._title = title
        self._value = value
        self._maximum = max(1, maximum)
        self.repaint()
        if screen is not None:
            geo = screen.availableGeometry()
            x = geo.center().x() - self.width() // 2
            y = geo.bottom() - 74 - self.height()
            self.move(x, y)
        self._hold.stop()
        self._fade.stop()
        if not self.isVisible():
            self.setWindowOpacity(0.0)
            self.show()
            self._fade.setStartValue(0.0)
            self._fade.setEndValue(1.0)
        else:
            self.setWindowOpacity(1.0)
            self._fade.setStartValue(1.0)
            self._fade.setEndValue(1.0)
        self._fade.start()
        self._hold.start()

    def _fade_out(self):
        self._fade.stop()
        self._fade.setStartValue(self.windowOpacity())
        self._fade.setEndValue(0.0)
        self._fade.start()

    def _on_fade_finished(self):
        if self.windowOpacity() <= 0.01:
            self.hide()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(0.75, 0.75, self.width() - 1.5, self.height() - 1.5)
        p.setPen(QPen(QColor(255, 255, 255, 20), 1.0))
        p.setBrush(QColor(18, 20, 25, 244))
        p.drawRoundedRect(rect, 16, 16)

        p.setPen(QColor(theme.MUTED))
        p.setFont(theme.font(11))
        p.drawText(
            QRectF(20, 15, 150, 16),
            int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
            self._title,
        )
        p.setPen(QColor(theme.TEXT))
        p.setFont(theme.font(19, QFont.Weight.DemiBold))
        p.drawText(
            QRectF(150, 11, self.width() - 170, 24),
            int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter),
            f"{self._value}%",
        )
        track = QRectF(20, 56, self.width() - 40, 5)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(255, 255, 255, 24))
        p.drawRoundedRect(track, 2.5, 2.5)
        ratio = min(1.0, max(0.0, self._value / self._maximum))
        if ratio > 0:
            fill = QRectF(track.x(), track.y(), max(5.0, track.width() * ratio), track.height())
            p.setBrush(QColor(theme.ACCENT))
            p.drawRoundedRect(fill, 2.5, 2.5)
        p.end()
