"""LRU frame cache keyed by frame index."""

from __future__ import annotations

from collections import OrderedDict
from typing import Generic, Optional, TypeVar

T = TypeVar("T")


class FrameCache(Generic[T]):
    def __init__(self, max_size: int = 60) -> None:
        if max_size < 1:
            raise ValueError("max_size must be >= 1")
        self._max_size = max_size
        self._cache: OrderedDict[int, T] = OrderedDict()

    @property
    def max_size(self) -> int:
        return self._max_size

    def __len__(self) -> int:
        return len(self._cache)

    def get(self, frame_index: int) -> Optional[T]:
        if frame_index not in self._cache:
            return None
        self._cache.move_to_end(frame_index)
        return self._cache[frame_index]

    def put(self, frame_index: int, value: T) -> None:
        if frame_index in self._cache:
            self._cache.move_to_end(frame_index)
            self._cache[frame_index] = value
        else:
            self._cache[frame_index] = value
        while len(self._cache) > self._max_size:
            self._cache.popitem(last=False)

    def contains(self, frame_index: int) -> bool:
        return frame_index in self._cache

    def clear(self) -> None:
        self._cache.clear()

    def evict_farthest_from(self, frame_index: int) -> None:
        """Evict the cached frame farthest from the given index when over capacity."""
        while len(self._cache) > self._max_size:
            farthest = max(self._cache.keys(), key=lambda k: abs(k - frame_index))
            del self._cache[farthest]
