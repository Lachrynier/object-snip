from PySide6.QtGui import QColor, QImage

from objectsnip.export.file import save_png


def test_save_png_writes_a_readable_transparent_image(tmp_path) -> None:
    image = QImage(2, 1, QImage.Format.Format_RGBA8888)
    image.setPixelColor(0, 0, QColor(10, 20, 30, 0))
    image.setPixelColor(1, 0, QColor(40, 50, 60, 255))
    path = tmp_path / "cutout.png"

    save_png(image, path)

    saved = QImage(str(path))
    assert not saved.isNull()
    assert saved.hasAlphaChannel()
    assert saved.pixelColor(0, 0).alpha() == 0
    assert saved.pixelColor(1, 0).alpha() == 255
