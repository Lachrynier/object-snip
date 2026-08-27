from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto


@dataclass(frozen=True, slots=True)
class Point:
    x: int
    y: int


@dataclass(frozen=True, slots=True)
class Size:
    width: int
    height: int

    def __post_init__(self) -> None:
        if self.width < 0 or self.height < 0:
            raise ValueError("size cannot be negative")


@dataclass(frozen=True, slots=True)
class Rect:
    """An integer, half-open rectangle: [left, right) × [top, bottom)."""

    left: int
    top: int
    right: int
    bottom: int

    @classmethod
    def from_points(cls, first: Point, second: Point) -> Rect:
        return cls(
            min(first.x, second.x),
            min(first.y, second.y),
            max(first.x, second.x),
            max(first.y, second.y),
        )

    @property
    def width(self) -> int:
        return self.right - self.left

    @property
    def height(self) -> int:
        return self.bottom - self.top

    @property
    def is_valid(self) -> bool:
        return self.width > 0 and self.height > 0

    def clamp(self, bounds: Size) -> Rect:
        return Rect(
            max(0, min(self.left, bounds.width)),
            max(0, min(self.top, bounds.height)),
            max(0, min(self.right, bounds.width)),
            max(0, min(self.bottom, bounds.height)),
        )

    def moved(self, dx: int, dy: int, bounds: Size) -> Rect:
        dx = max(-self.left, min(dx, bounds.width - self.right))
        dy = max(-self.top, min(dy, bounds.height - self.bottom))
        return Rect(
            self.left + dx,
            self.top + dy,
            self.right + dx,
            self.bottom + dy,
        )


class Handle(Enum):
    OUTSIDE = auto()
    MOVE = auto()
    LEFT = auto()
    RIGHT = auto()
    TOP = auto()
    BOTTOM = auto()
    TOP_LEFT = auto()
    TOP_RIGHT = auto()
    BOTTOM_LEFT = auto()
    BOTTOM_RIGHT = auto()


def hit_test(rect: Rect, point: Point, tolerance: int) -> Handle:
    if tolerance < 0:
        raise ValueError("tolerance cannot be negative")

    near_left = abs(point.x - rect.left) <= tolerance
    near_right = abs(point.x - rect.right) <= tolerance
    near_top = abs(point.y - rect.top) <= tolerance
    near_bottom = abs(point.y - rect.bottom) <= tolerance
    within_x = rect.left - tolerance <= point.x <= rect.right + tolerance
    within_y = rect.top - tolerance <= point.y <= rect.bottom + tolerance

    if near_left and near_top:
        return Handle.TOP_LEFT
    if near_right and near_top:
        return Handle.TOP_RIGHT
    if near_left and near_bottom:
        return Handle.BOTTOM_LEFT
    if near_right and near_bottom:
        return Handle.BOTTOM_RIGHT
    if near_left and within_y:
        return Handle.LEFT
    if near_right and within_y:
        return Handle.RIGHT
    if near_top and within_x:
        return Handle.TOP
    if near_bottom and within_x:
        return Handle.BOTTOM
    if rect.left < point.x < rect.right and rect.top < point.y < rect.bottom:
        return Handle.MOVE
    return Handle.OUTSIDE


def resize_rect(
    rect: Rect,
    handle: Handle,
    point: Point,
    bounds: Size,
    minimum_size: int = 1,
) -> Rect:
    if minimum_size < 1:
        raise ValueError("minimum_size must be positive")

    x = max(0, min(point.x, bounds.width))
    y = max(0, min(point.y, bounds.height))
    left, top, right, bottom = rect.left, rect.top, rect.right, rect.bottom

    if handle in {Handle.LEFT, Handle.TOP_LEFT, Handle.BOTTOM_LEFT}:
        left = min(x, right - minimum_size)
    if handle in {Handle.RIGHT, Handle.TOP_RIGHT, Handle.BOTTOM_RIGHT}:
        right = max(x, left + minimum_size)
    if handle in {Handle.TOP, Handle.TOP_LEFT, Handle.TOP_RIGHT}:
        top = min(y, bottom - minimum_size)
    if handle in {Handle.BOTTOM, Handle.BOTTOM_LEFT, Handle.BOTTOM_RIGHT}:
        bottom = max(y, top + minimum_size)

    return Rect(left, top, right, bottom).clamp(bounds)
