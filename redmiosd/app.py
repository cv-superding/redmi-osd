from __future__ import annotations

import ctypes
import re
from ctypes import wintypes
from pathlib import Path

from PyQt6.QtCore import QPoint, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QGuiApplication, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QApplication, QButtonGroup, QFrame, QGraphicsDropShadowEffect, QGridLayout,
    QHBoxLayout, QLabel, QPushButton, QStackedWidget, QVBoxLayout, QWidget,
)

from . import theme
from .autostart import is_enabled as autostart_enabled
from .autostart import set_enabled as set_autostart
from .monitor import (
    BLUE_GAIN, BRIGHTNESS, COLOR_PRESET, CONTRAST, GREEN_GAIN, INPUT_LABELS,
    INPUT_SOURCE, PRESET_LABELS, PRESET_NOTES, RED_GAIN,
    RESTORE_COLOR, RESTORE_LUMINANCE_CONTRAST, VOLUME, DdcWorker,
)
from .widgets import (
    ConfirmButton, InputTile, MetricRow, MiniOsd, StatusDot,
    ToggleSwitch, app_icon, logo_pixmap,
)

user32 = ctypes.WinDLL("user32", use_last_error=True)
user32.RegisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT]
user32.RegisterHotKey.restype = wintypes.BOOL
user32.UnregisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int]
user32.UnregisterHotKey.restype = wintypes.BOOL

WM_HOTKEY = 0x0312
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_NOREPEAT = 0x4000
VK_LEFT = 0x25
VK_UP = 0x26
VK_RIGHT = 0x27
VK_DOWN = 0x28
VK_O = 0x4F
VK_I = 0x49
VK_F10 = 0x79

HOTKEY_TOGGLE = 1
HOTKEY_BRIGHT_UP = 2
HOTKEY_BRIGHT_DOWN = 3
HOTKEY_CONTRAST_UP = 4
HOTKEY_CONTRAST_DOWN = 5
HOTKEY_PREVIOUS_INPUT = 6

TOGGLE_HOTKEYS = (
    ("Ctrl+Alt+O", ("Ctrl", "Alt", "O"), MOD_CONTROL | MOD_ALT, VK_O),
    ("Ctrl+Alt+Shift+O", ("Ctrl", "Alt", "Shift", "O"), MOD_CONTROL | MOD_ALT | MOD_SHIFT, VK_O),
    ("Ctrl+Alt+F10", ("Ctrl", "Alt", "F10"), MOD_CONTROL | MOD_ALT, VK_F10),
)


