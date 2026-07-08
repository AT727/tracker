import pytest
import numpy as np
from PyQt5.QtCore import QCoreApplication
from PyQt5.QtGui import QImage

from tracker.video.decoder_worker import VideoDecoderWorker


@pytest.fixture
def qapp():
    app = QCoreApplication.instance()
    if app is None:
        app = QCoreApplication([])
    return app


def test_decoder_opens_and_decodes(qapp, sample_video, qtbot):
    worker = VideoDecoderWorker()
    opened = {}

    def on_opened(fps, count, w, h):
        opened["fps"] = fps
        opened["count"] = count
        opened["w"] = w
        opened["h"] = h

    frames = {}

    def on_frame(index, image, ts):
        frames[index] = (image, ts)

    worker.opened.connect(on_opened)
    worker.frame_ready.connect(on_frame)
    worker.start()
    worker.open(str(sample_video))

    qtbot.waitUntil(lambda: "count" in opened, timeout=5000)
    worker.request_frame(0)
    qtbot.waitUntil(lambda: 0 in frames, timeout=5000)

    assert opened["count"] == 10
    assert opened["w"] == 64
    image, ts = frames[0]
    assert isinstance(image, QImage)
    assert ts >= 0.0

    worker.stop_worker()


def test_rapid_scrub_and_cache_hits(qapp, sample_video, qtbot):
    """Scrub coalesces to the latest frame; step requests are queued."""
    worker = VideoDecoderWorker()
    frames: dict[int, tuple] = {}

    worker.frame_ready.connect(lambda index, image, ts: frames.setdefault(index, (image, ts)))
    worker.start()
    worker.open(str(sample_video))

    qtbot.waitUntil(lambda: worker.frame_count > 0, timeout=5000)

    for i in range(10):
        worker.scrub_to_frame(i)
    qtbot.waitUntil(lambda: 9 in frames, timeout=5000)

    for _ in range(100):
        worker.request_frame(0)
    qtbot.waitUntil(lambda: 0 in frames, timeout=5000)

    for i in range(5):
        worker.request_frame(i)
    qtbot.waitUntil(lambda: 4 in frames, timeout=5000)

    worker.stop_worker()


def test_decode_skips_seek_for_sequential_reads(qapp, monkeypatch):
    """
    Sequential forward reads should not repeatedly call CAP_PROP_POS_FRAMES seeks.

    This is a regression test for performance: on some codecs, CAP_PROP_POS_FRAMES can
    be reported imprecisely, causing avoidable cap.set() calls.
    """

    import cv2

    class FakeCapture:
        def __init__(self, w: int = 8, h: int = 6) -> None:
            self._w = w
            self._h = h
            self._opened = True
            self.set_calls = 0
            self.pos_frames = 0

        def isOpened(self) -> bool:
            return self._opened

        def release(self) -> None:
            self._opened = False

        def get(self, prop_id: int) -> float:
            if prop_id == cv2.CAP_PROP_POS_FRAMES:
                # Deliberately "wrong" by 1 to trigger cap.set() in the old logic.
                return float(self.pos_frames - 1)
            if prop_id == cv2.CAP_PROP_POS_MSEC:
                return float(self.pos_frames * 40)
            if prop_id == cv2.CAP_PROP_FPS:
                return 40.0
            if prop_id == cv2.CAP_PROP_FRAME_COUNT:
                return 100
            if prop_id == cv2.CAP_PROP_FRAME_WIDTH:
                return float(self._w)
            if prop_id == cv2.CAP_PROP_FRAME_HEIGHT:
                return float(self._h)
            return 0.0

        def set(self, prop_id: int, value: float) -> bool:
            if prop_id == cv2.CAP_PROP_POS_FRAMES:
                self.pos_frames = int(value)
                self.set_calls += 1
                return True
            return False

        def read(self):
            frame = np.zeros((self._h, self._w, 3), dtype=np.uint8)
            # BGR: set blue channel to encode "frame identity".
            frame[:, :, 0] = self.pos_frames % 255
            self.pos_frames += 1
            return True, frame

    worker = VideoDecoderWorker()
    fake = FakeCapture()
    worker._cap = fake  # type: ignore[attr-defined]
    worker._fps = 40.0  # type: ignore[attr-defined]

    # Decode frames 0, 1, 2 in sequence.
    worker._decode_frame(0)
    worker._decode_frame(1)
    worker._decode_frame(2)

    # With sequential optimization we should seek only for the first frame.
    assert fake.set_calls == 1


def test_infer_cache_size_respects_bounds():
    assert VideoDecoderWorker._infer_cache_size(0, 0) == 60
    assert VideoDecoderWorker._infer_cache_size(768, 432) == 300   # ~332K px
    assert VideoDecoderWorker._infer_cache_size(1920, 1080) == 48   # ~2.07M px
    assert VideoDecoderWorker._infer_cache_size(3840, 2160) == 30   # ~8.29M px
    assert VideoDecoderWorker._infer_cache_size(1, 1) == 300        # clamp
