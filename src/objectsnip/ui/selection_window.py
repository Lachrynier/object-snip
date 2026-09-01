from __future__ import annotations

from enum import Enum
from html import escape
from math import ceil
from pathlib import Path

import numpy as np
from numpy.typing import NDArray
from PySide6.QtCore import QPointF, QRect, QRectF, QSize, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import (
    QAction,
    QActionGroup,
    QColor,
    QDesktopServices,
    QFont,
    QGuiApplication,
    QIcon,
    QImage,
    QMouseEvent,
    QPainter,
    QPainterPath,
    QPaintEvent,
    QPen,
    QPixmap,
    QResizeEvent,
    QWheelEvent,
)
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMenu,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QSlider,
    QStyle,
    QStyleOptionToolButton,
    QStylePainter,
    QToolBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
    QWidgetAction,
)

from objectsnip.segmentation.interface import PointLabel, PointPrompt


class MaskView(Enum):
    OVERLAY = "Overlay"
    MASK = "Mask"
    CUTOUT = "Cutout"
    OUTLINE = "Outline"
    EXCLUDED = "Excluded"


MASK_COLORS = (
    ("Cyan", "#00aaff"),
    ("Magenta", "#f044d1"),
    ("Yellow", "#ffd43b"),
    ("Green", "#35c759"),
    ("Red", "#ff453a"),
)


def _toolbar_icon(name: str) -> QIcon:
    """Return a fallback icon rendered for the active desktop pixel ratio."""
    screen = QGuiApplication.primaryScreen()
    pixel_ratio = screen.devicePixelRatio() if screen is not None else 1.0
    pixmap = QPixmap(ceil(20 * pixel_ratio), ceil(20 * pixel_ratio))
    pixmap.setDevicePixelRatio(pixel_ratio)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(QPen(QColor("#30343a"), 1.7, Qt.PenStyle.SolidLine))
    painter.setBrush(Qt.BrushStyle.NoBrush)

    if name in {"positive", "negative"}:
        painter.drawEllipse(QRectF(3, 3, 14, 14))
        painter.drawLine(QPointF(6.5, 10), QPointF(13.5, 10))
        if name == "positive":
            painter.drawLine(QPointF(10, 6.5), QPointF(10, 13.5))
    elif name == "fit":
        for start, corner, end in (
            (QPointF(8, 3), QPointF(3, 3), QPointF(3, 8)),
            (QPointF(12, 3), QPointF(17, 3), QPointF(17, 8)),
            (QPointF(3, 12), QPointF(3, 17), QPointF(8, 17)),
            (QPointF(17, 12), QPointF(17, 17), QPointF(12, 17)),
        ):
            path = QPainterPath(start)
            path.lineTo(corner)
            path.lineTo(end)
            painter.drawPath(path)
    elif name == "pan":
        path = QPainterPath(QPointF(6, 9))
        path.lineTo(6, 6)
        path.cubicTo(6, 4.5, 8, 4.5, 8, 6)
        path.lineTo(8, 4)
        path.cubicTo(8, 2.5, 10, 2.5, 10, 4)
        path.lineTo(10, 3.5)
        path.cubicTo(10, 2, 12, 2, 12, 3.5)
        path.lineTo(12, 5)
        path.cubicTo(12, 3.5, 14, 3.5, 14, 5)
        path.lineTo(14, 10)
        path.cubicTo(14, 15, 12, 17, 9, 17)
        path.cubicTo(6.5, 17, 5.5, 15, 4, 12)
        path.cubicTo(3, 10, 4.5, 8.5, 6, 9)
        painter.drawPath(path)
    elif name in {"eye-open", "eye-closed"}:
        eye = QPainterPath(QPointF(2.5, 10))
        eye.cubicTo(6, 5, 14, 5, 17.5, 10)
        eye.cubicTo(14, 15, 6, 15, 2.5, 10)
        painter.drawPath(eye)
        painter.drawEllipse(QPointF(10, 10), 2.5, 2.5)
        if name == "eye-closed":
            painter.drawLine(QPointF(3, 3), QPointF(17, 17))
    painter.end()
    return QIcon(pixmap)


