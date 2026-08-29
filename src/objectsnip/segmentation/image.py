from __future__ import annotations

from PySide6.QtGui import QImage

from objectsnip.segmentation.interface import ImageData


def image_data_from_qimage(image: QImage) -> ImageData:
    converted = image.convertToFormat(QImage.Format.Format_RGB888)
    return ImageData(
        width=converted.width(),
        height=converted.height(),
        bytes_per_line=converted.bytesPerLine(),
        rgb_bytes=bytes(converted.constBits()),
    )
