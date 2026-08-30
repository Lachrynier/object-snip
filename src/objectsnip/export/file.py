from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QImage


def save_png(image: QImage, path: str | Path) -> None:
    if not image.save(str(path)):
        raise OSError("Qt could not write the PNG file")
