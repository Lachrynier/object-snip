from PySide6.QtCore import QPoint, QRect, QSize

from objectsnip.domain.geometry import Rect
from objectsnip.ui.overlay import lock_button_position, region_is_lockable

BUTTON = QSize(100, 30)
VIEWPORT = QSize(800, 600)


def test_lock_button_is_centered_below_selection() -> None:
    selection = QRect(200, 100, 300, 200)

    assert lock_button_position(selection, BUTTON, VIEWPORT) == QPoint(300, 311)


def test_lock_button_flips_above_selection_near_bottom_edge() -> None:
    selection = QRect(200, 500, 300, 80)

    assert lock_button_position(selection, BUTTON, VIEWPORT) == QPoint(300, 458)


def test_lock_button_is_clamped_at_horizontal_edges() -> None:
    left = QRect(0, 100, 20, 100)
    right = QRect(790, 100, 10, 100)

    assert lock_button_position(left, BUTTON, VIEWPORT).x() == 12
    assert lock_button_position(right, BUTTON, VIEWPORT).x() == 688


def test_lock_button_stays_inside_small_viewport() -> None:
    viewport = QSize(80, 20)
    selection = QRect(0, 0, 80, 20)

    assert lock_button_position(selection, BUTTON, viewport) == QPoint(0, 0)


def test_region_must_be_marked_and_large_enough_to_lock() -> None:
    assert not region_is_lockable(None, 8)
    assert not region_is_lockable(Rect(0, 0, 7, 8), 8)
    assert not region_is_lockable(Rect(0, 0, 8, 7), 8)
    assert region_is_lockable(Rect(0, 0, 8, 8), 8)