class CandidateToolButton(QToolButton):
    """Draw a candidate number and confidence with distinct typography."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._number = ""
        self._score = ""

    def set_candidate_text(self, number: int, score: float | None = None) -> None:
        self._number = str(number)
        self._score = "" if score is None else f"({score:.3f})"
        self.updateGeometry()
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        del event
        option = QStyleOptionToolButton()
        self.initStyleOption(option)
        option.text = ""
        painter = QStylePainter(self)
        painter.drawComplexControl(QStyle.ComplexControl.CC_ToolButton, option)

        number_font = QFont(self.font())
        number_font.setBold(True)
        number_font.setPointSizeF(number_font.pointSizeF() + 0.5)
        score_font = QFont(self.font())
        score_font.setPointSizeF(max(8.0, score_font.pointSizeF() - 1.0))
        painter.setFont(number_font)
        number_width = painter.fontMetrics().horizontalAdvance(self._number)
        painter.setFont(score_font)
        score_width = painter.fontMetrics().horizontalAdvance(self._score)
        gap = 5 if self._score else 0
        left = (self.width() - number_width - gap - score_width) // 2

        if not self.isEnabled():
            number_color = score_color = QColor("#9298a1")
        elif self.isChecked():
            number_color, score_color = QColor("#071521"), QColor("#27475b")
        else:
            number_color, score_color = QColor("#24282e"), QColor("#68707b")
        painter.setFont(number_font)
        painter.setPen(number_color)
        painter.drawText(
            QRect(left, 0, number_width, self.height()),
            Qt.AlignmentFlag.AlignCenter,
            self._number,
        )
        painter.setFont(score_font)
        painter.setPen(score_color)
        painter.drawText(
            QRect(left + number_width + gap, 0, score_width, self.height()),
            Qt.AlignmentFlag.AlignCenter,
            self._score,
        )


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


def zoomed_viewport_rect(canvas: QRectF, image_size: QSize, zoom: float) -> QRectF:
    if canvas.isEmpty() or image_size.isEmpty():
        return QRectF()
    fitted = QRectF(fitted_image_rect(image_size, canvas.size().toSize()))
    width = min(canvas.width(), fitted.width() * zoom)
    height = min(canvas.height(), fitted.height() * zoom)
    return QRectF(
        canvas.center().x() - width / 2,
        canvas.center().y() - height / 2,
        width,
        height,
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
    copy_requested = Signal()
    save_as_requested = Signal()
    DEFAULT_SIZE = QSize(960, 640)
    MARKER_RADIUS = 7
    MIN_ZOOM = 1.0
    MAX_ZOOM = 16.0
    ZOOM_STEP = 1.25

    def __init__(self, image: QImage) -> None:
        super().__init__()
        self._image = image.copy()
        self._mask: NDArray[np.bool_] | None = None
        self._mask_image: QImage | None = None
        self._outline_image: QImage | None = None
        self._cutout_image: QImage | None = None
        self._cutout_bounds: QRect | None = None
        self._mask_view = MaskView.OVERLAY
        self._mask_color = QColor(MASK_COLORS[0][1])
        self._mask_opacity = 40
        self._candidate_masks: tuple[NDArray[np.bool_], ...] = ()
        self._active_candidate = 0
        self._points: list[PointPrompt] = []
        self._point_mode = PointLabel.INCLUDE
        self._show_points = True
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
        self._toolbar.setObjectName("selectionToolbar")
        self._toolbar.setMovable(False)
        self._toolbar.setFloatable(False)
        modes = QActionGroup(self)
        modes.setExclusive(True)
        self._reset_prompts_action = QAction("Clear", self)
        self._reset_prompts_action.setToolTip("Clear all prompts")
        self._reset_prompts_action.triggered.connect(self._reset_prompts)
        self._toolbar.addAction(self._reset_prompts_action)
        self._toolbar.addSeparator()
        self._include_action = QAction(
            _toolbar_icon("positive"),
            "Positive",
            modes,
        )
        self._include_action.setToolTip(
            "Mark an area that belongs to the object. "
            "Click an existing point to remove it."
        )
        self._include_action.setCheckable(True)
        self._include_action.setChecked(True)
        self._include_action.triggered.connect(
            lambda: self._set_point_mode(PointLabel.INCLUDE)
        )
        self._exclude_action = QAction(
            _toolbar_icon("negative"),
            "Negative",
            modes,
        )
        self._exclude_action.setToolTip(
            "Mark an area that should be excluded from the object."
        )
        self._exclude_action.setCheckable(True)
        self._exclude_action.triggered.connect(
            lambda: self._set_point_mode(PointLabel.EXCLUDE)
        )
        self._toolbar.addActions((self._include_action, self._exclude_action))
        self._show_points_action = QAction(
            QIcon.fromTheme("view-visible", _toolbar_icon("eye-open")),
            "Show points",
            self,
        )
        self._show_points_action.setToolTip("Hide prompt points")
        self._show_points_action.setCheckable(True)
        self._show_points_action.setChecked(True)
        self._show_points_action.toggled.connect(self._show_points_toggled)
        self._toolbar.addAction(self._show_points_action)
        self._toolbar.addSeparator()
        self._candidate_group = QActionGroup(self)
        self._candidate_group.setExclusive(True)
        self._masks_group = QFrame(self._toolbar)
        self._masks_group.setObjectName("masksGroup")
        masks_layout = QHBoxLayout(self._masks_group)
        masks_layout.setContentsMargins(5, 3, 5, 3)
        masks_layout.setSpacing(4)
        self._masks_label = QLabel("Masks", self._masks_group)
        self._masks_label.setToolTip("Candidate masks")
        masks_layout.addWidget(self._masks_label)
        self._candidate_actions: list[QAction] = []
        self._candidate_buttons: list[CandidateToolButton] = []
        for index in range(3):
            action = QAction(str(index + 1), self._candidate_group)
            action.setToolTip(f"Mask {index + 1} is not available yet")
            action.setCheckable(True)
            action.setEnabled(False)
            action.triggered.connect(
                lambda _checked=False, candidate=index: self._select_candidate(
                    candidate
                )
            )
            self._candidate_actions.append(action)
            button = CandidateToolButton(self._masks_group)
            button.setDefaultAction(action)
            button.set_candidate_text(index + 1)
            button.setProperty("toolRole", "candidate")
            self._candidate_buttons.append(button)
            masks_layout.addWidget(button)
        self._toolbar.addWidget(self._masks_group)
        self._toolbar.addSeparator()
        self._view_combo = QComboBox(self._toolbar)
        self._view_combo.setToolTip("Choose how to inspect the selected mask")
        for view in MaskView:
            self._view_combo.addItem(view.value, view)
        self._view_combo.currentIndexChanged.connect(self._view_changed)
        self._toolbar.addWidget(self._view_combo)
        self._color_button = QToolButton(self._toolbar)
        self._color_button.setObjectName("maskColorButton")
        self._color_button.setToolTip("Mask color")
        self._color_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        color_menu = QMenu(self._color_button)
        color_menu.setObjectName("maskColorMenu")
        color_menu.setStyleSheet(
            "QMenu#maskColorMenu { padding: 3px; }"
            "QMenu#maskColorMenu::item { padding: 0; margin: 0; }"
        )
        for name, value in MASK_COLORS:
            action = QWidgetAction(color_menu)
            action.setData(value)
            action.setToolTip(name)
            swatch = QPushButton(color_menu)
            swatch.setFixedSize(44, 20)
            swatch.setToolTip(name)
            swatch.setAccessibleName(name)
            swatch.setStyleSheet(
                "QPushButton {"
                f" background: {value}; border: 1px solid #565b62;"
                " border-radius: 2px; margin: 1px; }"
                "QPushButton:hover { border: 2px solid #202124; }"
            )
            swatch.clicked.connect(
                lambda _checked=False, color=value: (
                    self._set_mask_color(color),
                    color_menu.close(),
                )
            )
            action.setDefaultWidget(swatch)
            color_menu.addAction(action)
        self._color_menu = color_menu
        self._color_button.setMenu(self._color_menu)
        self._toolbar.addWidget(self._color_button)
        self._opacity_group = QFrame(self._toolbar)
        self._opacity_group.setObjectName("opacityGroup")
        opacity_layout = QVBoxLayout(self._opacity_group)
        opacity_layout.setContentsMargins(8, 3, 8, 4)
        opacity_layout.setSpacing(0)
        self._opacity_label = QLabel("Opacity", self._opacity_group)
        self._opacity_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        opacity_layout.addWidget(self._opacity_label)
        self._opacity_slider = QSlider(Qt.Orientation.Horizontal, self._opacity_group)
        self._opacity_slider.setRange(0, 100)
        self._opacity_slider.setValue(self._mask_opacity)
        self._opacity_slider.setFixedWidth(90)
        self._opacity_slider.setToolTip(f"Mask opacity: {self._mask_opacity}%")
        self._opacity_slider.valueChanged.connect(self._opacity_changed)
        opacity_layout.addWidget(self._opacity_slider)
        self._opacity_group.setFixedWidth(108)
        self._toolbar.addWidget(self._opacity_group)
        self._update_mask_color_ui()
        spacer = QWidget(self._toolbar)
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self._toolbar.addWidget(spacer)
        self._reset_zoom_action = QAction(
            QIcon.fromTheme("zoom-fit-best", _toolbar_icon("fit")),
            "Reset zoom",
            self,
        )
        self._reset_zoom_action.setToolTip("Reset zoom")
        self._reset_zoom_action.triggered.connect(self._reset_zoom)
        self._toolbar.addAction(self._reset_zoom_action)
        self._pan_action = QAction(
            QIcon.fromTheme("transform-move", _toolbar_icon("pan")),
            "Pan",
            self,
        )
        self._pan_action.setToolTip(
            "Drag to move the zoomed image. "
            "You can also drag with the middle mouse button."
        )
        self._pan_action.setCheckable(True)
        self._pan_action.toggled.connect(self._pan_toggled)
        self._toolbar.addAction(self._pan_action)
        self._toolbar.addSeparator()
        self._copy_action = QAction(
            QIcon.fromTheme(
                "edit-copy",
                self.style().standardIcon(QStyle.StandardPixmap.SP_DialogApplyButton),
            ),
            "Copy object",
            self,
        )
        self._copy_action.setToolTip(
            "Copy the selected object with a transparent background to the clipboard"
        )
        self._copy_action.setEnabled(False)
        self._copy_action.triggered.connect(self.copy_requested)
        self._toolbar.addAction(self._copy_action)
        self._save_as_action = QAction(
            QIcon.fromTheme(
                "document-save-as",
                self.style().standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton),
            ),
            "Save object as PNG",
            self,
        )
        self._save_as_action.setToolTip(
            "Save the selected object with a transparent background as a PNG"
        )
        self._save_as_action.setEnabled(False)
        self._save_as_action.triggered.connect(self.save_as_requested)
        self._toolbar.addAction(self._save_as_action)
        self._set_toolbar_role(self._include_action, "positive")
        self._set_toolbar_role(self._exclude_action, "negative")
        self._set_toolbar_role(self._show_points_action, "points")
        self._set_toolbar_role(self._reset_prompts_action, "reset")
        self._set_toolbar_role(self._reset_zoom_action, "navigation")
        self._set_toolbar_role(self._pan_action, "pan")
        self._set_toolbar_role(self._copy_action, "export")
        self._set_toolbar_role(self._save_as_action, "export")
        for action in (
            self._include_action,
            self._exclude_action,
            self._show_points_action,
            self._reset_zoom_action,
            self._pan_action,
            self._copy_action,
            self._save_as_action,
        ):
            button = self._toolbar.widgetForAction(action)
            if isinstance(button, QToolButton):
                button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self._toolbar.setStyleSheet(
            "QToolBar#selectionToolbar {"
            "  background: #d8dadd;"
            "  border: 0;"
            "  border-bottom: 1px solid #a5a9af;"
            "  spacing: 5px;"
            "  padding: 7px 9px;"
            "}"
            "QToolBar#selectionToolbar::separator {"
            "  background: #969ba3;"
            "  width: 2px;"
            "  margin: 4px 7px;"
            "}"
            "QToolBar#selectionToolbar QFrame#masksGroup {"
            "  background: #c7cacf;"
            "  border: 1px solid #969ba3;"
            "  border-radius: 7px;"
            "}"
            "QToolBar#selectionToolbar QFrame#masksGroup QLabel {"
            "  color: #30343a;"
            "  background: transparent;"
            "  border: 0;"
            "  padding: 0 3px 0 1px;"
            "  font-weight: 600;"
            "}"
            "QToolBar#selectionToolbar QComboBox {"
            "  color: #24282e; background: #eceef0;"
            "  border: 1px solid #a6abb2; border-radius: 6px; padding: 5px 8px;"
            "}"
            "QToolBar#selectionToolbar QFrame#opacityGroup {"
            "  background: #eceef0; border: 1px solid #a6abb2;"
            "  border-radius: 6px;"
            "}"
            "QToolBar#selectionToolbar QFrame#opacityGroup:disabled {"
            "  background: #ced1d5; border-color: #b4b8be;"
            "}"
            "QToolBar#selectionToolbar QLabel { color: #30343a; }"
            "QToolBar#selectionToolbar QToolButton#maskColorButton {"
            "  min-width: 24px; padding: 6px;"
            "}"
            "QToolBar#selectionToolbar QToolButton {"
            "  color: #24282e;"
            "  background: #eceef0;"
            "  border: 1px solid #a6abb2;"
            "  border-radius: 6px;"
            "  padding: 6px 10px;"
            "  font-weight: 500;"
            "}"
            "QToolBar#selectionToolbar QToolButton:hover {"
            "  background: #f8f9fa;"
            "  border-color: #7f858e;"
            "}"
            "QToolBar#selectionToolbar QToolButton:pressed {"
            "  background: #bfc3c8;"
            "}"
            "QToolBar#selectionToolbar QToolButton:disabled {"
            "  color: #858b94;"
            "  background: #ced1d5;"
            "  border-color: #b4b8be;"
            "}"
            "QToolBar#selectionToolbar QToolButton[toolRole='positive']:checked {"
            "  color: #071b0d;"
            "  background: #58d477;"
            "  border-color: #7ee598;"
            "  font-weight: 700;"
            "}"
            "QToolBar#selectionToolbar QToolButton[toolRole='negative']:checked {"
            "  color: #240707;"
            "  background: #ff6861;"
            "  border-color: #ff8b85;"
            "  font-weight: 700;"
            "}"
            "QToolBar#selectionToolbar QToolButton[toolRole='points']:checked {"
            "  color: #071521;"
            "  background: #8ed0f5;"
            "  border-color: #55a9d8;"
            "  font-weight: 700;"
            "}"
            "QToolBar#selectionToolbar QToolButton[toolRole='candidate']:checked {"
            "  color: #071521;"
            "  background: #55b9f3;"
            "  border-color: #86cff8;"
            "  font-weight: 700;"
            "}"
            "QToolBar#selectionToolbar QToolButton[toolRole='pan']:checked {"
            "  color: #160b28;"
            "  background: #b99af7;"
            "  border-color: #d0bafc;"
            "  font-weight: 700;"
            "}"
            "QToolBar#selectionToolbar QToolButton[toolRole='reset'] {"
            "  color: #5c431b;"
            "  background: #f2e1bd;"
            "  border-color: #c7a86f;"
            "}"
            "QToolBar#selectionToolbar QToolButton[toolRole='reset']:hover {"
            "  color: #3f2d11;"
            "  background: #f8e9ca;"
            "  border-color: #aa8545;"
            "}"
            "QToolBar#selectionToolbar QToolButton[toolRole='export'] {"
            "  min-width: 28px;"
            "  padding: 6px;"
            "}"
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

        self._export_bar = QFrame(self)
        self._export_bar.setObjectName("exportMessageBar")
        export_layout = QHBoxLayout(self._export_bar)
        export_layout.setContentsMargins(12, 4, 8, 4)
        export_layout.setSpacing(8)
        self._export_message = QLabel(self._export_bar)
        self._export_message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._export_message.setTextFormat(Qt.TextFormat.RichText)
        self._export_message.setTextInteractionFlags(
            Qt.TextInteractionFlag.LinksAccessibleByMouse
        )
        self._export_message.linkActivated.connect(self._open_export_link)
        export_layout.addStretch()
        export_layout.addWidget(self._export_message)
        self._open_folder_button = QToolButton(self._export_bar)
        self._open_folder_button.setIcon(
            QIcon.fromTheme(
                "folder-open",
                self.style().standardIcon(QStyle.StandardPixmap.SP_DirOpenIcon),
            )
        )
        self._open_folder_button.setText("Open folder")
        self._open_folder_button.setToolButtonStyle(
            Qt.ToolButtonStyle.ToolButtonTextBesideIcon
        )
        self._open_folder_button.clicked.connect(self._open_export_folder)
        export_layout.addWidget(self._open_folder_button)
        export_layout.addStretch()
        self._close_export_button = QToolButton(self._export_bar)
        self._close_export_button.setObjectName("closeExportButton")
        self._close_export_button.setIcon(
            QIcon.fromTheme(
                "window-close",
                self.style().standardIcon(QStyle.StandardPixmap.SP_DialogCloseButton),
            )
        )
        self._close_export_button.setToolTip("Dismiss")
        self._close_export_button.clicked.connect(self._hide_export_message)
        export_layout.addWidget(self._close_export_button)
        self._export_bar.setStyleSheet(
            "QFrame#exportMessageBar {"
            "  color: #dcecff;"
            "  background: #25384d;"
            "  border-bottom: 1px solid #4d7399;"
            "}"
            "QFrame#exportMessageBar QLabel { color: #dcecff; }"
            "QFrame#exportMessageBar QLabel a {"
            "  color: #85c7ff;"
            "  text-decoration: underline;"
            "}"
            "QFrame#exportMessageBar QToolButton {"
            "  color: #e9f4ff;"
            "  background: #36516d;"
            "  border: 1px solid #5e82a7;"
            "  border-radius: 4px;"
            "  padding: 4px 7px;"
            "}"
            "QFrame#exportMessageBar QToolButton:hover { background: #456789; }"
            "QFrame#exportMessageBar QToolButton#closeExportButton {"
            "  background: #a83232;"
            "  border-color: #dc5a5a;"
            "}"
            "QFrame#exportMessageBar QToolButton#closeExportButton:hover {"
            "  background: #cc4141;"
            "  border-color: #ff7777;"
            "}"
        )
        self._export_bar.hide()
        self._export_link_path: Path | None = None
        self._export_message_timer = QTimer(self)
        self._export_message_timer.setSingleShot(True)
        self._export_message_timer.timeout.connect(self._hide_export_message)

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
        self._set_export_enabled(False)
        self._status_overlay.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents, True
        )
        self._status_label.setText("Updating mask…")
        self._progress.show()
        self._retry_button.hide()
        self._status_overlay.show()
        self._status_overlay.raise_()

    def show_prediction_error(self, message: str) -> None:
        self._set_export_enabled(False)
        self._status_overlay.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents, True
        )
        self._status_label.setText(f"Could not update mask\n{message}")
        self._progress.hide()
        self._retry_button.hide()
        self._status_overlay.show()

    def show_copy_confirmation(self) -> None:
        self._export_link_path = None
        self._export_message.setToolTip("")
        self._export_message.setText("Object copied to clipboard")
        self._open_folder_button.hide()
        self._close_export_button.hide()
        self._show_export_message()
        self._export_message_timer.start(2500)

    def show_save_confirmation(self, path: str | Path) -> None:
        saved_path = Path(path).resolve()
        self._export_link_path = saved_path
        display_path = escape(str(saved_path))
        file_url = escape(
            QUrl.fromLocalFile(str(saved_path)).toString(
                QUrl.ComponentFormattingOption.FullyEncoded
            ),
            quote=True,
        )
        self._export_message.setToolTip(str(saved_path))
        self._export_message.setText(
            f'Object saved to <a href="{file_url}">{display_path}</a>'
        )
        self._open_folder_button.show()
        self._close_export_button.show()
        self._export_message_timer.stop()
        self._show_export_message()

    def _show_export_message(self) -> None:
        self._position_export_message()
        self._export_bar.show()
        self._export_bar.raise_()

    def _hide_export_message(self) -> None:
        self._export_message_timer.stop()
        self._export_bar.hide()

    def _position_export_message(self) -> None:
        height = self._export_bar.sizeHint().height()
        self._export_bar.setGeometry(
            0,
            self._toolbar.height(),
            self.width(),
            height,
        )

    def _open_export_link(self, _link: str) -> None:
        if self._export_link_path is not None:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self._export_link_path)))

    def _open_export_folder(self) -> None:
        if self._export_link_path is not None:
            QDesktopServices.openUrl(
                QUrl.fromLocalFile(str(self._export_link_path.parent))
            )

    def set_mask(self, mask: NDArray[np.bool_]) -> None:
        if mask.shape != (self._image.height(), self._image.width()):
            raise ValueError("mask dimensions must match the selection image")
        self._mask = np.ascontiguousarray(mask, dtype=np.bool_)
        self._rebuild_mask_images()
        self._status_overlay.hide()
        self.update()

    def _rebuild_mask_images(self) -> None:
        if self._mask is None:
            self._mask_image = None
            self._outline_image = None
            self._cutout_image = None
            self._cutout_bounds = None
            return
        mask = self._mask
        color = self._mask_color
        alpha = round(255 * self._mask_opacity / 100)
        rgba = np.zeros((mask.shape[0], mask.shape[1], 4), dtype=np.uint8)
        if self._mask_view is MaskView.MASK:
            rgba[:, :] = (0, 0, 0, 255)
            rgba[mask] = (255, 255, 255, 255)
        elif self._mask_view is MaskView.EXCLUDED:
            rgba[~mask] = (color.red(), color.green(), color.blue(), alpha)
        else:
            rgba[mask] = (color.red(), color.green(), color.blue(), alpha)
        self._mask_image = QImage(
            rgba.data,
            mask.shape[1],
            mask.shape[0],
            rgba.strides[0],
            QImage.Format.Format_RGBA8888,
        ).copy()

        boundary = mask.copy()
        if mask.shape[0] > 2 and mask.shape[1] > 2:
            eroded = np.zeros_like(mask)
            eroded[1:-1, 1:-1] = (
                mask[1:-1, 1:-1]
                & mask[:-2, 1:-1]
                & mask[2:, 1:-1]
                & mask[1:-1, :-2]
                & mask[1:-1, 2:]
            )
            boundary &= ~eroded
        outline_rgba = np.zeros_like(rgba)
        outline_rgba[boundary] = (color.red(), color.green(), color.blue(), 255)
        self._outline_image = QImage(
            outline_rgba.data,
            mask.shape[1],
            mask.shape[0],
            outline_rgba.strides[0],
            QImage.Format.Format_RGBA8888,
        ).copy()

        selected_y, selected_x = np.nonzero(mask)
        if len(selected_x) == 0:
            self._cutout_image = None
            self._cutout_bounds = None
            return
        left = int(selected_x.min())
        top = int(selected_y.min())
        right = int(selected_x.max()) + 1
        bottom = int(selected_y.max()) + 1
        self._cutout_bounds = QRect(left, top, right - left, bottom - top)
        cropped_mask = mask[top:bottom, left:right]
        alpha_data = np.ascontiguousarray(cropped_mask.astype(np.uint8) * 255)
        alpha_image = QImage(
            alpha_data.data,
            cropped_mask.shape[1],
            cropped_mask.shape[0],
            alpha_data.strides[0],
            QImage.Format.Format_Grayscale8,
        ).copy()
        self._cutout_image = self._image.copy(self._cutout_bounds).convertToFormat(
            QImage.Format.Format_ARGB32
        )
        self._cutout_image.setAlphaChannel(alpha_image)

    def clear_mask(self) -> None:
        self._mask = None
        self._mask_image = None
        self._outline_image = None
        self._cutout_image = None
        self._cutout_bounds = None
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
            self._candidate_buttons[index].setVisible(available)
            action.setChecked(index == 0 and available)
            if available:
                score = float(scores[index])
                action.setText(f"{index + 1} ({score:.3f})")
                self._candidate_buttons[index].set_candidate_text(index + 1, score)
                action.setToolTip(f"Select mask {index + 1} — confidence {score:.3f}")
        if self._candidate_masks:
            self.set_mask(self._candidate_masks[0])
            self._set_export_enabled(True)
        else:
            self.clear_mask()

    def clear_candidates(self) -> None:
        self._candidate_masks = ()
        self._active_candidate = 0
        for index, action in enumerate(self._candidate_actions):
            action.setText(str(index + 1))
            action.setToolTip(f"Mask {index + 1} is not available yet")
            action.setChecked(False)
            action.setEnabled(False)
            action.setVisible(True)
            self._candidate_buttons[index].set_candidate_text(index + 1)
            self._candidate_buttons[index].setVisible(True)
        self.clear_mask()
        self._set_export_enabled(False)

    def _set_export_enabled(self, enabled: bool) -> None:
        self._copy_action.setEnabled(enabled)
        self._save_as_action.setEnabled(enabled)

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

    def _show_points_toggled(self, visible: bool) -> None:
        self._show_points = visible
        if visible:
            icon = QIcon.fromTheme("view-visible", _toolbar_icon("eye-open"))
            self._show_points_action.setText("Show points")
            self._show_points_action.setToolTip("Hide prompt points")
        else:
            icon = QIcon.fromTheme("view-hidden", _toolbar_icon("eye-closed"))
            self._show_points_action.setText("Hide points")
            self._show_points_action.setToolTip("Show prompt points")
        self._show_points_action.setIcon(icon)
        self.update()

    def _view_changed(self, index: int) -> None:
        view = self._view_combo.itemData(index)
        if not isinstance(view, MaskView):
            return
        self._mask_view = view
        opacity_enabled = view in {
            MaskView.OVERLAY,
            MaskView.OUTLINE,
            MaskView.EXCLUDED,
        }
        self._opacity_group.setEnabled(opacity_enabled)
        self._color_button.setEnabled(view not in {MaskView.MASK, MaskView.CUTOUT})
        self._rebuild_mask_images()
        self.update()

    def _set_mask_color(self, value: str) -> None:
        self._mask_color = QColor(value)
        self._update_mask_color_ui()
        self._rebuild_mask_images()
        self.update()

    def _opacity_changed(self, value: int) -> None:
        self._mask_opacity = value
        self._opacity_slider.setToolTip(f"Mask opacity: {value}%")
        self._rebuild_mask_images()
        self.update()

    def _update_mask_color_ui(self) -> None:
        color = self._mask_color.name()
        self._color_button.setStyleSheet(
            "QToolButton#maskColorButton {"
            f" background: {color}; border: 2px solid #ffffff;"
            " border-radius: 4px; min-width: 14px; max-width: 14px;"
            " min-height: 14px; max-height: 14px; padding: 2px; }"
        )
        for button in self._candidate_buttons:
            button.setStyleSheet(
                "QToolButton:checked {"
                f" background: {color}; border-color: {color}; font-weight: 700;"
                "}"
            )

    def _set_toolbar_role(self, action: QAction, role: str) -> None:
        button = self._toolbar.widgetForAction(action)
        if isinstance(button, QToolButton):
            button.setProperty("toolRole", role)

    def _canvas_rect(self) -> QRectF:
        return QRectF(
            0,
            self._toolbar.height(),
            self.width(),
            self.height() - self._toolbar.height(),
        )

    def _viewport_rect(self) -> QRectF:
        return zoomed_viewport_rect(self._canvas_rect(), self._image.size(), self._zoom)

    def _fitted_viewport_rect(self) -> QRectF:
        canvas = self._canvas_rect()
        fitted = QRectF(fitted_image_rect(self._image.size(), canvas.size().toSize()))
        fitted.translate(canvas.topLeft())
        return fitted

    def _image_rect(self) -> QRectF:
        return zoomed_image_rect(
            self._fitted_viewport_rect(),
            self._image.size(),
            self._zoom,
            self._view_center,
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
        target = self._image_rect()
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
        if self._export_bar.isVisible() and self._export_bar.geometry().contains(
            event.position().toPoint()
        ):
            event.accept()
            return
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
        if (
            self._mask_view is MaskView.CUTOUT
            and self._cutout_image is not None
            and self._cutout_bounds is not None
        ):
            bounds = self._cutout_bounds
            scale_x = target.width() / self._image.width()
            scale_y = target.height() / self._image.height()
            export_target = QRectF(
                target.left() + bounds.left() * scale_x,
                target.top() + bounds.top() * scale_y,
                bounds.width() * scale_x,
                bounds.height() * scale_y,
            )
            painter.fillRect(target, QColor("#17191c"))
            tile = max(6.0, 12.0 * scale_x)
            rows = ceil(export_target.height() / tile)
            columns = ceil(export_target.width() / tile)
            for row in range(rows):
                for column in range(columns):
                    shade = "#eeeeee" if (row + column) % 2 == 0 else "#bdbdbd"
                    painter.fillRect(
                        QRectF(
                            export_target.left() + column * tile,
                            export_target.top() + row * tile,
                            min(tile, export_target.width() - column * tile),
                            min(tile, export_target.height() - row * tile),
                        ),
                        QColor(shade),
                    )
            painter.drawImage(export_target, self._cutout_image)
            painter.setPen(QPen(QColor("#8d939b"), 1))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(export_target)
        elif self._mask_view is MaskView.MASK and self._mask_image is not None:
            painter.drawImage(target, self._mask_image)
        else:
            painter.drawImage(target, self._image)
            if self._mask_image is not None:
                painter.drawImage(target, self._mask_image)
            shows_outline = self._mask_view is MaskView.OUTLINE
            if shows_outline and self._outline_image is not None:
                painter.drawImage(target, self._outline_image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self._show_points:
            for point in self._points:
                color = (
                    QColor("#35c759")
                    if point.label is PointLabel.INCLUDE
                    else QColor("#ff453a")
                )
                painter.setPen(QPen(QColor("white"), 2))
                painter.setBrush(color)
                painter.drawEllipse(
                    self._image_to_view(point),
                    self.MARKER_RADIUS,
                    self.MARKER_RADIUS,
                )

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._toolbar.setGeometry(0, 0, self.width(), self._toolbar.sizeHint().height())
        self._status_overlay.setGeometry(self.rect())
        self._status_overlay.raise_()
        self._position_export_message()
        if self._export_bar.isVisible():
            self._export_bar.raise_()
