from __future__ import annotations

import numpy as np
from numpy.typing import NDArray
from PySide6.QtCore import QPointF, QRect, QRectF, QSize, Qt, Signal
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
    QWheelEvent,
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
    position: QPointF, target: QRectF, image_size: QSize
) -> tuple[float, float] | None:
    if not target.contains(position) or target.isEmpty() or image_size.isEmpty():
        return None
    x = (position.x() - target.left()) * image_size.width() / target.width()
    y = (position.y() - target.top()) * image_size.height() / target.height()
    return min(x, image_size.width() - 1), min(y, image_size.height() - 1)


def zoomed_image_rect(
    canvas: QRectF,
    image_size: QSize,
    zoom: float,
    center: QPointF,
) -> QRectF:
    if canvas.isEmpty() or image_size.isEmpty():
        return QRectF()
    scale = max(
        canvas.width() / image_size.width(),
        canvas.height() / image_size.height(),
    )
    scale *= zoom
    return QRectF(
        canvas.center().x() - center.x() * scale,
        canvas.center().y() - center.y() * scale,
        image_size.width() * scale,
        image_size.height() * scale,
    )


class ObjectSelectionWindow(QWidget):
    retry_requested = Signal()
    prompts_changed = Signal(object)
    candidate_selected = Signal(int)
    DEFAULT_SIZE = QSize(960, 640)
    MARKER_RADIUS = 7
    MIN_ZOOM = 1.0
    MAX_ZOOM = 16.0
    ZOOM_STEP = 1.25

    def __init__(self, image: QImage) -> None:
        super().__init__()
        self._image = image.copy()
        self._mask_image: QImage | None = None
        self._candidate_masks: tuple[NDArray[np.bool_], ...] = ()
        self._active_candidate = 0
        self._points: list[PointPrompt] = []
        self._point_mode = PointLabel.INCLUDE
        self._zoom = self.MIN_ZOOM
        self._view_center = QPointF(self._image.width() / 2, self._image.height() / 2)
        self._pan_origin: QPointF | None = None
        self._pan_center_origin: QPointF | None = None
        self._pan_button: Qt.MouseButton | None = None
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
        self._toolbar.addSeparator()
        self._reset_prompts_action = QAction("Reset prompts", self)
        self._reset_prompts_action.triggered.connect(self._reset_prompts)
        self._toolbar.addAction(self._reset_prompts_action)
        self._toolbar.addSeparator()
        self._candidate_group = QActionGroup(self)
        self._candidate_group.setExclusive(True)
        self._candidate_actions: list[QAction] = []
        for index in range(3):
            action = QAction(f"Mask {index + 1}", self._candidate_group)
            action.setCheckable(True)
            action.setEnabled(False)
            action.triggered.connect(
                lambda _checked=False, candidate=index: self._select_candidate(
                    candidate
                )
            )
            self._candidate_actions.append(action)
            self._toolbar.addAction(action)
        self._toolbar.addSeparator()
        self._reset_zoom_action = QAction("Reset zoom", self)
        self._reset_zoom_action.triggered.connect(self._reset_zoom)
        self._toolbar.addAction(self._reset_zoom_action)
        self._pan_action = QAction("Pan", self)
        self._pan_action.setCheckable(True)
        self._pan_action.toggled.connect(self._pan_toggled)
        self._toolbar.addAction(self._pan_action)
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

    def set_candidates(
        self,
        masks: NDArray[np.bool_],
        scores: NDArray[np.float32],
    ) -> None:
        if masks.ndim != 3 or masks.shape[0] != len(scores):
            raise ValueError("candidate masks and scores must have matching counts")
        self._candidate_masks = tuple(masks[index] for index in range(len(scores)))
        self._active_candidate = 0
        for index, action in enumerate(self._candidate_actions):
            available = index < len(scores)
            action.setEnabled(available)
            action.setVisible(available)
            action.setChecked(index == 0 and available)
            if available:
                action.setText(f"Mask {index + 1} ({float(scores[index]):.3f})")
        if self._candidate_masks:
            self.set_mask(self._candidate_masks[0])
        else:
            self.clear_mask()

    def clear_candidates(self) -> None:
        self._candidate_masks = ()
        self._active_candidate = 0
        for index, action in enumerate(self._candidate_actions):
            action.setText(f"Mask {index + 1}")
            action.setChecked(False)
            action.setEnabled(False)
            action.setVisible(True)
        self.clear_mask()

    def _select_candidate(self, index: int) -> None:
        if not 0 <= index < len(self._candidate_masks):
            return
        self._active_candidate = index
        self.set_mask(self._candidate_masks[index])
        self.candidate_selected.emit(index)

    def _reset_prompts(self) -> None:
        self._points.clear()
        self.clear_candidates()
        self.prompts_changed.emit(())
        self.update()

    @property
    def points(self) -> tuple[PointPrompt, ...]:
        return tuple(self._points)

    def _set_point_mode(self, mode: PointLabel) -> None:
        self._point_mode = mode

    def _canvas_rect(self) -> QRectF:
        return QRectF(
            0,
            self._toolbar.height(),
            self.width(),
            self.height() - self._toolbar.height(),
        )

    def _viewport_rect(self) -> QRectF:
        canvas = self._canvas_rect()
        fitted = QRectF(fitted_image_rect(self._image.size(), canvas.size().toSize()))
        fitted.translate(canvas.topLeft())
        return fitted

    def _image_rect(self) -> QRectF:
        return zoomed_image_rect(
            self._viewport_rect(), self._image.size(), self._zoom, self._view_center
        )

    def _view_to_image(self, position: QPointF) -> tuple[float, float] | None:
        if not self._viewport_rect().contains(position):
            return None
        return view_to_image_point(position, self._image_rect(), self._image.size())

    def _image_to_view(self, point: PointPrompt) -> QPointF:
        target = self._image_rect()
        return QPointF(
            target.left() + point.x * target.width() / self._image.width(),
            target.top() + point.y * target.height() / self._image.height(),
        )

    def _reset_zoom(self) -> None:
        self._zoom = self.MIN_ZOOM
        self._view_center = QPointF(self._image.width() / 2, self._image.height() / 2)
        self.update()

    def _pan_toggled(self, active: bool) -> None:
        self.setCursor(
            Qt.CursorShape.OpenHandCursor if active else Qt.CursorShape.ArrowCursor
        )

    def _clamp_view_center(self, center: QPointF) -> QPointF:
        viewport = self._viewport_rect()
        target = zoomed_image_rect(
            viewport,
            self._image.size(),
            self._zoom,
            QPointF(self._image.width() / 2, self._image.height() / 2),
        )
        scale = target.width() / self._image.width()

        def clamp_axis(value: float, image_extent: int, canvas_extent: float) -> float:
            visible_extent = canvas_extent / scale
            if visible_extent >= image_extent:
                lower = max(0.0, image_extent - visible_extent / 2)
                upper = min(float(image_extent), visible_extent / 2)
            else:
                lower = visible_extent / 2
                upper = image_extent - visible_extent / 2
            return max(lower, min(upper, value))

        return QPointF(
            clamp_axis(center.x(), self._image.width(), viewport.width()),
            clamp_axis(center.y(), self._image.height(), viewport.height()),
        )

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if not self._encoding_ready:
            super().mousePressEvent(event)
            return
        position = event.position()
        starts_pan = event.button() is Qt.MouseButton.MiddleButton or (
            event.button() is Qt.MouseButton.LeftButton and self._pan_action.isChecked()
        )
        if starts_pan:
            if self._viewport_rect().contains(position):
                self._pan_origin = position
                self._pan_center_origin = QPointF(self._view_center)
                self._pan_button = event.button()
                self.setCursor(Qt.CursorShape.ClosedHandCursor)
            return
        if event.button() is not Qt.MouseButton.LeftButton:
            super().mousePressEvent(event)
            return
        for index, point in enumerate(self._points):
            delta = self._image_to_view(point) - position
            if abs(delta.x()) + abs(delta.y()) <= self.MARKER_RADIUS * 2:
                del self._points[index]
                self.prompts_changed.emit(tuple(self._points))
                self.update()
                return
        image_position = self._view_to_image(position)
        if image_position is not None:
            self._points.append(PointPrompt(*image_position, self._point_mode))
            self.prompts_changed.emit(tuple(self._points))
            self.update()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._pan_origin is None or self._pan_center_origin is None:
            super().mouseMoveEvent(event)
            return
        target = self._image_rect()
        scale = target.width() / self._image.width()
        movement = event.position() - self._pan_origin
        self._view_center = self._clamp_view_center(
            QPointF(
                self._pan_center_origin.x() - movement.x() / scale,
                self._pan_center_origin.y() - movement.y() / scale,
            )
        )
        self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() is self._pan_button and self._pan_origin is not None:
            self._pan_origin = None
            self._pan_center_origin = None
            self._pan_button = None
            self.setCursor(
                Qt.CursorShape.OpenHandCursor
                if self._pan_action.isChecked()
                else Qt.CursorShape.ArrowCursor
            )
            return
        super().mouseReleaseEvent(event)

    def wheelEvent(self, event: QWheelEvent) -> None:
        image_position = self._view_to_image(event.position())
        steps = event.angleDelta().y() / 120
        if image_position is None or steps == 0:
            super().wheelEvent(event)
            return
        previous_zoom = self._zoom
        self._zoom = max(
            self.MIN_ZOOM,
            min(self.MAX_ZOOM, self._zoom * self.ZOOM_STEP**steps),
        )
        if self._zoom == previous_zoom:
            event.accept()
            return
        viewport = self._viewport_rect()
        viewport_center = viewport.center()
        scale = self._image_rect().width() / self._image.width()
        self._view_center = self._clamp_view_center(
            QPointF(
                image_position[0]
                - (event.position().x() - viewport_center.x()) / scale,
                image_position[1]
                - (event.position().y() - viewport_center.y()) / scale,
            )
        )
        if self._pan_origin is not None:
            self._pan_origin = event.position()
            self._pan_center_origin = QPointF(self._view_center)
        self.update()
        event.accept()

    def paintEvent(self, event: QPaintEvent) -> None:
        del event
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#202124"))
        painter.setClipRect(self._viewport_rect())
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
