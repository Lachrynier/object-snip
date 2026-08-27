from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from PySide6.QtGui import QImage


def save_png(image: QImage, path: Path) -> None:
    if image.isNull():
        raise ValueError("cannot save a null debug image")
    if not image.save(str(path)):
        raise OSError(f"could not save debug image to {path}")


@dataclass(frozen=True, slots=True)
class DebugCaptureSession:
    source_path: Path
    region_path: Path

    def save_region(self, image: QImage) -> Path:
        save_png(image, self.region_path)
        print(f"ObjectSnip debug region: {self.region_path.resolve()}", flush=True)
        return self.region_path


class DebugCaptureWriter:
    def __init__(self, directory: Path) -> None:
        self.directory = directory

    def begin(self, source: QImage) -> DebugCaptureSession:
        self.directory.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        session = DebugCaptureSession(
            source_path=self.directory / f"{timestamp}-source.png",
            region_path=self.directory / f"{timestamp}-region.png",
        )
        save_png(source, session.source_path)
        print(f"ObjectSnip debug source: {session.source_path.resolve()}", flush=True)
        return session
