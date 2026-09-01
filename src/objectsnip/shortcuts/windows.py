from __future__ import annotations

import ctypes
from ctypes import wintypes

from PySide6.QtCore import QAbstractNativeEventFilter, QByteArray, QObject, Signal, Slot
from PySide6.QtWidgets import QApplication

WM_HOTKEY = 0x0312
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
VK_O = ord("O")
HOTKEY_ID = 0x4F53  # "OS"


class MSG(ctypes.Structure):
    _fields_ = [
        ("hwnd", wintypes.HWND),
        ("message", wintypes.UINT),
        ("wParam", wintypes.WPARAM),
        ("lParam", wintypes.LPARAM),
        ("time", wintypes.DWORD),
        ("pt", wintypes.POINT),
    ]


class WindowsGlobalShortcutService(QObject, QAbstractNativeEventFilter):
    """Register Win+Shift+O on the Qt GUI thread and receive WM_HOTKEY."""

    activated = Signal()
    failed = Signal(str)

    def __init__(self, parent: QObject | None = None) -> None:
        QObject.__init__(self, parent)
        QAbstractNativeEventFilter.__init__(self)
        self._registered = False

    def start(self) -> None:
        if self._registered:
            return
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        if not user32.RegisterHotKey(None, HOTKEY_ID, MOD_WIN | MOD_SHIFT, VK_O):
            error = ctypes.get_last_error()
            detail = ctypes.WinError(error)
            self.failed.emit(f"Win+Shift+O could not be registered: {detail}")
            return
        application = QApplication.instance()
        if application is None:
            user32.UnregisterHotKey(None, HOTKEY_ID)
            self.failed.emit("Win+Shift+O requires a running application")
            return
        application.installNativeEventFilter(self)
        self._registered = True

    @Slot()
    def stop(self) -> None:
        if not self._registered:
            return
        application = QApplication.instance()
        if application is not None:
            application.removeNativeEventFilter(self)
        ctypes.WinDLL("user32", use_last_error=True).UnregisterHotKey(None, HOTKEY_ID)
        self._registered = False

    def nativeEventFilter(
        self,
        event_type: QByteArray | bytes | bytearray | memoryview[int],
        message: int,
    ) -> tuple[bool, int]:
        del event_type
        native_message = ctypes.cast(
            int(message), ctypes.POINTER(MSG)
        ).contents
        if native_message.message == WM_HOTKEY and native_message.wParam == HOTKEY_ID:
            self.activated.emit()
            return True, 0
        return False, 0
