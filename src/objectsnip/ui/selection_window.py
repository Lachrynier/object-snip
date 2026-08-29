from __future__ import annotations

import numpy as np
from numpy.typing import NDArray
from PySide6.QtCore import QPoint, QRect, QSize, Qt, Signal
from PySide6.QtGui import (
    QAction,
    QActionGroup,
    QColor,
    QImage,
    QMouseEvent,
    QPainter,
    QPaintEvent,
    QPen,
    QResizeEvent,
)
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QProgressBar,
    QPushButton,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from objectsnip.segmentation.interface import PointLabel, PointPrompt


def fitted_image_rect(image_size: QSize, viewport_size: QSize) -> QRect:
    if image_size.isEmpty() or viewport_size.isEmpty():
        return QRect()
    scaled = image_size.scaled(viewport_size, Qt.AspectRatioMode.KeepAspectRatio)
    return QRect(
        (viewport_size.width() - scaled.width()) // 2,
        (viewport_size.height() - scaled.height()) // 2,
        scaled.width(),
        scaled.height(),
    )


def view_to_image_point(
    position: QPoint, target: QRect, image_size: QSize
) -> tuple[float, float] | None:
    if not target.contains(position) or target.isEmpty() or image_size.isEmpty():
        return None
    x = (position.x() - target.left()) * image_size.width() / target.width()
    y = (position.y() - target.top()) * image_size.height() / target.height()
    return min(x, image_size.width() - 1), min(y, image_size.height() - 1)


