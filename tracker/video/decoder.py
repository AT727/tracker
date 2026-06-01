from __future__ import annotations

import hashlib
from typing import List, Optional, Tuple

import cv2
import numpy as np


class VideoDecoder:
    CACHE_SIZE = 30

    def __init__(self, path: str):
        self._path = path
        self._cap: Optional[cv2.VideoCapture] = None
        self._cache_start: int = 0
        self._cache: List[Optional[np.ndarray]] = [None] * self.CACHE_SIZE
        self._open()

    def _open(self):
        self._cap = cv2.VideoCapture(self._path)
        if not self._cap.isOpened():
            raise RuntimeError(f"Could not open video: {self._path}")

    @property
    def is_open(self) -> bool:
        return self._cap is not None and self._cap.isOpened()

    @property
    def frame_count(self) -> int:
        return int(self._cap.get(cv2.CAP_PROP_FRAME_COUNT))

    @property
    def fps(self) -> float:
        return self._cap.get(cv2.CAP_PROP_FPS)

    @property
    def width(self) -> int:
        return int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))

    @property
    def height(self) -> int:
        return int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    def get_frame(self, frame_index: int) -> Tuple[np.ndarray, float]:
        if not self.is_open:
            raise RuntimeError("Video capture is not open")

        if frame_index < 0 or frame_index >= self.frame_count:
            raise IndexError(
                f"Frame index {frame_index} out of range [0, {self.frame_count})"
            )

        if frame_index < self._cache_start or frame_index >= self._cache_start + self.CACHE_SIZE:
            self._clear_cache()
            self._seek_to(frame_index)
            self._cache_start = frame_index
            frame = self._decode_current()
            self._cache[0] = frame
            timestamp = self._current_timestamp()
            return frame, timestamp

        offset = frame_index - self._cache_start
        if self._cache[offset] is not None:
            return self._cache[offset], self._timestamp_for_frame(frame_index)

        self._seek_to(frame_index)
        frame = self._decode_current()
        self._cache[offset] = frame
        timestamp = self._current_timestamp()
        return frame, timestamp

    def first_frame_hash(self) -> str:
        original_pos = int(self._cap.get(cv2.CAP_PROP_POS_FRAMES))
        self._cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        ret, frame = self._cap.read()
        if not ret:
            raise RuntimeError("Could not read first frame")
        _, buf = cv2.imencode(".png", frame)
        digest = hashlib.sha256(buf.tobytes()).hexdigest()
        self._cap.set(cv2.CAP_PROP_POS_FRAMES, original_pos)
        return digest

    def _clear_cache(self):
        self._cache = [None] * self.CACHE_SIZE

    def _seek_to(self, frame_index: int):
        self._cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)

    def _decode_current(self) -> np.ndarray:
        ret, frame = self._cap.read()
        if not ret:
            raise RuntimeError(f"Could not decode frame at position")
        return frame

    def _current_timestamp(self) -> float:
        return self._cap.get(cv2.CAP_PROP_POS_MSEC) / 1000.0

    def _timestamp_for_frame(self, frame_index: int) -> float:
        original_pos = int(self._cap.get(cv2.CAP_PROP_POS_FRAMES))
        self._cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
        ret, _ = self._cap.read()
        if not ret:
            raise RuntimeError(f"Could not decode frame {frame_index} for timestamp")
        ts = self._current_timestamp()
        self._cap.set(cv2.CAP_PROP_POS_FRAMES, original_pos)
        return ts

    def close(self):
        if self._cap is not None:
            self._cap.release()
            self._cap = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
