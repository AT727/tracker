import pytest
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
