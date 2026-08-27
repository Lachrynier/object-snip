import pytest
from PySide6.QtGui import QColor, QImage

from objectsnip.capture.crop import crop_context
from objectsnip.domain.geometry import Rect


def test_crop_context_returns_exact_enclosed_pixels() -> None:
    image = QImage(4, 3, QImage.Format.Format_RGB32)
    for y in range(image.height()):
        for x in range(image.width()):
            image.setPixelColor(x, y, QColor(x * 10, y * 20, 0))

    crop = crop_context(image, Rect(1, 1, 4, 3))

    assert (crop.width(), crop.height()) == (3, 2)
    assert crop.pixelColor(0, 0) == image.pixelColor(1, 1)
    assert crop.pixelColor(2, 1) == image.pixelColor(3, 2)


@pytest.mark.parametrize("bounds", [Rect(1, 1, 1, 2), Rect(-1, 0, 2, 2)])
def test_crop_context_rejects_invalid_bounds(bounds: Rect) -> None:
    with pytest.raises(ValueError):
        crop_context(QImage(10, 10, QImage.Format.Format_RGB32), bounds)
