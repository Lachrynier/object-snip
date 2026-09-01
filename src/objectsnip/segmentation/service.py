from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from threading import Event, Lock

from PySide6.QtCore import QObject, Signal, Slot

from objectsnip.segmentation.interface import (
    ImageData,
    ImageSegmenter,
    PredictionRequest,
    SegmentationResult,
)


class ImageEncodingService(QObject):
    encoded = Signal(int, object)
    failed = Signal(int, str)
    predicted = Signal(int, object)
    prediction_failed = Signal(int, str)

    def __init__(self, encoder: ImageSegmenter, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._encoder = encoder
        self._executor = ThreadPoolExecutor(
            max_workers=1,
            thread_name_prefix="objectsnip-encoder",
        )
        self._lock = Lock()
        self._generation = 0
        self._closed = False
        self._loaded = Event()
        self._load_future = self._executor.submit(self._load_encoder)

    def encode(self, image: ImageData) -> int:
        with self._lock:
            if self._closed:
                raise RuntimeError("image encoder is closed")
            self._generation += 1
            generation = self._generation
        future = self._executor.submit(self._encode_after_load, image)
        future.add_done_callback(
            lambda completed, request=generation: self._encoding_finished(
                request, completed
            )
        )
        return generation

    def predict(self, request: PredictionRequest) -> int:
        with self._lock:
            if self._closed:
                raise RuntimeError("image encoder is closed")
            self._generation += 1
            generation = self._generation
        future = self._executor.submit(self._encoder.predict, request)
        future.add_done_callback(
            lambda completed, request_id=generation: self._prediction_finished(
                request_id, completed
            )
        )
        return generation

    def invalidate(self) -> None:
        with self._lock:
            self._generation += 1

    @Slot()
    def close(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True
            self._generation += 1
        self._executor.shutdown(wait=False, cancel_futures=True)

    def _encode_after_load(self, image: ImageData) -> object:
        if not self._loaded.is_set():
            try:
                self._load_future.result()
            except Exception:
                self._load_encoder()
        return self._encoder.set_image(image)

    def _load_encoder(self) -> None:
        self._encoder.load()
        self._loaded.set()

    def _encoding_finished(self, generation: int, future: Future[object]) -> None:
        with self._lock:
            current = generation == self._generation and not self._closed
        if not current or future.cancelled():
            return
        try:
            encoding = future.result()
        except Exception as exc:
            self.failed.emit(generation, str(exc))
            return
        self.encoded.emit(generation, encoding)

    def _prediction_finished(
        self, generation: int, future: Future[SegmentationResult]
    ) -> None:
        with self._lock:
            current = generation == self._generation and not self._closed
        if not current or future.cancelled():
            return
        try:
            result = future.result()
        except Exception as exc:
            self.prediction_failed.emit(generation, str(exc))
            return
        self.predicted.emit(generation, result)
