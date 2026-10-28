from __future__ import annotations

import ctypes
import queue
import re
import time
from ctypes import wintypes
from dataclasses import dataclass

from PyQt6.QtCore import QThread, pyqtSignal

user32 = ctypes.WinDLL("user32", use_last_error=True)
dxva2 = ctypes.WinDLL("dxva2", use_last_error=True)

BRIGHTNESS = 0x10
CONTRAST = 0x12
COLOR_PRESET = 0x14
RED_GAIN = 0x16
GREEN_GAIN = 0x18
BLUE_GAIN = 0x1A
VOLUME = 0x62
INPUT_SOURCE = 0x60
RESTORE_LUMINANCE_CONTRAST = 0x05
RESTORE_COLOR = 0x08

RELEVANT_CODES = (
    BRIGHTNESS, CONTRAST, COLOR_PRESET, RED_GAIN, GREEN_GAIN, BLUE_GAIN,
    INPUT_SOURCE, VOLUME,
)

INPUT_LABELS = {
    0x01: "VGA",
    0x03: "DVI",
    0x0F: "DP 1",
    0x10: "DP 2",
    0x11: "HDMI 1",
    0x12: "HDMI 2",
}

PRESET_LABELS = {
    0x01: "sRGB",
    0x02: "原生",
    0x03: "4000K",
    0x04: "5000K",
    0x05: "6500K",
    0x06: "7500K",
    0x07: "8200K",
    0x08: "9300K",
    0x09: "10000K",
    0x0A: "11500K",
    0x0B: "用户",
    0x0C: "用户 2",
    0x0D: "用户 3",
}

PRESET_NOTES = {
    0x04: "暖色，适合夜间与影音",
    0x05: "标准色温，日常使用",
    0x08: "偏冷色温，适合明亮环境",
    0x0B: "自定义 RGB 增益",
}


class PHYSICAL_MONITOR(ctypes.Structure):
    _fields_ = [
        ("hPhysicalMonitor", wintypes.HANDLE),
        ("szPhysicalMonitorDescription", wintypes.WCHAR * 128),
    ]


class MONITORINFOEXW(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("rcMonitor", wintypes.RECT),
        ("rcWork", wintypes.RECT),
        ("dwFlags", wintypes.DWORD),
        ("szDevice", wintypes.WCHAR * 32),
    ]


MONITORENUMPROC = ctypes.WINFUNCTYPE(
    wintypes.BOOL, wintypes.HMONITOR, wintypes.HDC,
    ctypes.POINTER(wintypes.RECT), wintypes.LPARAM,
)

user32.EnumDisplayMonitors.argtypes = [wintypes.HDC, ctypes.c_void_p, MONITORENUMPROC, wintypes.LPARAM]
user32.EnumDisplayMonitors.restype = wintypes.BOOL
user32.GetMonitorInfoW.argtypes = [wintypes.HMONITOR, ctypes.POINTER(MONITORINFOEXW)]
user32.GetMonitorInfoW.restype = wintypes.BOOL

dxva2.GetNumberOfPhysicalMonitorsFromHMONITOR.argtypes = [wintypes.HMONITOR, ctypes.POINTER(wintypes.DWORD)]
dxva2.GetNumberOfPhysicalMonitorsFromHMONITOR.restype = wintypes.BOOL
dxva2.GetPhysicalMonitorsFromHMONITOR.argtypes = [
    wintypes.HMONITOR, wintypes.DWORD, ctypes.POINTER(PHYSICAL_MONITOR),
]
dxva2.GetPhysicalMonitorsFromHMONITOR.restype = wintypes.BOOL
dxva2.DestroyPhysicalMonitors.argtypes = [wintypes.DWORD, ctypes.POINTER(PHYSICAL_MONITOR)]
dxva2.DestroyPhysicalMonitors.restype = wintypes.BOOL
dxva2.GetCapabilitiesStringLength.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
dxva2.GetCapabilitiesStringLength.restype = wintypes.BOOL
dxva2.CapabilitiesRequestAndCapabilitiesReply.argtypes = [wintypes.HANDLE, ctypes.c_char_p, wintypes.DWORD]
dxva2.CapabilitiesRequestAndCapabilitiesReply.restype = wintypes.BOOL
dxva2.GetVCPFeatureAndVCPFeatureReply.argtypes = [
    wintypes.HANDLE, ctypes.c_ubyte, ctypes.POINTER(wintypes.DWORD),
    ctypes.POINTER(wintypes.DWORD), ctypes.POINTER(wintypes.DWORD),
]
dxva2.GetVCPFeatureAndVCPFeatureReply.restype = wintypes.BOOL
dxva2.SetVCPFeature.argtypes = [wintypes.HANDLE, ctypes.c_ubyte, wintypes.DWORD]
dxva2.SetVCPFeature.restype = wintypes.BOOL


