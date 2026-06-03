"""Shared pytest fixtures."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pytest


@pytest.fixture
def sample_video(tmp_path: Path) -> Path:
    path = tmp_path / "test.mp4"
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(path), fourcc, 30.0, (64, 48))
    for i in range(10):
        frame = np.zeros((48, 64, 3), dtype=np.uint8)
        frame[:, :, 0] = i * 20
        writer.write(frame)
    writer.release()
    return path
