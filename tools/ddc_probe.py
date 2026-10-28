import ctypes
from ctypes import wintypes

user32 = ctypes.WinDLL("user32", use_last_error=True)
dxva2 = ctypes.WinDLL("dxva2", use_last_error=True)


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
dxva2.GetPhysicalMonitorsFromHMONITOR.argtypes = [wintypes.HMONITOR, wintypes.DWORD, ctypes.POINTER(PHYSICAL_MONITOR)]
dxva2.DestroyPhysicalMonitors.argtypes = [wintypes.DWORD, ctypes.POINTER(PHYSICAL_MONITOR)]
dxva2.GetMonitorCapabilities.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD), ctypes.POINTER(wintypes.DWORD)]
dxva2.GetCapabilitiesStringLength.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
dxva2.CapabilitiesRequestAndCapabilitiesReply.argtypes = [wintypes.HANDLE, ctypes.c_char_p, wintypes.DWORD]
dxva2.GetVCPFeatureAndVCPFeatureReply.argtypes = [
    wintypes.HANDLE, ctypes.c_ubyte, ctypes.POINTER(wintypes.DWORD),
    ctypes.POINTER(wintypes.DWORD), ctypes.POINTER(wintypes.DWORD),
]
dxva2.SetVCPFeature.argtypes = [wintypes.HANDLE, ctypes.c_ubyte, wintypes.DWORD]

VCP_NAMES = {
    0x10: "Brightness", 0x12: "Contrast", 0x14: "ColorPreset", 0x16: "RedGain",
    0x18: "GreenGain", 0x1A: "BlueGain", 0x52: "VSharpness", 0x60: "InputSource",
    0x62: "Volume", 0x6C: "Hue", 0x6E: "Sharpness", 0x87: "Sharpness",
    0x8D: "AudioMute", 0xAC: "HSharpness", 0xAE: "Hue", 0xB6: "DisplayMode",
    0xD6: "PowerMode", 0xDC: "DisplayUsageTime", 0xDB: "Scaling",
}


def read_vcp(handle, code):
    vcp_type = wintypes.DWORD()
    cur = wintypes.DWORD()
    mx = wintypes.DWORD()
    ok = dxva2.GetVCPFeatureAndVCPFeatureReply(
        handle, code, ctypes.byref(vcp_type), ctypes.byref(cur), ctypes.byref(mx)
    )
    if not ok:
        return None
    return cur.value, mx.value


def main():
    monitors = []

    def enum_cb(hmon, hdc, rect, lparam):
        info = MONITORINFOEXW()
        info.cbSize = ctypes.sizeof(MONITORINFOEXW)
        if user32.GetMonitorInfoW(hmon, ctypes.byref(info)):
            count = wintypes.DWORD()
            if dxva2.GetNumberOfPhysicalMonitorsFromHMONITOR(hmon, ctypes.byref(count)) and count.value:
                arr = (PHYSICAL_MONITOR * count.value)()
                if dxva2.GetPhysicalMonitorsFromHMONITOR(hmon, count.value, arr):
                    for i in range(count.value):
                        monitors.append((info.szDevice, info.rcMonitor, arr[i]))
        return True

    user32.EnumDisplayMonitors(None, None, MONITORENUMPROC(enum_cb), 0)

    for dev, rc, pm in monitors:
        h = pm.hPhysicalMonitor
        print("=" * 70)
        print(f"{dev}  {rc.right - rc.left}x{rc.bottom - rc.top}  desc={pm.szPhysicalMonitorDescription!r}")
        caps, temps = wintypes.DWORD(), wintypes.DWORD()
        if dxva2.GetMonitorCapabilities(h, ctypes.byref(caps), ctypes.byref(temps)):
            print(f"caps=0x{caps.value:08X} colorTemps=0x{temps.value:08X}")
        else:
            print("GetMonitorCapabilities failed")
        length = wintypes.DWORD()
        if dxva2.GetCapabilitiesStringLength(h, ctypes.byref(length)) and length.value:
            buf = ctypes.create_string_buffer(length.value)
            if dxva2.CapabilitiesRequestAndCapabilitiesReply(h, buf, length.value):
                print("capabilities:", buf.value.decode("ascii", "replace"))
        else:
            print("capabilities string unavailable")
        for code, name in VCP_NAMES.items():
            res = read_vcp(h, code)
            if res:
                print(f"  0x{code:02X} {name:<14} current={res[0]:<5} max={res[1]}")

    for _, _, pm in monitors:
        dxva2.DestroyPhysicalMonitors(1, ctypes.byref(pm))


if __name__ == "__main__":
    main()
