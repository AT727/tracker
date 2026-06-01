import numpy as np
import pytest
from tracker.video.decoder import VideoDecoder

SAMPLE_VIDEO = "PhaseII_TestD_0001_c4_01.MP4"


def test_decoder_opens_video():
    with VideoDecoder(SAMPLE_VIDEO) as dec:
        assert dec.is_open
        assert dec.frame_count > 0
        assert dec.fps > 0
        assert dec.width > 0
        assert dec.height > 0


def test_get_frame_returns_valid_frame():
    with VideoDecoder(SAMPLE_VIDEO) as dec:
        frame, ts = dec.get_frame(0)
        assert isinstance(frame, np.ndarray)
        assert frame.shape[2] == 3
        assert ts >= 0.0


def test_get_frame_timestamp_increases():
    with VideoDecoder(SAMPLE_VIDEO) as dec:
        _, ts0 = dec.get_frame(0)
        _, ts1 = dec.get_frame(1)
        assert ts1 > ts0


def test_get_frame_caches_forward():
    with VideoDecoder(SAMPLE_VIDEO) as dec:
        f0a, _ = dec.get_frame(0)
        f0b, _ = dec.get_frame(0)
        assert np.array_equal(f0a, f0b)


def test_first_frame_hash_is_hex():
    with VideoDecoder(SAMPLE_VIDEO) as dec:
        h = dec.first_frame_hash()
        assert isinstance(h, str)
        assert len(h) == 64
        int(h, 16)


def test_decoder_out_of_range():
    with VideoDecoder(SAMPLE_VIDEO) as dec:
        with pytest.raises(IndexError):
            dec.get_frame(dec.frame_count + 1)
