from pathlib import Path

from PySide6.QtGui import QColor, QImage

from objectsnip.debug_capture import DebugCaptureWriter


def image(color: str, width: int, height: int) -> QImage:
    result = QImage(width, height, QImage.Format.Format_RGB32)
    result.fill(QColor(color))
    return result


def test_debug_writer_saves_paired_source_and_region(tmp_path: Path) -> None:
    session = DebugCaptureWriter(tmp_path).begin(image("red", 20, 10))
    region_path = session.save_region(image("blue", 5, 4))

    source = QImage(str(session.source_path))
    region = QImage(str(region_path))
    assert (source.width(), source.height()) == (20, 10)
    assert source.pixelColor(0, 0) == QColor("red")
    assert (region.width(), region.height()) == (5, 4)
    assert region.pixelColor(0, 0) == QColor("blue")
    assert session.source_path.name.endswith("-source.png")
    assert region_path.name.endswith("-region.png")
    assert session.source_path.stem.removesuffix("-source") == (
        region_path.stem.removesuffix("-region")
    )
