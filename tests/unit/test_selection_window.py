from PySide6.QtCore import QPoint, QRect, QSize

from objectsnip.ui.selection_window import fitted_image_rect, view_to_image_point


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
    target = QRect(100, 50, 400, 200)

    assert view_to_image_point(QPoint(300, 150), target, QSize(100, 50)) == (
        50.0,
        25.0,
    )
    assert view_to_image_point(QPoint(50, 50), target, QSize(100, 50)) is None
