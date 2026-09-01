from unittest.mock import Mock

import numpy as np
from PySide6.QtCore import QPoint, QPointF, QRect, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QImage, QInputDevice
from PySide6.QtWidgets import QApplication, QWidgetAction

from objectsnip.segmentation.interface import PointLabel, PointPrompt
from objectsnip.ui.selection_window import (
    MaskView,
    ObjectSelectionWindow,
    fitted_image_rect,
    view_to_image_point,
    zoomed_image_rect,
    zoomed_viewport_rect,
)

_APP = QApplication.instance() or QApplication([])


def test_landscape_image_is_fitted_and_vertically_centered() -> None:
    assert fitted_image_rect(QSize(1200, 600), QSize(960, 640)) == QRect(
        0, 80, 960, 480
    )


def test_portrait_image_is_fitted_and_horizontally_centered() -> None:
    assert fitted_image_rect(QSize(300, 600), QSize(960, 640)) == QRect(
        320, 0, 320, 640
    )


def test_small_image_is_upscaled_to_fit_standard_viewport() -> None:
    assert fitted_image_rect(QSize(120, 80), QSize(960, 640)) == QRect(0, 0, 960, 640)


def test_empty_image_or_viewport_has_no_target_rect() -> None:
    assert fitted_image_rect(QSize(), QSize(960, 640)).isEmpty()
    assert fitted_image_rect(QSize(100, 100), QSize()).isEmpty()


def test_view_point_maps_to_original_image_coordinates() -> None:
    target = QRectF(100, 50, 400, 200)

    assert view_to_image_point(QPointF(300, 150), target, QSize(100, 50)) == (
        50.0,
        25.0,
    )
    assert view_to_image_point(QPointF(50, 50), target, QSize(100, 50)) is None


def test_zoomed_image_rect_uses_image_coordinate_as_view_center() -> None:
    canvas = QRectF(0, 40, 800, 400)

    target = zoomed_image_rect(canvas, QSize(400, 200), 2, QPointF(100, 50))

    assert target == QRectF(0, 40, 1600, 800)
    assert view_to_image_point(canvas.center(), target, QSize(400, 200)) == (
        100.0,
        50.0,
    )


def test_fitted_viewport_remains_centered_inside_larger_canvas() -> None:
    canvas = QRect(0, 40, 800, 600)
    fitted = fitted_image_rect(QSize(1600, 900), canvas.size())
    fitted.translate(canvas.topLeft())

    assert fitted == QRect(0, 115, 800, 450)


def test_zoomed_viewport_starts_at_centered_fitted_bounds() -> None:
    canvas = QRectF(0, 40, 800, 600)

    viewport = zoomed_viewport_rect(canvas, QSize(1600, 900), 1)

    assert viewport == QRectF(0, 115, 800, 450)


def test_zoomed_viewport_expands_until_it_fills_canvas() -> None:
    canvas = QRectF(0, 40, 800, 600)

    expanding = zoomed_viewport_rect(canvas, QSize(1600, 900), 1.25)
    full = zoomed_viewport_rect(canvas, QSize(1600, 900), 2)

    assert expanding == QRectF(0, 58.75, 800, 562.5)
    assert full == canvas


def test_mask_view_renders_binary_black_and_white() -> None:
    window = ObjectSelectionWindow(QImage(3, 3, QImage.Format.Format_RGB32))
    mask = np.zeros((3, 3), dtype=np.bool_)
    mask[1, 1] = True

    window._view_combo.setCurrentIndex(list(MaskView).index(MaskView.MASK))
    window.set_mask(mask)

    assert window._mask_image is not None
    assert window._mask_image.pixelColor(0, 0) == QColor("black")
    assert window._mask_image.pixelColor(1, 1) == QColor("white")
    assert not window._opacity_slider.isEnabled()
    assert not window._color_button.isEnabled()


def test_outline_uses_shared_color_and_slider_opacity_inside() -> None:
    window = ObjectSelectionWindow(QImage(5, 5, QImage.Format.Format_RGB32))
    mask = np.ones((5, 5), dtype=np.bool_)
    window._view_combo.setCurrentIndex(list(MaskView).index(MaskView.OUTLINE))
    window._set_mask_color("#f044d1")
    window._opacity_slider.setValue(25)

    window.set_mask(mask)

    assert window._mask_image is not None
    assert window._outline_image is not None
    interior = window._mask_image.pixelColor(2, 2)
    outline = window._outline_image.pixelColor(0, 0)
    assert interior.red() == outline.red() == 240
    assert interior.green() == outline.green() == 68
    assert interior.blue() == outline.blue() == 209
    assert interior.alpha() == round(255 * 0.25)
    assert outline.alpha() == 255


def test_excluded_view_dims_only_the_background() -> None:
    window = ObjectSelectionWindow(QImage(3, 3, QImage.Format.Format_RGB32))
    mask = np.zeros((3, 3), dtype=np.bool_)
    mask[1, 1] = True
    window._view_combo.setCurrentIndex(list(MaskView).index(MaskView.EXCLUDED))
    window._opacity_slider.setValue(80)

    window.set_mask(mask)

    assert window._mask_image is not None
    assert window._mask_image.pixelColor(1, 1).alpha() == 0
    assert window._mask_image.pixelColor(0, 0) == QColor(0, 170, 255, 204)


def test_cutout_uses_the_masks_minimal_bounding_box() -> None:
    window = ObjectSelectionWindow(QImage(8, 6, QImage.Format.Format_RGB32))
    mask = np.zeros((6, 8), dtype=np.bool_)
    mask[2:5, 3:7] = True

    window.set_mask(mask)

    assert window._cutout_bounds == QRect(3, 2, 4, 3)
    assert window._cutout_image is not None
    assert window._cutout_image.size() == QSize(4, 3)


