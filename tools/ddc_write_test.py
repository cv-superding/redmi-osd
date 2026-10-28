import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from redmiosd.monitor import (
    BRIGHTNESS, COLOR_PRESET, CONTRAST, INPUT_SOURCE, VOLUME, DdcMonitor,
)

CODES = (
    (BRIGHTNESS, "亮度"),
    (CONTRAST, "对比度"),
    (COLOR_PRESET, "色彩预设"),
    (VOLUME, "音量"),
    (INPUT_SOURCE, "输入源"),
)

monitor = DdcMonitor.open_best()
try:
    print(f"monitor: {monitor.device} {monitor.rect}")
    print(f"capabilities: {monitor.capabilities}")
    for code, name in CODES:
        if code not in monitor.vcp:
            print(f"{name}: unsupported")
            continue
        before, maximum = monitor.read_vcp(code)
        ok = monitor.set_vcp(code, before)
        after, _ = monitor.read_vcp(code)
        print(f"{name} 0x{code:02X}: read={before}/{maximum} set_same={ok} readback={after}")
        assert ok, f"SetVCP {name} failed"
        assert after == before, f"{name} changed unexpectedly"
    print("OK: all same-value DDC writes accepted, no setting was changed")
finally:
    monitor.close()
