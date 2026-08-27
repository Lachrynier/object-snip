from PySide6.QtGui import QColor, QImage

from objectsnip.capture.screen import image_is_uniform


def test_uniform_image_is_detected() -> None:
    image = QImage(20, 20, QImage.Format.Format_RGB32)
    image.fill(QColor("black"))
    assert image_is_uniform(image)


def test_non_uniform_image_is_not_detected() -> None:
    image = QImage(20, 20, QImage.Format.Format_RGB32)
    image.fill(QColor("black"))
    image.setPixelColor(10, 10, QColor("white"))
    assert not image_is_uniform(image, samples_per_axis=20)