class DdcError(RuntimeError):
    pass


@dataclass
class _Candidate:
    device: str
    rect: tuple[int, int, int, int]
    description: str
    pm: PHYSICAL_MONITOR
    closed: bool = False

    @property
    def handle(self):
        return self.pm.hPhysicalMonitor

    def close(self):
        if not self.closed:
            dxva2.DestroyPhysicalMonitors(1, ctypes.byref(self.pm))
            self.closed = True


_enum_callback_ref = None


def _enumerate_candidates() -> list[_Candidate]:
    global _enum_callback_ref
    found: list[_Candidate] = []

    def callback(hmon, hdc, rect, lparam):
        info = MONITORINFOEXW()
        info.cbSize = ctypes.sizeof(MONITORINFOEXW)
        if not user32.GetMonitorInfoW(hmon, ctypes.byref(info)):
            return True
        count = wintypes.DWORD()
        if not dxva2.GetNumberOfPhysicalMonitorsFromHMONITOR(hmon, ctypes.byref(count)):
            return True
        if count.value == 0:
            return True
        arr = (PHYSICAL_MONITOR * count.value)()
        if not dxva2.GetPhysicalMonitorsFromHMONITOR(hmon, count.value, arr):
            return True
        rc = info.rcMonitor
        for i in range(count.value):
            found.append(_Candidate(
                device=info.szDevice,
                rect=(rc.left, rc.top, rc.right - rc.left, rc.bottom - rc.top),
                description=arr[i].szPhysicalMonitorDescription,
                pm=arr[i],
            ))
        return True

    enum_callback = MONITORENUMPROC(callback)
    # 保持 ctypes 回调对象在枚举期间存活，避免被 GC 回收。
    _enum_callback_ref = enum_callback
    try:
        user32.EnumDisplayMonitors(None, None, enum_callback, 0)
    finally:
        _enum_callback_ref = None
    return found


def read_capabilities(handle) -> str | None:
    length = wintypes.DWORD()
    if not dxva2.GetCapabilitiesStringLength(handle, ctypes.byref(length)) or length.value == 0:
        return None
    buf = ctypes.create_string_buffer(length.value)
    if not dxva2.CapabilitiesRequestAndCapabilitiesReply(handle, buf, length.value):
        return None
    return buf.value.decode("ascii", "ignore").strip("\x00")


def _extract_group(text: str, name: str) -> str | None:
    marker = name + "("
    start = text.find(marker)
    if start < 0:
        return None
    i = start + len(marker)
    depth = 1
    while i < len(text):
        if text[i] == "(":
            depth += 1
        elif text[i] == ")":
            depth -= 1
            if depth == 0:
                return text[start + len(marker):i]
        i += 1
    return None


def parse_capabilities(caps: str) -> dict[int, tuple[int, ...] | None]:
    group = _extract_group(caps, "vcp")
    result: dict[int, tuple[int, ...] | None] = {}
    if not group:
        return result
    i = 0
    while i < len(group):
        while i < len(group) and group[i].isspace():
            i += 1
        if i + 2 > len(group):
            break
        token = group[i:i + 2]
        if not re.fullmatch(r"[0-9A-Fa-f]{2}", token):
            i += 1
            continue
        code = int(token, 16)
        i += 2
        while i < len(group) and group[i].isspace():
            i += 1
        values = None
        if i < len(group) and group[i] == "(":
            end = group.find(")", i)
            if end < 0:
                end = len(group)
            raw = group[i + 1:end].split()
            parsed = tuple(sorted({int(x, 16) for x in raw if re.fullmatch(r"[0-9A-Fa-f]{2}", x)}))
            values = parsed or None
            i = end + 1
        result[code] = values
    return result


