from __future__ import annotations

from uuid import uuid4

from PySide6.QtCore import SLOT, QObject, QUrl, Signal, Slot
from PySide6.QtDBus import (
    QDBusConnection,
    QDBusInterface,
    QDBusMessage,
    QDBusObjectPath,
    QDBusPendingCallWatcher,
    QDBusVariant,
)
from PySide6.QtGui import QImage

PORTAL_SERVICE = "org.freedesktop.portal.Desktop"
PORTAL_PATH = "/org/freedesktop/portal/desktop"
SCREENSHOT_INTERFACE = "org.freedesktop.portal.Screenshot"
REQUEST_INTERFACE = "org.freedesktop.portal.Request"
# PySide6's runtime requires SLOT()'s string here, while its type stub
# incorrectly declares the parameter as bytes.
RESPONSE_SLOT = SLOT("_on_response(uint,QVariantMap)")


def unwrap_dbus_value(value: object) -> object:
    return value.variant() if isinstance(value, QDBusVariant) else value


def screenshot_path_from_results(results: dict[str, object]) -> str:
    value = unwrap_dbus_value(results.get("uri"))
    if not isinstance(value, str) or not value:
        raise ValueError("screenshot portal response did not include an image URI")
    path = QUrl(value).toLocalFile()
    if not path:
        raise ValueError("screenshot portal returned a non-local image URI")
    return path


class PortalScreenshotService(QObject):
    captured = Signal(QImage)
    cancelled = Signal()
    failed = Signal(str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._connection = QDBusConnection.sessionBus()
        self._request_path: str | None = None
        self._watcher: QDBusPendingCallWatcher | None = None

    @property
    def is_pending(self) -> bool:
        return self._watcher is not None or self._request_path is not None

    def request(self) -> None:
        if self.is_pending:
            return
        if not self._connection.isConnected():
            self.failed.emit("the desktop portal session bus is unavailable")
            return

        interface = QDBusInterface(
            PORTAL_SERVICE,
            PORTAL_PATH,
            SCREENSHOT_INTERFACE,
            self._connection,
            self,
        )
        if not interface.isValid():
            self.failed.emit("the desktop screenshot portal is unavailable")
            return

        token = f"objectsnip_{uuid4().hex}"
        options = {
            "handle_token": token,
            "interactive": False,
            "modal": False,
        }
        pending = interface.asyncCallWithArgumentList("Screenshot", ["", options])
        watcher = QDBusPendingCallWatcher(pending, self)
        watcher.finished.connect(self._on_request_created)
        self._watcher = watcher

    @Slot(QDBusPendingCallWatcher)
    def _on_request_created(self, watcher: QDBusPendingCallWatcher) -> None:
        if watcher is not self._watcher:
            watcher.deleteLater()
            return
        self._watcher = None
        reply = watcher.reply()
        watcher.deleteLater()

        if reply.type() == QDBusMessage.MessageType.ErrorMessage:
            self.failed.emit(reply.errorMessage() or reply.errorName())
            return
        arguments = reply.arguments()
        if not arguments or not isinstance(arguments[0], QDBusObjectPath):
            self.failed.emit("the screenshot portal returned an invalid request handle")
            return

        request_path = arguments[0].path()
        connected = self._connection.connect(
            PORTAL_SERVICE,
            request_path,
            REQUEST_INTERFACE,
            "Response",
            self,
            RESPONSE_SLOT,  # pyright: ignore[reportArgumentType]
        )
        if not connected:
            self.failed.emit("could not subscribe to the screenshot portal response")
            return
        self._request_path = request_path

    @Slot("uint", "QVariantMap")
    def _on_response(self, response: int, results: dict[str, object]) -> None:
        self._disconnect_response()
        if response == 1:
            self.cancelled.emit()
            return
        if response != 0:
            self.failed.emit("the desktop screenshot request failed")
            return

        try:
            path = screenshot_path_from_results(results)
            image = QImage(path)
            if image.isNull():
                raise ValueError("the screenshot portal returned an unreadable image")
            image.setDevicePixelRatio(1.0)
        except ValueError as exc:
            self.failed.emit(str(exc))
            return
        self.captured.emit(image)

    def _disconnect_response(self) -> None:
        if self._request_path is None:
            return
        self._connection.disconnect(
            PORTAL_SERVICE,
            self._request_path,
            REQUEST_INTERFACE,
            "Response",
            self,
            RESPONSE_SLOT,  # pyright: ignore[reportArgumentType]
        )
        self._request_path = None