class ObjectSelectionWindow(QWidget):
    retry_requested = Signal()
    prompts_changed = Signal(object)
    DEFAULT_SIZE = QSize(960, 640)
    MARKER_RADIUS = 7

    def __init__(self, image: QImage) -> None:
        super().__init__()
        self._image = image.copy()
        self._mask_image: QImage | None = None
        self._points: list[PointPrompt] = []
        self._point_mode = PointLabel.INCLUDE
        self._encoding_ready = False
        self.setWindowTitle("ObjectSnip")
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.resize(self.DEFAULT_SIZE)

        self._toolbar = QToolBar(self)
        modes = QActionGroup(self)
        modes.setExclusive(True)
        self._include_action = QAction("Positive", modes)
        self._include_action.setCheckable(True)
        self._include_action.setChecked(True)
        self._include_action.triggered.connect(
            lambda: self._set_point_mode(PointLabel.INCLUDE)
        )
        self._exclude_action = QAction("Negative", modes)
        self._exclude_action.setCheckable(True)
        self._exclude_action.triggered.connect(
            lambda: self._set_point_mode(PointLabel.EXCLUDE)
        )
        self._toolbar.addActions((self._include_action, self._exclude_action))
        self._toolbar.setStyleSheet(
            "QToolButton:checked { font-weight: bold; }"
            "QToolButton[text='Positive'] { color: #35c759; }"
            "QToolButton[text='Negative'] { color: #ff453a; }"
        )

        self._status_overlay = QFrame(self)
        self._status_overlay.setStyleSheet(
            "QFrame { background: rgba(0, 0, 0, 145); }"
            "QLabel { color: white; background: transparent; }"
            "QProgressBar { min-width: 220px; }"
        )
        layout = QVBoxLayout(self._status_overlay)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status_label = QLabel("Preparing image…", self._status_overlay)
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._progress = QProgressBar(self._status_overlay)
        self._progress.setRange(0, 0)
        self._progress.setTextVisible(False)
        self._retry_button = QPushButton("Retry", self._status_overlay)
        self._retry_button.clicked.connect(self.retry_requested)
        self._retry_button.hide()
        layout.addWidget(self._status_label)
        layout.addWidget(self._progress)
        layout.addWidget(self._retry_button, alignment=Qt.AlignmentFlag.AlignCenter)

    @property
    def is_encoding_ready(self) -> bool:
        return self._encoding_ready

    def show_preparing(self) -> None:
        self._encoding_ready = False
        self._status_overlay.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents, False
        )
        self._status_label.setText("Preparing image…")
        self._progress.show()
        self._retry_button.hide()
        self._status_overlay.show()
        self._toolbar.setEnabled(False)

    def show_ready(self) -> None:
        self._encoding_ready = True
        self._status_overlay.hide()
        self._toolbar.setEnabled(True)

    def show_encoding_error(self, message: str) -> None:
        self._encoding_ready = False
        self._status_overlay.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents, False
        )
        self._status_label.setText(f"Could not prepare image\n{message}")
        self._progress.hide()
        self._retry_button.show()
        self._status_overlay.show()
        self._toolbar.setEnabled(False)

    def show_predicting(self) -> None:
        self._status_overlay.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents, True
        )
        self._status_label.setText("Updating mask…")
        self._progress.show()
        self._retry_button.hide()
        self._status_overlay.show()
        self._status_overlay.raise_()

    def show_prediction_error(self, message: str) -> None:
        self._status_overlay.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents, True
        )
        self._status_label.setText(f"Could not update mask\n{message}")
        self._progress.hide()
        self._retry_button.hide()
        self._status_overlay.show()

    def set_mask(self, mask: NDArray[np.bool_]) -> None:
        if mask.shape != (self._image.height(), self._image.width()):
            raise ValueError("mask dimensions must match the selection image")
        rgba = np.zeros((mask.shape[0], mask.shape[1], 4), dtype=np.uint8)
        rgba[mask] = (0, 170, 255, 105)
        self._mask_image = QImage(
            rgba.data,
            mask.shape[1],
            mask.shape[0],
            rgba.strides[0],
            QImage.Format.Format_RGBA8888,
        ).copy()
        self._status_overlay.hide()
        self.update()

    def clear_mask(self) -> None:
        self._mask_image = None
        self._status_overlay.hide()
        self.update()

    @property
    def points(self) -> tuple[PointPrompt, ...]:
        return tuple(self._points)

    def _set_point_mode(self, mode: PointLabel) -> None:
        self._point_mode = mode

    def _image_rect(self) -> QRect:
        available = QRect(
            0,
            self._toolbar.height(),
            self.width(),
            self.height() - self._toolbar.height(),
        )
        fitted = fitted_image_rect(self._image.size(), available.size())
        fitted.translate(available.topLeft())
        return fitted

    def _view_to_image(self, position: QPoint) -> tuple[float, float] | None:
        return view_to_image_point(position, self._image_rect(), self._image.size())

    def _image_to_view(self, point: PointPrompt) -> QPoint:
        target = self._image_rect()
        return QPoint(
            round(target.left() + point.x * target.width() / self._image.width()),
            round(target.top() + point.y * target.height() / self._image.height()),
        )

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() is not Qt.MouseButton.LeftButton or not self._encoding_ready:
            super().mousePressEvent(event)
            return
        position = event.position().toPoint()
        for index, point in enumerate(self._points):
            delta = self._image_to_view(point) - position
            if delta.manhattanLength() <= self.MARKER_RADIUS * 2:
                del self._points[index]
                self.prompts_changed.emit(tuple(self._points))
                self.update()
                return
        image_position = self._view_to_image(position)
        if image_position is not None:
            self._points.append(PointPrompt(*image_position, self._point_mode))
            self.prompts_changed.emit(tuple(self._points))
            self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        del event
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#202124"))
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        target = self._image_rect()
        painter.drawImage(target, self._image)
        if self._mask_image is not None:
            painter.drawImage(target, self._mask_image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        for point in self._points:
            color = (
                QColor("#35c759")
                if point.label is PointLabel.INCLUDE
                else QColor("#ff453a")
            )
            painter.setPen(QPen(QColor("white"), 2))
            painter.setBrush(color)
            painter.drawEllipse(
                self._image_to_view(point), self.MARKER_RADIUS, self.MARKER_RADIUS
            )

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._toolbar.setGeometry(0, 0, self.width(), self._toolbar.sizeHint().height())
        self._status_overlay.setGeometry(self.rect())
        self._status_overlay.raise_()
