from __future__ import annotations

import sys
from datetime import datetime
from importlib import resources
from pathlib import Path

import numpy as np
from PySide6.QtCore import QObject, Slot
from PySide6.QtGui import QAction, QGuiApplication, QIcon, QImage, QPixmap, QScreen
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QMenu,
    QMessageBox,
    QSystemTrayIcon,
)

from objectsnip.capture.portal import PortalScreenshotService
from objectsnip.capture.screen import (
    capture_screen,
    image_is_uniform,
    screen_at_pointer,
)
from objectsnip.debug_capture import DebugCaptureSession, DebugCaptureWriter
from objectsnip.domain.geometry import Rect
from objectsnip.export.cutout import build_cutout
from objectsnip.export.file import save_png
from objectsnip.segmentation.image import image_data_from_qimage
from objectsnip.segmentation.interface import (
    ImageData,
    ImageEncoding,
    ImageSegmenter,
    PredictionRequest,
    SegmentationResult,
)
from objectsnip.segmentation.service import ImageEncodingService
from objectsnip.shortcuts import create_global_shortcut_service
from objectsnip.ui.overlay import CaptureOverlay
from objectsnip.ui.selection_window import ObjectSelectionWindow


def application_icon() -> QIcon:
    """Load the application icon from package data, including zipped wheels."""
    icon_data = (
        resources.files("objectsnip").joinpath("assets/objectsnip-512.png").read_bytes()
    )
    pixmap = QPixmap()
    if not pixmap.loadFromData(icon_data):
        raise RuntimeError("the packaged ObjectSnip icon could not be loaded")
    return QIcon(pixmap)


def rank_segmentation_result(result: SegmentationResult) -> SegmentationResult:
    order = np.argsort(-result.scores, stable=True)
    return SegmentationResult(
        masks=np.ascontiguousarray(result.masks[order]),
        scores=np.ascontiguousarray(result.scores[order]),
        low_resolution_logits=np.ascontiguousarray(result.low_resolution_logits[order]),
    )


def refinement_mask_input(
    result: SegmentationResult | None, active_candidate: int
) -> np.ndarray | None:
    if result is None:
        return None
    if not 0 <= active_candidate < len(result.scores):
        raise IndexError("active candidate is out of range")
    return np.ascontiguousarray(
        result.low_resolution_logits[active_candidate : active_candidate + 1],
        dtype=np.float32,
    )


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
        self._segmentation_result: SegmentationResult | None = None
        self._active_candidate = 0
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
        self._shortcut = create_global_shortcut_service(self)
        self._shortcut.activated.connect(self.start_capture)
        self._shortcut.failed.connect(self._shortcut_failed)
        application.aboutToQuit.connect(self._shortcut.stop)
        self._encoding = ImageEncodingService(segmenter, self)
        self._encoding.encoded.connect(self._image_encoded)
        self._encoding.failed.connect(self._image_encoding_failed)
        self._encoding.predicted.connect(self._mask_predicted)
        self._encoding.prediction_failed.connect(self._mask_prediction_failed)
        application.aboutToQuit.connect(self._encoding.close)

        self._tray = QSystemTrayIcon(application.windowIcon(), self)
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
        selection_window.candidate_selected.connect(self._candidate_selected)
        selection_window.copy_requested.connect(self._copy_cutout)
        selection_window.save_as_requested.connect(self._save_cutout_as)
        selection_window.destroyed.connect(
            lambda _object=None, window=selection_window: (
                self._selection_window_destroyed(window)
            )
        )
        self._selection_window = selection_window
        self._selection_image = image_data_from_qimage(crop)
        self._image_encoding = None
        self._segmentation_result = None
        self._active_candidate = 0
        self._start_image_encoding()
        selection_window.showMaximized()
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
            self._segmentation_result = None
            self._active_candidate = 0
            self._selection_window.clear_candidates()
            return
        mask_input = refinement_mask_input(
            self._segmentation_result, self._active_candidate
        )
        self._selection_window.show_predicting()
        self._prediction_request = self._encoding.predict(
            PredictionRequest(points=points, mask_input=mask_input)
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
        ranked = rank_segmentation_result(result)
        self._segmentation_result = ranked
        self._active_candidate = 0
        self._selection_window.set_candidates(ranked.masks, ranked.scores)

    @Slot(int)
    def _candidate_selected(self, index: int) -> None:
        if self._segmentation_result is None:
            return
        if not 0 <= index < len(self._segmentation_result.scores):
            return
        self._active_candidate = index

    def _active_cutout_image(self) -> QImage:
        if self._selection_image is None or self._segmentation_result is None:
            raise ValueError("select an object before exporting")
        if not 0 <= self._active_candidate < len(self._segmentation_result.masks):
            raise ValueError("the active mask is unavailable")
        cutout = build_cutout(
            self._selection_image,
            self._segmentation_result.masks[self._active_candidate],
        )
        height, width, _channels = cutout.rgba.shape
        return QImage(
            cutout.rgba.data,
            width,
            height,
            cutout.rgba.strides[0],
            QImage.Format.Format_RGBA8888,
        ).copy()

    @Slot()
    def _copy_cutout(self) -> None:
        if self._selection_window is None:
            return
        try:
            image = self._active_cutout_image()
            self._application.clipboard().setImage(image)
            self._selection_window.show_copy_confirmation()
        except (RuntimeError, ValueError) as exc:
            QMessageBox.warning(
                self._selection_window, "Could not copy cutout", str(exc)
            )

    @Slot()
    def _save_cutout_as(self) -> None:
        if self._selection_window is None:
            return
        suggested_name = f"objectsnip-{datetime.now():%Y-%m-%d-%H%M%S}.png"
        path, _selected_filter = QFileDialog.getSaveFileName(
            self._selection_window,
            "Save cutout as",
            suggested_name,
            "PNG image (*.png)",
        )
        if not path:
            return
        if Path(path).suffix.lower() != ".png":
            path += ".png"
        try:
            image = self._active_cutout_image()
            save_png(image, path)
            self._selection_window.show_save_confirmation(path)
        except (OSError, RuntimeError, ValueError) as exc:
            QMessageBox.warning(
                self._selection_window, "Could not save cutout", str(exc)
            )

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
            self._segmentation_result = None
            self._active_candidate = 0

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
    application.setWindowIcon(application_icon())
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
