import os
import sys
import time
from pathlib import Path


def main() -> int:
    args = sys.argv[1:]
    screenshot_mode = "--screenshots" in args
    if screenshot_mode:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    try:
        from ctypes import windll
        windll.shell32.SetCurrentProcessExplicitAppUserModelID("Redmi.OSD")
    except Exception:
        pass

    from PyQt6.QtGui import QFontDatabase
    from PyQt6.QtNetwork import QLocalServer, QLocalSocket
    from PyQt6.QtWidgets import QApplication

    from redmiosd import theme
    from redmiosd.app import MainWindow

    app = QApplication(sys.argv)
    app.setApplicationName("Redmi OSD")
    app.setApplicationDisplayName("Redmi OSD")
    app.setQuitOnLastWindowClosed(False)
    if screenshot_mode:
        font_dir = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"
        for name in ("segoeui.ttf", "segoeuib.ttf", "seguisb.ttf", "msyh.ttc", "msyhbd.ttc", "msyhsb.ttc"):
            candidate = font_dir / name
            if candidate.exists():
                QFontDatabase.addApplicationFont(str(candidate))
    theme.setup_fonts(app)
    app.setStyleSheet(theme.QSS)

    if screenshot_mode:
        index = args.index("--screenshots")
        out_dir = Path(args[index + 1]) if index + 1 < len(args) else Path("screenshots")
        out_dir = out_dir.resolve()
        window = MainWindow(headless=True)
        window.show()
        deadline = time.monotonic() + 9
        while not window._finished_connecting and time.monotonic() < deadline:
            app.processEvents()
            time.sleep(0.05)
        app.processEvents()
        print("CONNECTED" if window._state is not None else "NOT_CONNECTED")
        for path in window.capture_pages(out_dir):
            print(path)
        window.close()
        app.processEvents()
        return 0

    socket = QLocalSocket()
    socket.connectToServer("RedmiOSD.singleton")
    if socket.waitForConnected(200):
        socket.write(b"show")
        socket.flush()
        socket.waitForBytesWritten(200)
        socket.disconnectFromServer()
        return 0

    QLocalServer.removeServer("RedmiOSD.singleton")
    window = MainWindow()
    server = QLocalServer(window)
    server.listen("RedmiOSD.singleton")

    def new_connection():
        connection = server.nextPendingConnection()
        if connection is not None:
            connection.disconnectFromServer()
        window.reveal()

    server.newConnection.connect(new_connection)
    window._server = server

    if "--silent" in args:
        window.start_hidden()
    else:
        window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