class DdcMonitor:
    def __init__(self, candidate: _Candidate, capabilities: str, vcp: dict):
        self._candidate = candidate
        self.capabilities = capabilities
        self.vcp = vcp
        self.device = candidate.device
        self.rect = candidate.rect
        self.description = candidate.description
        self._closed = False

    @property
    def handle(self):
        return self._candidate.handle

    @classmethod
    def open_best(cls) -> "DdcMonitor":
        candidates = _enumerate_candidates()
        if not candidates:
            raise DdcError("未检测到显示器")

        best: tuple[float, _Candidate, str, dict] | None = None
        for candidate in candidates:
            caps = read_capabilities(candidate.handle)
            if not caps:
                candidate.close()
                continue
            vcp = parse_capabilities(caps)
            if BRIGHTNESS not in vcp and CONTRAST not in vcp:
                candidate.close()
                continue
            area = candidate.rect[2] * candidate.rect[3]
            score = (
                (1000 if BRIGHTNESS in vcp else 0)
                + (400 if CONTRAST in vcp else 0)
                + (300 if INPUT_SOURCE in vcp else 0)
                + (200 if COLOR_PRESET in vcp else 0)
                + min(area / 1_000_000, 9)
            )
            if best is None or score > best[0]:
                if best is not None:
                    best[1].close()
                best = (score, candidate, caps, vcp)
            else:
                candidate.close()

        if best is None:
            raise DdcError("未找到支持 DDC/CI 的显示器，请在显示器菜单中开启 DDC/CI")

        _, candidate, caps, vcp = best
        return cls(candidate, caps, vcp)

    def read_vcp(self, code: int) -> tuple[int, int]:
        vcp_type = wintypes.DWORD()
        current = wintypes.DWORD()
        maximum = wintypes.DWORD()
        last_error = 0
        for attempt in range(3):
            ok = dxva2.GetVCPFeatureAndVCPFeatureReply(
                self.handle, code, ctypes.byref(vcp_type), ctypes.byref(current), ctypes.byref(maximum),
            )
            if ok:
                return current.value, maximum.value
            last_error = ctypes.get_last_error()
            time.sleep(0.06)
        raise DdcError(f"读取 VCP 0x{code:02X} 失败（错误 {last_error}）")

    def read_all(self) -> dict[int, tuple[int, int]]:
        values: dict[int, tuple[int, int]] = {}
        for code in RELEVANT_CODES:
            if code not in self.vcp:
                continue
            try:
                values[code] = self.read_vcp(code)
            except DdcError:
                continue
            time.sleep(0.01)
        return values

    def set_vcp(self, code: int, value: int) -> bool:
        for attempt in range(2):
            if dxva2.SetVCPFeature(self.handle, code, int(value)):
                return True
            if attempt == 0:
                time.sleep(0.08)
        return False

    def trigger(self, code: int) -> bool:
        # 本显示器要求恢复类指令 value=1；value=0 会返回成功但显示器不执行。
        return dxva2.SetVCPFeature(self.handle, code, 1)

    def close(self):
        if not self._closed:
            self._candidate.close()
            self._closed = True


class DdcWorker(QThread):
    stateReady = pyqtSignal(dict)
    failed = pyqtSignal(str)
    valuesSynced = pyqtSignal(dict)
    setFinished = pyqtSignal(int, int, bool)
    triggerFinished = pyqtSignal(int, bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._commands: queue.Queue = queue.Queue()
        self._monitor: DdcMonitor | None = None
        self._stopping = False

    def submit_set(self, code: int, value: int):
        self._commands.put(("set", code, value))

    def submit_trigger(self, code: int):
        self._commands.put(("trigger", code))

    def refresh(self):
        self._commands.put(("refresh",))

    def request_stop(self):
        self._stopping = True
        self._commands.put(("stop",))

    def run(self):
        try:
            self._monitor = DdcMonitor.open_best()
        except Exception as exc:
            self.failed.emit(str(exc))
            return

        monitor = self._monitor
        values = monitor.read_all()
        self.stateReady.emit({
            "device": monitor.device,
            "rect": list(monitor.rect),
            "description": monitor.description,
            "capabilities": monitor.capabilities,
            "vcp": {code: (list(vals) if vals else None) for code, vals in monitor.vcp.items()},
            "values": {code: [cur, mx] for code, (cur, mx) in values.items()},
        })

        while not self._stopping:
            try:
                command = self._commands.get()
            except Exception:
                break
            if command[0] == "stop":
                break
            if command[0] == "set":
                _, code, value = command
                ok = monitor.set_vcp(code, value)
                self.setFinished.emit(code, value, ok)
            elif command[0] == "trigger":
                _, code = command
                ok = monitor.trigger(code)
                self.triggerFinished.emit(code, ok)
            elif command[0] == "refresh":
                self.valuesSynced.emit({
                    code: [cur, mx] for code, (cur, mx) in monitor.read_all().items()
                })

        monitor.close()
        self._monitor = None
