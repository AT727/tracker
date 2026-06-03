"""QThread video decoder with LRU frame cache."""

from __future__ import annotations

import cv2
from PyQt5.QtCore import QMutex, QMutexLocker, QThread, pyqtSignal
from PyQt5.QtGui import QImage

from tracker.video.frame_cache import FrameCache


class VideoDecoderWorker(QThread):
    opened = pyqtSignal(float, int, int, int)  # fps, frame_count, width, height
    frame_ready = pyqtSignal(int, object, float)  # index, QImage, timestamp_s
    frame_failed = pyqtSignal(int)
    open_failed = pyqtSignal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._mutex = QMutex()
        self._path: str | None = None
        self._open_path: str | None = None
        self._cap: cv2.VideoCapture | None = None
        self._fps = 30.0
        self._frame_count = 0
        self._width = 0
        self._height = 0
        # Tracks the logical frame index corresponding to the last successful decode.
        # This lets us skip CAP_PROP_POS_FRAMES seeks for sequential forward reads.
        self._cap_pos_index: int | None = None
        self._cache: FrameCache[tuple[QImage, float]] = FrameCache(max_size=60)
        self._scrub_frame: int | None = None
        self._pending: list[int] = []
        self._prefetch_pending: list[int] = []
        self._running = True

    @property
    def fps(self) -> float:
        return self._fps

    @property
    def frame_count(self) -> int:
        return self._frame_count

    def open(self, path: str) -> None:
        with QMutexLocker(self._mutex):
            self._path = path
            self._scrub_frame = None
            self._pending.clear()
            self._prefetch_pending.clear()
            self._cache.clear()
            self._cap_pos_index = None

    def request_frame(self, index: int) -> None:
        """Queue a frame for step navigation (prev/next, click-advance)."""
        cached = self._emit_if_cached(index)
        if cached is not None:
            return
        with QMutexLocker(self._mutex):
            if index not in self._pending:
                self._pending.append(index)

    def scrub_to_frame(self, index: int) -> None:
        """Jump to a frame; coalesce rapid scrubber moves to the latest index."""
        cached = self._emit_if_cached(index)
        if cached is not None:
            with QMutexLocker(self._mutex):
                self._prefetch_pending.clear()
            return
        with QMutexLocker(self._mutex):
            self._scrub_frame = index
            self._pending.clear()
            self._prefetch_pending.clear()

    def prefetch(self, from_index: int, count: int = 5) -> None:
        with QMutexLocker(self._mutex):
            self._prefetch_pending.clear()
            for i in range(from_index, from_index + count):
                if i >= self._frame_count:
                    break
                if self._cache.contains(i):
                    continue
                if i == self._scrub_frame or i in self._pending:
                    continue
                if i not in self._prefetch_pending:
                    self._prefetch_pending.append(i)

    def stop_worker(self) -> None:
        self._running = False
        self.wait(5000)

    def _emit_if_cached(self, index: int) -> tuple[QImage, float] | None:
        with QMutexLocker(self._mutex):
            cached = self._cache.get(index)
        if cached is not None:
            image, ts = cached
            self.frame_ready.emit(index, image, ts)
            return cached
        return None

    def run(self) -> None:
        while self._running:
            path: str | None
            index: int | None
            emit_when_done = False
            with QMutexLocker(self._mutex):
                path = self._path
                if self._scrub_frame is not None:
                    index = self._scrub_frame
                    emit_when_done = True
                elif self._pending:
                    index = self._pending.pop(0)
                    emit_when_done = True
                elif self._prefetch_pending:
                    index = self._prefetch_pending.pop(0)
                else:
                    index = None

            if path is None:
                self.msleep(10)
                continue

            if self._cap is None or self._open_path != path:
                self._open_capture(path)

            if self._cap is None or not self._cap.isOpened():
                self.msleep(10)
                continue

            if index is None:
                self.msleep(5)
                continue

            with QMutexLocker(self._mutex):
                cached = self._cache.get(index)
            if cached is not None:
                if emit_when_done:
                    image, ts = cached
                    with QMutexLocker(self._mutex):
                        if self._scrub_frame == index:
                            self._scrub_frame = None
                    self.frame_ready.emit(index, image, ts)
                continue

            decoded = self._decode_frame(index)
            if decoded is None:
                if emit_when_done:
                    with QMutexLocker(self._mutex):
                        if self._scrub_frame == index:
                            self._scrub_frame = None
                    self.frame_failed.emit(index)
                continue

            image, ts = decoded
            with QMutexLocker(self._mutex):
                self._cache.put(index, (image, ts))
                if self._scrub_frame == index:
                    self._scrub_frame = None
            if emit_when_done:
                self.frame_ready.emit(index, image, ts)

    def _open_capture(self, path: str) -> None:
        if self._cap is not None:
            self._cap.release()
        cap = cv2.VideoCapture(path)
        if not cap.isOpened():
            self.open_failed.emit(f"Could not open video: {path}")
            self._cap = None
            return
        self._cap = cap
        self._open_path = path
        self._fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        self._frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        self._width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        self._height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
        self._cache.clear()
        self._cap_pos_index = None
        self.opened.emit(self._fps, self._frame_count, self._width, self._height)

    def _decode_frame(self, index: int) -> tuple[QImage, float] | None:
        if self._cap is None:
            return None
        if self._cap_pos_index is None:
            # First decode after open/scrub: seek once.
            self._cap.set(cv2.CAP_PROP_POS_FRAMES, index)
        elif index == self._cap_pos_index + 1:
            # Sequential forward read: no seek, just read the next frame.
            pass
        else:
            # Non-sequential (seek backward, jumps, etc.): seek.
            self._cap.set(cv2.CAP_PROP_POS_FRAMES, index)

        ok, frame = self._cap.read()
        if not ok or frame is None:
            return None

        # Use index/fps to avoid an extra CAP_PROP_POS_MSEC get() per frame.
        timestamp_s = index / self._fps if self._fps > 0 else 0.0

        self._cap_pos_index = index
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        bytes_per_line = ch * w
        qimg = QImage(rgb.data, w, h, bytes_per_line, QImage.Format_RGB888).copy()
        return qimg, timestamp_s