def section_label(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("sectionLabel")
    return label


def divider() -> QFrame:
    line = QFrame()
    line.setObjectName("divider")
    line.setFrameShape(QFrame.Shape.NoFrame)
    return line


def keycap(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("keycap")
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    return label


class DragHeader(QWidget):
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            handle = self.window().windowHandle()
            if handle is not None and handle.startSystemMove():
                event.accept()
                return
        super().mousePressEvent(event)


class DisplayPage(QWidget):
    valueCommitted = pyqtSignal(int, int)
    brightnessPreset = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 16, 0, 0)
        layout.setSpacing(24)
        self.rows: dict[int, MetricRow] = {}
        definitions = [
            (BRIGHTNESS, "sun", "亮度"),
            (CONTRAST, "contrast", "对比度"),
            (VOLUME, "volume", "音量"),
        ]
        for code, icon, label in definitions:
            row = MetricRow(icon, label)
            row.valueCommitted.connect(lambda value, c=code: self.valueCommitted.emit(c, value))
            layout.addWidget(row)
            self.rows[code] = row
        layout.addSpacing(2)
        layout.addWidget(section_label("快捷亮度"))
        quick = QHBoxLayout()
        quick.setContentsMargins(0, 0, 0, 0)
        quick.setSpacing(8)
        for percent in (30, 50, 70, 100):
            button = QPushButton(f"{percent}%")
            button.setObjectName("chip")
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(
                lambda checked=False, value=percent: self.brightnessPreset.emit(value)
            )
            quick.addWidget(button, 1)
        layout.addLayout(quick)
        layout.addStretch(1)
        hint = QLabel("拖动滑杆即时生效 · 悬停后可用滚轮微调")
        hint.setObjectName("hintLabel")
        layout.addWidget(hint)

    def apply_values(self, values: dict[int, tuple[int, int]]):
        for code, row in self.rows.items():
            if code not in values:
                row.hide()
                continue
            row.show()
            current, maximum = values[code]
            row.set_limits(maximum or 100, current)
            row.set_editable(True)


class ColorPage(QWidget):
    presetSelected = pyqtSignal(int)
    gainCommitted = pyqtSignal(int, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 16, 0, 0)
        layout.setSpacing(10)

        layout.addWidget(section_label("色彩预设"))
        chips_layout = QHBoxLayout()
        chips_layout.setContentsMargins(0, 0, 0, 0)
        chips_layout.setSpacing(8)
        self.chips: dict[int, QPushButton] = {}
        self.group = QButtonGroup(self)
        self.group.setExclusive(True)
        for value in (0x04, 0x05, 0x08, 0x0B):
            chip = QPushButton(PRESET_LABELS[value])
            chip.setObjectName("chip")
            chip.setCheckable(True)
            chip.setCursor(Qt.CursorShape.PointingHandCursor)
            if value == 0x0B:
                chip.setToolTip("切换到用户模式后可自定义 RGB 增益")
            chip.clicked.connect(lambda checked=False, v=value: self.presetSelected.emit(v))
            self.group.addButton(chip)
            chips_layout.addWidget(chip, 1)
            self.chips[value] = chip
        layout.addLayout(chips_layout)

        self.preset_note = QLabel("")
        self.preset_note.setObjectName("hintLabel")
        layout.addWidget(self.preset_note)
        layout.addSpacing(18)

        gain_header = QHBoxLayout()
        gain_header.setContentsMargins(0, 0, 0, 0)
        gain_header.addWidget(section_label("RGB 增益"))
        gain_header.addStretch(1)
        self.gain_hint = QLabel("仅用户模式可调")
        self.gain_hint.setObjectName("hintLabel")
        gain_header.addWidget(self.gain_hint)
        self.user_mode_button = QPushButton("启用")
        self.user_mode_button.setObjectName("linkBtn")
        self.user_mode_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.user_mode_button.setToolTip("切换到用户模式并解锁 RGB 增益")
        self.user_mode_button.clicked.connect(lambda: self.presetSelected.emit(0x0B))
        gain_header.addWidget(self.user_mode_button)
        layout.addLayout(gain_header)

        self.gain_rows: dict[int, MetricRow] = {}
        for code, icon, label, accent in (
            (RED_GAIN, "r", "红", "#FF6B6B"),
            (GREEN_GAIN, "g", "绿", "#5BD6A2"),
            (BLUE_GAIN, "b", "蓝", "#5B9DFF"),
        ):
            row = MetricRow(icon, label, suffix="", accent=accent)
            row.valueCommitted.connect(lambda value, c=code: self.gainCommitted.emit(c, value))
            layout.addWidget(row)
            self.gain_rows[code] = row

        layout.addStretch(1)
        self.footer_hint = QLabel("")
        self.footer_hint.setObjectName("hintLabel")
        self.footer_hint.setWordWrap(True)
        layout.addWidget(self.footer_hint)
        self.set_editable(False)

    def apply(self, supported: tuple[int, ...] | None, values: dict[int, tuple[int, int]]):
        supported_set = set(supported or (0x04, 0x05, 0x08, 0x0B))
        for value, chip in self.chips.items():
            chip.setVisible(value in supported_set)
        current = values.get(COLOR_PRESET, (0, 0))[0]
        chip = self.chips.get(current)
        if chip is not None:
            chip.blockSignals(True)
            chip.setChecked(True)
            chip.blockSignals(False)
        self.select_preset(current)
        for code, row in self.gain_rows.items():
            if code in values:
                row.show()
                cur, maximum = values[code]
                row.set_limits(maximum or 100, cur)
            else:
                row.hide()
        self.set_editable(current == 0x0B)

    def select_preset(self, value: int):
        self.preset_note.setText(PRESET_NOTES.get(value, "显示器自定义模式"))
        self.set_editable(value == 0x0B)

    def set_editable(self, editable: bool):
        for row in self.gain_rows.values():
            row.set_editable(editable)
        self.gain_hint.setText("可编辑" if editable else "仅用户模式可调")
        self.user_mode_button.setVisible(not editable)
        if editable:
            self.footer_hint.setText("当前为用户模式，RGB 增益更改会立即应用。")
        else:
            self.footer_hint.setText("点击「启用」或选择「用户」，即可自定义 RGB 增益。")


class InputPage(QWidget):
    inputConfirmed = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 16, 0, 0)
        layout.setSpacing(12)
        layout.addWidget(section_label("输入源"))

        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(10)
        self.tiles: dict[int, InputTile] = {}
        definitions = [(0x0F, "DP 1"), (0x10, "DP 2"), (0x11, "HDMI 1"), (0x12, "HDMI 2")]
        for index, (value, label) in enumerate(definitions):
            tile = InputTile(value, label)
            tile.confirmed.connect(self.inputConfirmed.emit)
            tile.clicked.connect(lambda checked=False, t=tile: self._disarm_others(t))
            grid.addWidget(tile, index // 2, index % 2)
            self.tiles[value] = tile
        layout.addLayout(grid)
        layout.addStretch(1)

        warning = QLabel("提示：切换信号源后此面板将不可见，可按 Ctrl+Alt+I 切回上一输入。")
        warning.setObjectName("hintLabel")
        warning.setWordWrap(True)
        layout.addWidget(warning)

    def _disarm_others(self, active: InputTile):
        for tile in self.tiles.values():
            if tile is not active:
                tile.disarm()

    def apply(self, supported: tuple[int, ...] | None, current: int | None):
        supported_set = set(supported or (0x0F, 0x10, 0x11, 0x12))
        for value, tile in self.tiles.items():
            tile.setVisible(value in supported_set)
            tile.set_current(value == current)


class MorePage(QWidget):
    autoStartToggled = pyqtSignal(bool)
    restoreLuminanceConfirmed = pyqtSignal()
    restoreColorConfirmed = pyqtSignal()
    quitRequested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 16, 0, 0)
        layout.setSpacing(10)

        layout.addWidget(section_label("启动"))
        auto_row = QHBoxLayout()
        auto_row.setContentsMargins(0, 0, 0, 0)
        texts = QVBoxLayout()
        texts.setContentsMargins(0, 0, 0, 0)
        texts.setSpacing(2)
        title = QLabel("开机自动启动")
        title.setObjectName("metricLabel")
        self.autostart_hint = QLabel("后台静默运行，按 Ctrl+Alt+Shift+O 呼出")
        self.autostart_hint.setObjectName("hintLabel")
        texts.addWidget(title)
        texts.addWidget(self.autostart_hint)
        auto_row.addLayout(texts)
        auto_row.addStretch(1)
        self.autostart_switch = ToggleSwitch()
        self.autostart_switch.toggled.connect(self.autoStartToggled.emit)
        auto_row.addWidget(self.autostart_switch)
        layout.addLayout(auto_row)

        layout.addSpacing(2)
        layout.addWidget(divider())
        layout.addWidget(section_label("维护"))
        self.restore_lum = ConfirmButton("恢复亮度与对比度")
        self.restore_lum.confirmed.connect(self.restoreLuminanceConfirmed.emit)
        self.restore_color = ConfirmButton("恢复颜色设置")
        self.restore_color.confirmed.connect(self.restoreColorConfirmed.emit)
        layout.addWidget(self.restore_lum)
        layout.addWidget(self.restore_color)

        layout.addWidget(divider())
        layout.addWidget(section_label("快捷键"))
        layout.addWidget(self._shortcut_row(("Ctrl", "Alt", "↑", "↓"), "亮度 ±5"))
        layout.addWidget(self._shortcut_row(("Ctrl", "Alt", "←", "→"), "对比度 ±5"))
        layout.addWidget(self._shortcut_row(("Ctrl", "Alt", "I"), "切回上一输入"))
        self._toggle_key_labels: list[QLabel] = []
        toggle_row = self._shortcut_row(("Ctrl", "Alt", "Shift", "O"), "显示 / 隐藏")
        self._toggle_key_labels = toggle_row.findChildren(
            QLabel, "keycap", Qt.FindChildOption.FindDirectChildrenOnly,
        )
        layout.addWidget(toggle_row)
        layout.addStretch(1)

        self.info = QLabel("DDC/CI")
        self.info.setObjectName("hintLabel")
        layout.addWidget(self.info)
        quit_button = QPushButton("退出 Redmi OSD")
        quit_button.setObjectName("quitBtn")
        quit_button.setCursor(Qt.CursorShape.PointingHandCursor)
        quit_button.clicked.connect(self.quitRequested.emit)
        layout.addWidget(quit_button)

    def _shortcut_row(self, keys, description: str) -> QWidget:
        wrapper = QWidget()
        row = QHBoxLayout(wrapper)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(4)
        for key in keys:
            row.addWidget(keycap(key))
        row.addStretch(1)
        text = QLabel(description)
        text.setObjectName("hintLabel")
        row.addWidget(text)
        return wrapper

    def set_toggle_hotkey(self, label: str, keys: list[str]):
        self.autostart_hint.setText(f"后台静默运行，按 {label} 呼出")
        for index, key_label in enumerate(self._toggle_key_labels):
            if index < len(keys):
                key_label.setText(keys[index])
                key_label.show()
            else:
                key_label.hide()

    def set_autostart(self, enabled: bool):
        self.autostart_switch.blockSignals(True)
        self.autostart_switch.setChecked(enabled)
        self.autostart_switch.blockSignals(False)

    def set_info(self, text: str):
        self.info.setText(text)


