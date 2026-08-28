from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QObject, Slot
from PySide6.QtGui import QAction, QGuiApplication, QImage, QScreen
from PySide6.QtWidgets import QApplication, QMenu, QMessageBox, QStyle, QSystemTrayIcon

from objectsnip.capture.portal import PortalScreenshotService
from objectsnip.capture.screen import (
    capture_screen,
    image_is_uniform,
    screen_at_pointer,
)
from objectsnip.debug_capture import DebugCaptureSession, DebugCaptureWriter
from objectsnip.domain.geometry import Rect
from objectsnip.shortcuts.portal import PortalGlobalShortcutService
from objectsnip.ui.overlay import CaptureOverlay


class ObjectSnipApplication(QObject):
    def __init__(
        self,
        application: QApplication,
        debug_capture_directory: Path | None = None,
    ) -> None:
        super().__init__(application)
        self._application = application
        self._overlay: CaptureOverlay | None = None
        self._capture_screen: QScreen | None = None
        self._debug_writer = (
            DebugCaptureWriter(debug_capture_directory)
            if debug_capture_directory is not None
            else None
        )
        self._debug_session: DebugCaptureSession | None = None
        self._portal = PortalScreenshotService(self)
        self._portal.captured.connect(self._portal_captured)
        self._portal.cancelled.connect(self._portal_cancelled)
        self._portal.failed.connect(self._capture_failed)
        self._shortcut = PortalGlobalShortcutService(self)
        self._shortcut.activated.connect(self.start_capture)
        self._shortcut.failed.connect(self._shortcut_failed)
        application.aboutToQuit.connect(self._shortcut.stop)

        icon = application.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)
        self._tray = QSystemTrayIcon(icon, self)
        self._tray.setToolTip("ObjectSnip")

        menu = QMenu()
        capture_action = QAction("Capture region", menu)
        capture_action.triggered.connect(self.start_capture)
        menu.addAction(capture_action)
        menu.addSeparator()
        quit_action = QAction("Quit", menu)
        quit_action.triggered.connect(application.quit)
        menu.addAction(quit_action)
        self._tray.setContextMenu(menu)
        self._tray.activated.connect(self._tray_activated)
        self._tray.show()
        self._shortcut.start()

    @Slot()
    def start_capture(self) -> None:
        if self._overlay is not None and self._overlay.isVisible():
            self._overlay.raise_()
            self._overlay.activateWindow()
            return

        if self._portal.is_pending:
            return

        screen = screen_at_pointer()
        self._capture_screen = screen
        if QGuiApplication.platformName() == "wayland":
            self._portal.request()
            return

        try:
            screenshot = capture_screen(screen)
            if image_is_uniform(screenshot):
                raise RuntimeError("screen capture returned only a uniform image")
        except RuntimeError as exc:
            self._capture_failed(str(exc))
            return
        self._open_overlay(screenshot, screen)

    def _open_overlay(self, screenshot: QImage, screen: QScreen) -> None:
        if self._debug_writer is not None:
            try:
                self._debug_session = self._debug_writer.begin(screenshot)
            except (OSError, ValueError) as exc:
                QMessageBox.warning(None, "ObjectSnip debug capture", str(exc))
                self._debug_session = None

        overlay = CaptureOverlay(screenshot, self._region_locked)
        overlay.destroyed.connect(self._overlay_destroyed)
        overlay.winId()
        window = overlay.windowHandle()
        if window is not None:
            window.setScreen(screen)
        overlay.setGeometry(screen.geometry())
        self._overlay = overlay
        overlay.showFullScreen()
        overlay.raise_()
        overlay.activateWindow()

    @Slot(QImage)
    def _portal_captured(self, screenshot: QImage) -> None:
        screen = self._capture_screen or screen_at_pointer()
        self._capture_screen = None
        self._open_overlay(screenshot, screen)

    @Slot()
    def _portal_cancelled(self) -> None:
        self._capture_screen = None

    @Slot(str)
    def _capture_failed(self, message: str) -> None:
        self._capture_screen = None
        QMessageBox.critical(None, "ObjectSnip", message)

    @Slot(str)
    def _shortcut_failed(self, message: str) -> None:
        self._tray.showMessage(
            "Global shortcut unavailable",
            message,
            QSystemTrayIcon.MessageIcon.Warning,
            5000,
        )

    @Slot(QSystemTrayIcon.ActivationReason)
    def _tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.start_capture()

    def _region_locked(self, crop: QImage, bounds: Rect) -> None:
        debug_message = ""
        if self._debug_session is not None:
            try:
                path = self._debug_session.save_region(crop)
                debug_message = f"\nSaved debug region to {path.resolve()}."
            except (OSError, ValueError) as exc:
                QMessageBox.warning(None, "ObjectSnip debug capture", str(exc))
        self._tray.showMessage(
            "Context region locked",
            f"Prepared {crop.width()} × {crop.height()} pixels at "
            f"({bounds.left}, {bounds.top}).{debug_message}",
            QSystemTrayIcon.MessageIcon.NoIcon,
            2500,
        )

    @Slot()
    def _overlay_destroyed(self) -> None:
        self._overlay = None
        self._debug_session = None


def run(debug_capture_directory: Path | None = None) -> int:
    application = QApplication([sys.argv[0]])
    application.setApplicationName("ObjectSnip")
    application.setQuitOnLastWindowClosed(False)

    if not QSystemTrayIcon.isSystemTrayAvailable():
        QMessageBox.critical(
            None,
            "ObjectSnip",
            "No system tray is available in this desktop session.",
        )
        return 1

    ObjectSnipApplication(application, debug_capture_directory)
    return application.exec()
