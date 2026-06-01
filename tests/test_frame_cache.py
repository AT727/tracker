from tracker.video.frame_cache import FrameCache


def test_lru_eviction_at_61():
    cache: FrameCache[int] = FrameCache(max_size=60)
    for i in range(61):
        cache.put(i, i)
    assert len(cache) == 60
    assert cache.get(0) is None
    assert cache.get(60) == 60


def test_get_moves_to_end():
    cache: FrameCache[str] = FrameCache(max_size=2)
    cache.put(0, "a")
    cache.put(1, "b")
    cache.get(0)
    cache.put(2, "c")
    assert cache.get(0) == "a"
    assert cache.get(1) is None
