from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtGui import (
    QColor,
    QImage,
    QKeyEvent,
    QMouseEvent,
    QPainter,
    QPaintEvent,
    QPen,
)
from PySide6.QtWidgets import QPushButton, QWidget

from objectsnip.capture.crop import crop_context
from objectsnip.domain.geometry import Handle, Point, Rect, Size, hit_test, resize_rect


class CaptureOverlay(QWidget):
    HANDLE_RADIUS = 5
    HIT_TOLERANCE = 8
    MINIMUM_SIZE = 8

    def __init__(
        self,
        screenshot: QImage,
        on_locked: Callable[[QImage, Rect], None],
    ) -> None:
        super().__init__()
        self._screenshot = screenshot
        self._image_size = Size(screenshot.width(), screenshot.height())
        self._on_locked = on_locked
        self._draft: Rect | None = None
        self._press_point: Point | None = None
        self._press_rect: Rect | None = None
        self._active_handle = Handle.OUTSIDE

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setCursor(Qt.CursorShape.CrossCursor)

        self._lock_button = QPushButton("Lock region", self)
        self._lock_button.setEnabled(False)
        self._lock_button.clicked.connect(self._lock_region)
        self._lock_button.adjustSize()

    def resizeEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        super().resizeEvent(event)
        margin = 24
        x = max(margin, (self.width() - self._lock_button.width()) // 2)
        y = max(margin, self.height() - self._lock_button.height() - margin)
        self._lock_button.move(x, y)

    def paintEvent(self, event: QPaintEvent) -> None:
        del event
        painter = QPainter(self)
        painter.drawImage(self.rect(), self._screenshot)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 110))

        if self._draft is None or not self._draft.is_valid:
            return

        view_rect = self._to_view_rect(self._draft)
        source_rect = QRect(
            self._draft.left,
            self._draft.top,
            self._draft.width,
            self._draft.height,
        )
        painter.drawImage(view_rect, self._screenshot, source_rect)
        painter.setPen(QPen(QColor("#55c2ff"), 2))
        painter.drawRect(view_rect)
        painter.setBrush(QColor("#f7fbff"))
        painter.setPen(QPen(QColor("#147eae"), 1))
        for point in self._handle_points(view_rect):
            painter.drawEllipse(point, self.HANDLE_RADIUS, self.HANDLE_RADIUS)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            return
        point = self._to_image_point(event.position().toPoint())
        self._press_point = point
        self._press_rect = self._draft
        tolerance = self._image_tolerance()
        self._active_handle = (
            hit_test(self._draft, point, tolerance)
            if self._draft is not None
            else Handle.OUTSIDE
        )
        if self._active_handle is Handle.OUTSIDE:
            self._draft = Rect.from_points(point, point)
        self.update()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        point = self._to_image_point(event.position().toPoint())
        if self._press_point is None:
            self._update_cursor(point)
            return

        if self._active_handle is Handle.OUTSIDE:
            self._draft = Rect.from_points(self._press_point, point).clamp(
                self._image_size
            )
        elif self._active_handle is Handle.MOVE and self._press_rect is not None:
            self._draft = self._press_rect.moved(
                point.x - self._press_point.x,
                point.y - self._press_point.y,
                self._image_size,
            )
        elif self._press_rect is not None:
            self._draft = resize_rect(
                self._press_rect,
                self._active_handle,
                point,
                self._image_size,
                self.MINIMUM_SIZE,
            )
        self._sync_button()
        self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            return
        self._press_point = None
        self._press_rect = None
        self._active_handle = Handle.OUTSIDE
        self._sync_button()
        self._update_cursor(self._to_image_point(event.position().toPoint()))

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.close()
            return
        super().keyPressEvent(event)

    def _lock_region(self) -> None:
        if self._draft is None or not self._draft.is_valid:
            return
        crop = crop_context(self._screenshot, self._draft)
        self._lock_button.setEnabled(False)
        self._on_locked(crop, self._draft)
        self.close()

    def _sync_button(self) -> None:
        self._lock_button.setEnabled(
            self._draft is not None
            and self._draft.width >= self.MINIMUM_SIZE
            and self._draft.height >= self.MINIMUM_SIZE
        )

    def _to_image_point(self, view_point: QPoint) -> Point:
        x = round(view_point.x() * self._image_size.width / max(1, self.width()))
        y = round(view_point.y() * self._image_size.height / max(1, self.height()))
        return Point(
            max(0, min(x, self._image_size.width)),
            max(0, min(y, self._image_size.height)),
        )

    def _to_view_rect(self, rect: Rect) -> QRect:
        x = round(rect.left * self.width() / self._image_size.width)
        y = round(rect.top * self.height() / self._image_size.height)
        right = round(rect.right * self.width() / self._image_size.width)
        bottom = round(rect.bottom * self.height() / self._image_size.height)
        return QRect(x, y, right - x, bottom - y)

    def _image_tolerance(self) -> int:
        return max(
            1,
            round(
                self.HIT_TOLERANCE
                * self._image_size.width
                / max(1, self.width())
            ),
        )

    def _update_cursor(self, point: Point) -> None:
        handle = (
            hit_test(self._draft, point, self._image_tolerance())
            if self._draft is not None
            else Handle.OUTSIDE
        )
        cursor = {
            Handle.MOVE: Qt.CursorShape.SizeAllCursor,
            Handle.LEFT: Qt.CursorShape.SizeHorCursor,
            Handle.RIGHT: Qt.CursorShape.SizeHorCursor,
            Handle.TOP: Qt.CursorShape.SizeVerCursor,
            Handle.BOTTOM: Qt.CursorShape.SizeVerCursor,
            Handle.TOP_LEFT: Qt.CursorShape.SizeFDiagCursor,
            Handle.BOTTOM_RIGHT: Qt.CursorShape.SizeFDiagCursor,
            Handle.TOP_RIGHT: Qt.CursorShape.SizeBDiagCursor,
            Handle.BOTTOM_LEFT: Qt.CursorShape.SizeBDiagCursor,
        }.get(handle, Qt.CursorShape.CrossCursor)
        self.setCursor(cursor)

    @staticmethod
    def _handle_points(rect: QRect) -> tuple[QPoint, ...]:
        return (
            rect.topLeft(),
            QPoint(rect.center().x(), rect.top()),
            rect.topRight(),
            QPoint(rect.left(), rect.center().y()),
            QPoint(rect.right(), rect.center().y()),
            rect.bottomLeft(),
            QPoint(rect.center().x(), rect.bottom()),
            rect.bottomRight(),
        )
