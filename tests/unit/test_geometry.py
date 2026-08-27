import pytest

from objectsnip.domain.geometry import Handle, Point, Rect, Size, hit_test, resize_rect


def test_from_points_normalizes_every_drag_direction() -> None:
    expected = Rect(10, 20, 50, 70)
    assert Rect.from_points(Point(10, 20), Point(50, 70)) == expected
    assert Rect.from_points(Point(50, 70), Point(10, 20)) == expected
    assert Rect.from_points(Point(10, 70), Point(50, 20)) == expected
    assert Rect.from_points(Point(50, 20), Point(10, 70)) == expected


def test_move_preserves_size_and_clamps_to_bounds() -> None:
    rect = Rect(20, 30, 60, 80)
    assert rect.moved(-100, 100, Size(90, 100)) == Rect(0, 50, 40, 100)


@pytest.mark.parametrize(
    ("point", "expected"),
    [
        (Point(10, 10), Handle.TOP_LEFT),
        (Point(50, 10), Handle.TOP_RIGHT),
        (Point(10, 40), Handle.BOTTOM_LEFT),
        (Point(50, 40), Handle.BOTTOM_RIGHT),
        (Point(10, 25), Handle.LEFT),
        (Point(50, 25), Handle.RIGHT),
        (Point(30, 10), Handle.TOP),
        (Point(30, 40), Handle.BOTTOM),
        (Point(30, 25), Handle.MOVE),
        (Point(70, 70), Handle.OUTSIDE),
    ],
)
def test_hit_test(point: Point, expected: Handle) -> None:
    assert hit_test(Rect(10, 10, 50, 40), point, tolerance=2) is expected


def test_resize_corner_obeys_minimum_size() -> None:
    result = resize_rect(
        Rect(10, 10, 50, 50),
        Handle.TOP_LEFT,
        Point(49, 49),
        Size(100, 100),
        minimum_size=8,
    )
    assert result == Rect(42, 42, 50, 50)


def test_resize_is_clamped_to_image_bounds() -> None:
    result = resize_rect(
        Rect(10, 10, 50, 50),
        Handle.BOTTOM_RIGHT,
        Point(500, 500),
        Size(100, 80),
    )
    assert result == Rect(10, 10, 100, 80)
