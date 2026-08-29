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
from objectsnip.segmentation.image import image_data_from_qimage
from objectsnip.segmentation.interface import (
    ImageData,
    ImageEncoding,
    ImageSegmenter,
    PredictionRequest,
    SegmentationResult,
)
from objectsnip.segmentation.service import ImageEncodingService
from objectsnip.shortcuts.portal import PortalGlobalShortcutService
from objectsnip.ui.overlay import CaptureOverlay
from objectsnip.ui.selection_window import ObjectSelectionWindow


class ObjectSnipApplication(QObject):
    def __init__(
        self,
        application: QApplication,
        segmenter: ImageSegmenter,
        debug_capture_directory: Path | None = None,
    ) -> None:
        super().__init__(application)
        self._application = application
        self._overlay: CaptureOverlay | None = None
        self._selection_window: ObjectSelectionWindow | None = None
        self._selection_image: ImageData | None = None
        self._encoding_request: int | None = None
        self._prediction_request: int | None = None
        self._image_encoding: ImageEncoding | None = None
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
        self._encoding = ImageEncodingService(segmenter, self)
        self._encoding.encoded.connect(self._image_encoded)
        self._encoding.failed.connect(self._image_encoding_failed)
        self._encoding.predicted.connect(self._mask_predicted)
        self._encoding.prediction_failed.connect(self._mask_prediction_failed)
        application.aboutToQuit.connect(self._encoding.close)

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
        del bounds
        if self._debug_session is not None:
            try:
                self._debug_session.save_region(crop)
            except (OSError, ValueError) as exc:
                QMessageBox.warning(None, "ObjectSnip debug capture", str(exc))

        if self._selection_window is not None:
            self._selection_window.close()
        selection_window = ObjectSelectionWindow(crop)
        selection_window.retry_requested.connect(self._retry_image_encoding)
        selection_window.prompts_changed.connect(self._prompts_changed)
        selection_window.destroyed.connect(
            lambda _object=None, window=selection_window: (
                self._selection_window_destroyed(window)
            )
        )
        self._selection_window = selection_window
        self._selection_image = image_data_from_qimage(crop)
        self._image_encoding = None
        self._start_image_encoding()
        selection_window.show()
        selection_window.raise_()
        selection_window.activateWindow()

    def _start_image_encoding(self) -> None:
        if self._selection_window is None or self._selection_image is None:
            return
        self._selection_window.show_preparing()
        self._encoding_request = self._encoding.encode(self._selection_image)

    @Slot()
    def _retry_image_encoding(self) -> None:
        self._start_image_encoding()

    @Slot(int, object)
    def _image_encoded(self, request: int, encoding: object) -> None:
        if request != self._encoding_request or self._selection_window is None:
            return
        if not isinstance(encoding, ImageEncoding):
            self._selection_window.show_encoding_error(
                "the segmentation backend returned invalid encoding metadata"
            )
            return
        self._image_encoding = encoding
        self._selection_window.show_ready()

    @Slot(object)
    def _prompts_changed(self, points: object) -> None:
        if self._selection_window is None or not isinstance(points, tuple):
            return
        if not points:
            self._encoding.invalidate()
            self._prediction_request = None
            self._selection_window.clear_mask()
            return
        self._selection_window.show_predicting()
        self._prediction_request = self._encoding.predict(
            PredictionRequest(points=points)
        )

    @Slot(int, object)
    def _mask_predicted(self, request: int, result: object) -> None:
        if request != self._prediction_request or self._selection_window is None:
            return
        if not isinstance(result, SegmentationResult):
            self._selection_window.show_prediction_error(
                "the segmentation backend returned an invalid result"
            )
            return
        best = int(result.scores.argmax())
        self._selection_window.set_mask(result.masks[best])

    @Slot(int, str)
    def _mask_prediction_failed(self, request: int, message: str) -> None:
        if request == self._prediction_request and self._selection_window is not None:
            self._selection_window.show_prediction_error(message)

    @Slot(int, str)
    def _image_encoding_failed(self, request: int, message: str) -> None:
        if request != self._encoding_request or self._selection_window is None:
            return
        self._selection_window.show_encoding_error(message)

    def _selection_window_destroyed(self, window: ObjectSelectionWindow) -> None:
        if self._selection_window is window:
            self._encoding.invalidate()
            self._selection_window = None
            self._selection_image = None
            self._encoding_request = None
            self._prediction_request = None
            self._image_encoding = None

    @Slot()
    def _overlay_destroyed(self) -> None:
        self._overlay = None
        self._debug_session = None


def run(
    segmenter: ImageSegmenter,
    debug_capture_directory: Path | None = None,
) -> int:
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

    ObjectSnipApplication(application, segmenter, debug_capture_directory)
    return application.exec()