def test_show_points_toggle_hides_markers_without_removing_prompts() -> None:
    window = ObjectSelectionWindow(QImage(3, 3, QImage.Format.Format_RGB32))
    window._points.append(PointPrompt(1, 1, PointLabel.INCLUDE))

    window._show_points_action.setChecked(False)

    assert not window._show_points
    assert window._show_points_action.text() == "Hide points"
    assert not window._show_points_action.icon().isNull()
    assert window.points == (PointPrompt(1, 1, PointLabel.INCLUDE),)


def test_color_menu_uses_compact_swatch_widgets() -> None:
    window = ObjectSelectionWindow(QImage(3, 3, QImage.Format.Format_RGB32))
    menu = window._color_button.menu()

    assert menu is not None
    swatches = []
    for action in menu.actions():
        assert isinstance(action, QWidgetAction)
        swatches.append(action.defaultWidget())
    assert all(swatch is not None for swatch in swatches)
    assert all(swatch.size().width() == 44 for swatch in swatches if swatch)
    assert menu.sizeHint().width() < 60


def test_opacity_label_and_slider_are_stacked() -> None:
    window = ObjectSelectionWindow(QImage(3, 3, QImage.Format.Format_RGB32))
    layout = window._opacity_group.layout()

    assert layout is not None
    assert layout.indexOf(window._opacity_label) < layout.indexOf(
        window._opacity_slider
    )
    assert window._opacity_label.alignment() & Qt.AlignmentFlag.AlignHCenter
    assert window._opacity_group.width() == 108
    assert window._opacity_slider.value() == 40


def test_unmodified_wheel_event_pans_in_both_axes_automatically() -> None:
    window = ObjectSelectionWindow(QImage(400, 300, QImage.Format.Format_RGB32))
    window._pan_by_view_delta = Mock()
    event = Mock()
    event.modifiers.return_value = Qt.KeyboardModifier.NoModifier
    event.pixelDelta.return_value = QPoint(18, -11)
    event.angleDelta.return_value = QPoint()
    event.phase.return_value = Qt.ScrollPhase.NoScrollPhase

    window.wheelEvent(event)

    window._pan_by_view_delta.assert_called_once_with(QPointF(18, -11))
    event.accept.assert_called_once()


def test_precision_angle_touchpad_event_pans_automatically() -> None:
    window = ObjectSelectionWindow(QImage(400, 300, QImage.Format.Format_RGB32))
    window._pan_by_view_delta = Mock()
    event = Mock()
    event.modifiers.return_value = Qt.KeyboardModifier.NoModifier
    event.pixelDelta.return_value = QPoint()
    event.angleDelta.return_value = QPoint(0, 24)
    event.phase.return_value = Qt.ScrollPhase.NoScrollPhase
    event.device.return_value.type.return_value = QInputDevice.DeviceType.Mouse

    window.wheelEvent(event)

    window._pan_by_view_delta.assert_called_once_with(QPointF(0, 12))
    event.accept.assert_called_once()


def test_control_modified_wheel_event_stays_out_of_pan_path() -> None:
    window = ObjectSelectionWindow(QImage(400, 300, QImage.Format.Format_RGB32))
    window._pan_by_view_delta = Mock()
    window._zoom_at = Mock(return_value=True)
    event = Mock()
    event.modifiers.return_value = Qt.KeyboardModifier.ControlModifier
    event.angleDelta.return_value = QPoint(0, 120)
    event.pixelDelta.return_value = QPoint()
    event.position.return_value = QPointF(200, 150)

    window.wheelEvent(event)

    window._pan_by_view_delta.assert_not_called()
    window._zoom_at.assert_called_once_with(QPointF(200, 150), 1)
    event.accept.assert_called_once()


def test_unmodified_notched_mouse_wheel_zooms() -> None:
    window = ObjectSelectionWindow(QImage(400, 300, QImage.Format.Format_RGB32))
    window._zoom_at = Mock(return_value=True)
    event = Mock()
    event.modifiers.return_value = Qt.KeyboardModifier.NoModifier
    event.angleDelta.return_value = QPoint(0, 120)
    event.pixelDelta.return_value = QPoint()
    event.phase.return_value = Qt.ScrollPhase.NoScrollPhase
    event.device.return_value.type.return_value = QInputDevice.DeviceType.Mouse
    event.position.return_value = QPointF(200, 150)

    window.wheelEvent(event)

    window._zoom_at.assert_called_once_with(QPointF(200, 150), 1)
    event.accept.assert_called_once()


def test_notched_wheel_zooms_when_linux_reports_touchpad_device() -> None:
    window = ObjectSelectionWindow(QImage(400, 300, QImage.Format.Format_RGB32))
    window._pan_by_view_delta = Mock()
    window._zoom_at = Mock(return_value=True)
    event = Mock()
    event.modifiers.return_value = Qt.KeyboardModifier.NoModifier
    event.angleDelta.return_value = QPoint(0, -120)
    event.pixelDelta.return_value = QPoint()
    event.phase.return_value = Qt.ScrollPhase.ScrollUpdate
    event.device.return_value.type.return_value = QInputDevice.DeviceType.TouchPad
    event.position.return_value = QPointF(200, 150)

    window.wheelEvent(event)

    window._pan_by_view_delta.assert_not_called()
    window._zoom_at.assert_called_once_with(QPointF(200, 150), -1)
    event.accept.assert_called_once()
