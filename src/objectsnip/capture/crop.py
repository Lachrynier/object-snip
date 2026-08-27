from PySide6.QtGui import QImage

from objectsnip.domain.geometry import Rect


def crop_context(image: QImage, bounds: Rect) -> QImage:
    if not bounds.is_valid:
        raise ValueError("context bounds must be non-empty")
    if (
        bounds.left < 0
        or bounds.top < 0
        or bounds.right > image.width()
        or bounds.bottom > image.height()
    ):
        raise ValueError("context bounds must be inside the captured image")
    return image.copy(bounds.left, bounds.top, bounds.width, bounds.height)
