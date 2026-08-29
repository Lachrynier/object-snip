from threading import Event
from time import monotonic

from PySide6.QtCore import QCoreApplication

from objectsnip.segmentation.fake import FakeImageSegmenter
from objectsnip.segmentation.interface import (
    ImageData,
    ImageEncoding,
    PointLabel,
    PointPrompt,
    PredictionRequest,
    SegmentationResult,
)
from objectsnip.segmentation.service import ImageEncodingService

IMAGE = ImageData(
    width=1,
    height=1,
    bytes_per_line=3,
    rgb_bytes=b"\x00\x01\x02",
)


def wait_for(event: Event, timeout: float) -> bool:
    application = QCoreApplication.instance() or QCoreApplication([])
    deadline = monotonic() + timeout
    while monotonic() < deadline:
        application.processEvents()
        if event.wait(0.01):
            return True
    application.processEvents()
    return event.is_set()


def test_encoding_service_completes_in_background() -> None:
    service = ImageEncodingService(FakeImageSegmenter())
    completed = Event()
    result: list[tuple[int, object]] = []
    service.encoded.connect(
        lambda request, encoding: (
            result.append((request, encoding)),
            completed.set(),
        )
    )

    request = service.encode(IMAGE)

    assert wait_for(completed, 1)
    assert result[0][0] == request
    assert isinstance(result[0][1], ImageEncoding)
    service.close()


class BlockingSegmenter(FakeImageSegmenter):
    def __init__(self, release: Event) -> None:
        super().__init__()
        self._release = release

    def set_image(self, image: ImageData) -> ImageEncoding:
        self._release.wait(1)
        return super().set_image(image)


def test_encoding_service_discards_invalidated_result() -> None:
    release = Event()
    service = ImageEncodingService(BlockingSegmenter(release))
    completed = Event()
    service.encoded.connect(lambda _request, _encoding: completed.set())

    service.encode(IMAGE)
    service.invalidate()
    release.set()

    assert not wait_for(completed, 0.1)
    service.close()


class FailFirstLoadSegmenter(FakeImageSegmenter):
    def __init__(self) -> None:
        super().__init__()
        self.load_attempts = 0

    def load(self) -> None:
        self.load_attempts += 1
        if self.load_attempts == 1:
            raise RuntimeError("model load failed")


def test_encoding_service_recovers_from_failed_startup_prewarm() -> None:
    segmenter = FailFirstLoadSegmenter()
    service = ImageEncodingService(segmenter)
    completed = Event()
    service.encoded.connect(lambda _request, _encoding: completed.set())

    service.encode(IMAGE)

    assert wait_for(completed, 1)
    assert segmenter.load_attempts == 2
    service.close()


def test_prediction_service_returns_segmentation_result() -> None:
    service = ImageEncodingService(FakeImageSegmenter())
    encoded = Event()
    predicted = Event()
    result: list[object] = []
    service.encoded.connect(lambda _request, _encoding: encoded.set())
    service.predicted.connect(
        lambda _request, prediction: (result.append(prediction), predicted.set())
    )
    service.encode(IMAGE)
    assert wait_for(encoded, 1)

    service.predict(PredictionRequest(points=(PointPrompt(0, 0, PointLabel.INCLUDE),)))

    assert wait_for(predicted, 1)
    assert isinstance(result[0], SegmentationResult)
    service.close()