class MainWindow(QWidget):
    def __init__(self, headless: bool = False, tool_window: bool = False, parent=None):
        super().__init__(parent)
        self.headless = headless
        self._state: dict | None = None
        self._finished_connecting = False
        self._initial_positioned = False
        self._vcp: dict[int, tuple[int, ...] | None] = {}
        self._current: dict[int, int] = {}
        self._maximum: dict[int, int] = {}
        self._last_good: dict[int, int] = {}
        self._previous_input: int | None = None
        self._toggle_hotkey_label = "Ctrl+Alt+Shift+O"
        self._toggle_hotkey_keys = ["Ctrl", "Alt", "Shift", "O"]
        self._hotkey_ids: list[int] = []
        self._closed = False
        self._worker: DdcWorker | None = None
        self._status_timer = QTimer(self)
        self._status_timer.setSingleShot(True)
        self._status_timer.timeout.connect(self._reset_status)

        self.setWindowTitle("Redmi OSD")
        self.setWindowIcon(app_icon())
        window_kind = Qt.WindowType.Tool if tool_window else Qt.WindowType.Window
        self.setWindowFlags(
            window_kind
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        if tool_window:
            self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFixedSize(416, 640)
        self._screen = self._pick_screen()
        self._build_ui()

        self.more_page.set_autostart(autostart_enabled())
        self.more_page.set_toggle_hotkey(self._toggle_hotkey_label, self._toggle_hotkey_keys)
        self._mini = MiniOsd()
        if not self.headless:
            self._register_hotkeys()
        self._connect_worker()

        shortcut = QShortcut(QKeySequence("Esc"), self)
        shortcut.activated.connect(self.showMinimized)

    # ---------- UI ----------
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)

        self.panel = QFrame()
        self.panel.setObjectName("panel")
        shadow = QGraphicsDropShadowEffect(self.panel)
        shadow.setBlurRadius(44)
        shadow.setOffset(0, 10)
        shadow.setColor(QColor(0, 0, 0, 160))
        self.panel.setGraphicsEffect(shadow)
        root.addWidget(self.panel)

        layout = QVBoxLayout(self.panel)
        layout.setContentsMargins(24, 20, 24, 14)
        layout.setSpacing(0)

        header = DragHeader()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(10)
        logo = QLabel()
        logo.setPixmap(logo_pixmap(30))
        logo.setFixedSize(30, 30)
        header_layout.addWidget(logo)

        titles = QVBoxLayout()
        titles.setContentsMargins(0, 0, 0, 0)
        titles.setSpacing(2)
        title_row = QHBoxLayout()
        title_row.setContentsMargins(0, 0, 0, 0)
        title_row.setSpacing(8)
        title = QLabel("Redmi G27Q 2026")
        title.setObjectName("appTitle")
        self.badge = QLabel("读取中")
        self.badge.setObjectName("inputBadge")
        title_row.addWidget(title)
        title_row.addWidget(self.badge)
        title_row.addStretch(1)
        self.subtitle = QLabel("正在连接显示器…")
        self.subtitle.setObjectName("appSubtitle")
        titles.addLayout(title_row)
        titles.addWidget(self.subtitle)
        header_layout.addLayout(titles)
        header_layout.addStretch(1)

        self.min_button = QPushButton("−")
        self.min_button.setObjectName("winBtn")
        self.min_button.setFixedSize(26, 26)
        self.min_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.min_button.setToolTip("最小化")
        self.min_button.clicked.connect(self.showMinimized)
        header_layout.addWidget(self.min_button)
        self.close_button = QPushButton("×")
        self.close_button.setObjectName("winBtn")
        self.close_button.setProperty("close", "true")
        self.close_button.setFixedSize(26, 26)
        self.close_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_button.setToolTip("关闭")
        self.close_button.clicked.connect(self.close)
        header_layout.addWidget(self.close_button)
        layout.addWidget(header)

        layout.addSpacing(16)
        self.tabs: list[QPushButton] = []
        tabs_layout = QHBoxLayout()
        tabs_layout.setContentsMargins(0, 0, 0, 0)
        tabs_layout.setSpacing(6)
        self.tab_group = QButtonGroup(self)
        self.tab_group.setExclusive(True)
        for index, text in enumerate(("显示", "色彩", "输入", "更多")):
            button = QPushButton(text)
            button.setObjectName("tab")
            button.setCheckable(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(lambda checked=False, i=index: self.stack.setCurrentIndex(i))
            self.tab_group.addButton(button)
            tabs_layout.addWidget(button, 1)
            self.tabs.append(button)
        self.tabs[0].setChecked(True)
        layout.addLayout(tabs_layout)
        layout.addWidget(divider())

        self.stack = QStackedWidget()
        self.display_page = DisplayPage()
        self.color_page = ColorPage()
        self.input_page = InputPage()
        self.more_page = MorePage()
        for page in (self.display_page, self.color_page, self.input_page, self.more_page):
            self.stack.addWidget(page)
        layout.addSpacing(4)
        layout.addWidget(self.stack, 1)
        for page in (self.display_page, self.color_page, self.input_page):
            page.setEnabled(False)

        footer = QHBoxLayout()
        footer.setContentsMargins(0, 8, 0, 0)
        footer.setSpacing(7)
        self.status_dot = StatusDot()
        self.status_label = QLabel("正在读取显示器…")
        self.status_label.setObjectName("statusLabel")
        footer.addWidget(self.status_dot)
        footer.addWidget(self.status_label)
        self.retry_button = QPushButton("重试")
        self.retry_button.setObjectName("retryBtn")
        self.retry_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.retry_button.clicked.connect(self._retry_backend)
        self.retry_button.hide()
        footer.addWidget(self.retry_button)
        footer.addStretch(1)
        hint = QLabel(self._toggle_hotkey_label)
        hint.setObjectName("hintLabel")
        hint.setToolTip("显示或最小化面板")
        self.footer_hotkey = hint
        footer.addWidget(hint)
        layout.addLayout(footer)

        self.display_page.valueCommitted.connect(self._set_vcp)
        self.display_page.brightnessPreset.connect(self._set_brightness_preset)
        self.color_page.presetSelected.connect(self._choose_preset)
        self.color_page.gainCommitted.connect(self._set_vcp)
        self.input_page.inputConfirmed.connect(self._switch_input)
        self.more_page.autoStartToggled.connect(self._toggle_autostart)
        self.more_page.restoreLuminanceConfirmed.connect(
            lambda: self._trigger(RESTORE_LUMINANCE_CONTRAST, "已恢复亮度与对比度")
        )
        self.more_page.restoreColorConfirmed.connect(
            lambda: self._trigger(RESTORE_COLOR, "已恢复颜色设置")
        )
        self.more_page.quitRequested.connect(self.close)

        self._render_decorations()

    def _render_decorations(self):
        self.min_button.setStyleSheet("font-size: 16px;")
        self.close_button.setStyleSheet("font-size: 17px;")

    # ---------- DDC ----------
    def _connect_worker(self):
        if self._closed or self._worker is not None:
            return
        self._worker = DdcWorker(self)
        self._worker.stateReady.connect(self._on_state)
        self._worker.failed.connect(self._on_failed)
        self._worker.valuesSynced.connect(self._on_values_synced)
        self._worker.setFinished.connect(self._on_set_finished)
        self._worker.triggerFinished.connect(self._on_trigger_finished)
        self._worker.start()

    def _on_state(self, state: dict):
        self._state = state
        self._vcp = {
            int(code): (tuple(values) if values else None)
            for code, values in state["vcp"].items()
        }
        self._apply_values(state["values"])
        self._screen = self._pick_screen(state)
        if not self.headless:
            self.subtitle.setText(f"{self._screen_meta()} · DDC/CI")
        else:
            self.subtitle.setText("2560 × 1440 · 144 Hz · DDC/CI")
        self.more_page.set_info(self._mccs_info(state["capabilities"]))
        self.status_label.setToolTip(state["device"])
        for page in (self.display_page, self.color_page, self.input_page):
            page.setEnabled(True)
        self._set_status("DDC/CI 已连接", theme.SUCCESS)
        self.retry_button.hide()
        self._finished_connecting = True

    def _apply_values(self, raw_values: dict):
        values = {int(code): tuple(value) for code, value in raw_values.items()}
        for code, (current, maximum) in values.items():
            self._current[code] = current
            self._maximum[code] = maximum
            self._last_good[code] = current
        self.display_page.apply_values(values)
        self.color_page.apply(self._vcp.get(COLOR_PRESET), values)
        self.input_page.apply(
            self._vcp.get(INPUT_SOURCE),
            values.get(INPUT_SOURCE, (None, 0))[0],
        )
        self._update_badge()

    def _on_failed(self, message: str):
        self.status_dot.set_color(theme.DANGER)
        self.status_label.setText("DDC/CI 连接失败")
        self.status_label.setToolTip(message)
        self.subtitle.setText("请确认显示器已开启 DDC/CI")
        self.badge.setText("未连接")
        self.more_page.set_info("DDC/CI 未连接")
        self.retry_button.show()
        self._finished_connecting = True

    def _retry_backend(self):
        if self._closed:
            return
        if self._worker is not None:
            if self._worker.isRunning():
                return
            self._worker.deleteLater()
            self._worker = None
        self._finished_connecting = False
        self._set_status("正在重新连接显示器…", theme.WARNING)
        self._connect_worker()

    def _on_values_synced(self, raw_values: dict):
        if self._state is None:
            return
        values = {int(code): tuple(value) for code, value in raw_values.items()}
        self._apply_values(values)

    def _set_vcp(self, code: int, value: int):
        if self._state is None or self._worker is None:
            return
        maximum = self._maximum.get(code, 100)
        value = max(0, min(value, maximum))
        self._current[code] = value
        self._worker.submit_set(code, value)

    def _set_brightness_preset(self, value: int):
        row = self.display_page.rows.get(BRIGHTNESS)
        if row is not None:
            row.set_value(value)
        self._set_vcp(BRIGHTNESS, value)

    def _choose_preset(self, value: int):
        if self._state is None or self._worker is None:
            return
        self._current[COLOR_PRESET] = value
        self.color_page.select_preset(value)
        self._worker.submit_set(COLOR_PRESET, value)

    def _switch_input(self, value: int):
        if self._state is None or self._worker is None:
            return
        if value == self._current.get(INPUT_SOURCE):
            return
        previous = self._current.get(INPUT_SOURCE)
        if previous is not None:
            self._previous_input = previous
        label = INPUT_LABELS.get(value, "该接口")
        self._current[INPUT_SOURCE] = value
        self.input_page.apply(self._vcp.get(INPUT_SOURCE), value)
        self._update_badge()
        self._set_status(f"正在切换至 {label}…", theme.WARNING)
        self._worker.submit_set(INPUT_SOURCE, value)

    def _switch_previous_input(self):
        if self._previous_input is None:
            return
        target = self._previous_input
        self._previous_input = None
        self._switch_input(target)

    def _on_set_finished(self, code: int, value: int, ok: bool):
        if ok:
            self._last_good[code] = value
            if code == INPUT_SOURCE:
                label = INPUT_LABELS.get(value, "新输入")
                self.input_page.apply(self._vcp.get(INPUT_SOURCE), value)
                self._update_badge()
                self._set_status(f"已切换至 {label}", theme.SUCCESS, 4000)
            elif code == COLOR_PRESET:
                self.color_page.select_preset(value)
                self._set_status("色彩预设已更新", theme.SUCCESS, 2500)
            elif code in (RED_GAIN, GREEN_GAIN, BLUE_GAIN):
                pass
            return

        self._set_status("设置未生效，正在重新读取显示器…", theme.WARNING, 5000)
        if code == INPUT_SOURCE:
            previous = self._last_good.get(INPUT_SOURCE)
            if previous is not None:
                self._current[INPUT_SOURCE] = previous
                self.input_page.apply(self._vcp.get(INPUT_SOURCE), previous)
                self._update_badge()
        elif code == COLOR_PRESET:
            previous = self._last_good.get(COLOR_PRESET)
            if previous is not None:
                self._current[COLOR_PRESET] = previous
                chip = self.color_page.chips.get(previous)
                if chip is not None:
                    chip.blockSignals(True)
                    chip.setChecked(True)
                    chip.blockSignals(False)
                self.color_page.select_preset(previous)
        if self._worker is not None:
            QTimer.singleShot(250, self._refresh_values)

    def _trigger(self, code: int, message: str):
        if self._state is None or self._worker is None:
            return
        self._set_status("正在恢复…", theme.WARNING)
        self._worker.submit_trigger(code)

    def _on_trigger_finished(self, code: int, ok: bool):
        if ok:
            message = "已恢复亮度与对比度" if code == RESTORE_LUMINANCE_CONTRAST else "已恢复颜色设置"
            self._set_status(message, theme.SUCCESS, 4000)
            QTimer.singleShot(400, self._refresh_values)
        else:
            self._set_status("恢复失败，请重试", theme.WARNING, 4000)

    def _refresh_values(self):
        if self._worker is not None:
            self._worker.refresh()

    # ---------- helpers ----------
    def _update_badge(self):
        current = self._current.get(INPUT_SOURCE)
        self.badge.setText(INPUT_LABELS.get(current, "输入源"))

    @staticmethod
    def _mccs_info(capabilities: str) -> str:
        match = re.search(r"mccs_ver\(([^)]+)\)", capabilities)
        if match:
            return f"VESA MCCS {match.group(1)} · DDC/CI"
        return "DDC/CI"

    def _set_status(self, text: str, color: str = theme.MUTED, reset_ms: int | None = None):
        self._status_timer.stop()
        self.status_dot.set_color(color)
        self.status_label.setText(text)
        if reset_ms:
            self._status_timer.start(reset_ms)

    def _reset_status(self):
        if self._state is None:
            self.status_dot.set_color(theme.DANGER)
            self.status_label.setText("DDC/CI 连接失败")
        else:
            self.status_dot.set_color(theme.SUCCESS)
            self.status_label.setText("DDC/CI 已连接")

    def _pick_screen(self, state: dict | None = None):
        if state is not None:
            left, top, width, height = state["rect"]
            screen = QGuiApplication.screenAt(QPoint(left + width // 2, top + height // 2))
            if screen is not None:
                return screen
        screens = QGuiApplication.screens()
        if not screens:
            return None
        return max(
            screens,
            key=lambda screen: screen.geometry().width()
            * screen.geometry().height()
            * screen.devicePixelRatio() ** 2,
        )

    def _screen_meta(self) -> str:
        screen = self._screen
        if screen is None:
            return "2560 × 1440 · 180 Hz"
        width = round(screen.geometry().width() * screen.devicePixelRatio())
        height = round(screen.geometry().height() * screen.devicePixelRatio())
        hz = round(screen.refreshRate())
        return f"{width} × {height} · {hz} Hz"

    def _center_window(self):
        screen = self._screen
        if screen is None:
            return
        area = screen.availableGeometry()
        x = area.center().x() - self.width() // 2
        y = area.center().y() - self.height() // 2
        self.move(max(area.left(), x), max(area.top(), y))

    def showEvent(self, event):
        if not self._initial_positioned:
            self._initial_positioned = True
            self._center_window()
        super().showEvent(event)

    # ---------- hotkeys ----------
    def _register_hotkeys(self):
        hwnd = int(self.winId())
        definitions = (
            (HOTKEY_BRIGHT_UP, MOD_CONTROL | MOD_ALT | MOD_NOREPEAT, VK_UP),
            (HOTKEY_BRIGHT_DOWN, MOD_CONTROL | MOD_ALT | MOD_NOREPEAT, VK_DOWN),
            (HOTKEY_CONTRAST_UP, MOD_CONTROL | MOD_ALT | MOD_NOREPEAT, VK_RIGHT),
            (HOTKEY_CONTRAST_DOWN, MOD_CONTROL | MOD_ALT | MOD_NOREPEAT, VK_LEFT),
            (HOTKEY_PREVIOUS_INPUT, MOD_CONTROL | MOD_ALT | MOD_NOREPEAT, VK_I),
        )
        for hotkey_id, modifiers, key in definitions:
            if user32.RegisterHotKey(hwnd, hotkey_id, modifiers, key):
                self._hotkey_ids.append(hotkey_id)

        for label, keys, modifiers, key in TOGGLE_HOTKEYS:
            if user32.RegisterHotKey(hwnd, HOTKEY_TOGGLE, modifiers | MOD_NOREPEAT, key):
                self._hotkey_ids.append(HOTKEY_TOGGLE)
                self._toggle_hotkey_label = label
                self._toggle_hotkey_keys = list(keys)
                break
        self.footer_hotkey.setText(self._toggle_hotkey_label)
        self.more_page.set_toggle_hotkey(self._toggle_hotkey_label, self._toggle_hotkey_keys)

    def _unregister_hotkeys(self):
        if self.headless:
            return
        hwnd = int(self.winId())
        for hotkey_id in self._hotkey_ids:
            user32.UnregisterHotKey(hwnd, hotkey_id)
        self._hotkey_ids.clear()

    def nativeEvent(self, event_type, message):
        try:
            if bytes(event_type) in (b"windows_generic_MSG", b"windows_dispatcher_MSG"):
                msg = wintypes.MSG.from_address(int(message))
                if msg.message == WM_HOTKEY:
                    self._handle_hotkey(int(msg.wParam))
                    return True, 0
        except Exception:
            pass
        # PyQt6 6.9 在这台机器上调用 super().nativeEvent() 会原生崩溃，未处理消息直接返回。
        return False, 0

    def _handle_hotkey(self, hotkey_id: int):
        if hotkey_id == HOTKEY_TOGGLE:
            self.toggle_panel()
            return
        if hotkey_id == HOTKEY_PREVIOUS_INPUT:
            self._switch_previous_input()
            return
        if self._state is None:
            return
        if hotkey_id in (HOTKEY_BRIGHT_UP, HOTKEY_BRIGHT_DOWN):
            code, title, step = BRIGHTNESS, "亮度", 5
            delta = step if hotkey_id == HOTKEY_BRIGHT_UP else -step
        else:
            code, title, step = CONTRAST, "对比度", 5
            delta = step if hotkey_id == HOTKEY_CONTRAST_UP else -step
        maximum = self._maximum.get(code, 100)
        current = self._current.get(code, 0)
        value = max(0, min(maximum, current + delta))
        self._current[code] = value
        row = self.display_page.rows.get(code)
        if row is not None:
            row.set_value(value)
        if self._worker is not None:
            self._worker.submit_set(code, value)
        self._mini.show_metric(title, value, maximum, self._screen)

    def toggle_panel(self):
        if self.isVisible() and not self.isMinimized():
            self.showMinimized()
        else:
            self.reveal()

    def reveal(self):
        self._screen = self._pick_screen(self._state)
        self.showNormal()
        self.raise_()
        self.activateWindow()
        if self._state is None:
            self._retry_backend()
        elif self._worker is not None:
            self._worker.refresh()

    def start_hidden(self):
        self.hide()

    # ---------- autostart / lifecycle ----------
    def _toggle_autostart(self, enabled: bool):
        ok, _error = set_autostart(enabled)
        if ok:
            self._set_status("已开启开机自启" if enabled else "已关闭开机自启", theme.SUCCESS, 3000)
        else:
            self._set_status("无法修改开机启动项", theme.WARNING, 4000)
            self.more_page.set_autostart(not enabled)

    def capture_pages(self, out_dir: Path) -> list[Path]:
        out_dir.mkdir(parents=True, exist_ok=True)
        self.show()
        QApplication.processEvents()
        paths: list[Path] = []
        for index, name in enumerate(("display", "color", "input", "more")):
            self.tabs[index].setChecked(True)
            self.stack.setCurrentIndex(index)
            QApplication.processEvents()
            path = out_dir / f"page-{name}.png"
            self.grab().save(str(path))
            paths.append(path)
        self._mini.show_metric("亮度", self._current.get(BRIGHTNESS, 39), self._maximum.get(BRIGHTNESS, 100), self._screen)
        QApplication.processEvents()
        mini_path = out_dir / "osd-mini.png"
        self._mini.grab().save(str(mini_path))
        paths.append(mini_path)
        self._mini.hide()
        return paths

    def closeEvent(self, event):
        if self._closed:
            event.accept()
            return
        self._closed = True
        self._unregister_hotkeys()
        self._mini.close()
        if self._worker is not None:
            self._worker.request_stop()
            self._worker.wait(3000)
            self._worker = None
        event.accept()
        QApplication.quit()
