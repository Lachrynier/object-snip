from PySide6.QtGui import QCursor, QGuiApplication, QImage, QScreen


def screen_at_pointer() -> QScreen:
    pointer_screen = QGuiApplication.screenAt(QCursor.pos())
    if pointer_screen is not None:
        return pointer_screen
    screen = QGuiApplication.primaryScreen()
    if screen is None:
        raise RuntimeError("no screen is available")
    return screen


def capture_screen(screen: QScreen) -> QImage:
    image = screen.grabWindow(0).toImage()
    if image.isNull():
        raise RuntimeError("screen capture returned no pixels")
    image.setDevicePixelRatio(1.0)
    return image


def image_is_uniform(image: QImage, samples_per_axis: int = 12) -> bool:
    """Quickly detect unusable single-color captures such as an XWayland root."""

    if image.isNull() or samples_per_axis < 1:
        return True
    x_step = max(1, image.width() // samples_per_axis)
    y_step = max(1, image.height() // samples_per_axis)
    first = image.pixel(0, 0)
    return all(
        image.pixel(x, y) == first
        for x in range(0, image.width(), x_step)
        for y in range(0, image.height(), y_step)
    )
