from tracker.coordinates.pipeline import CoordinatePipeline
from tracker.panels.data_table import DataTablePanel
from tracker.tracking.collector import TrackingCollector


def test_refresh_renders_gap_separator_row(qtbot):
    panel = DataTablePanel()
    qtbot.addWidget(panel)
    collector = TrackingCollector()
    collector.upsert_mark(0, 0.0, 10.0, 10.0)
    collector.upsert_mark(2, 0.1, 11.0, 11.0)
    active_series_id = collector.active_series_id
    assert active_series_id is not None

    panel.refresh(
        collector,
        CoordinatePipeline(),
        series_id=active_series_id,
        gap_after_frames={0},
    )

    assert panel.rowCount() == 3
    assert panel.item(1, 1).text() == "missing frame(s)"


def test_refresh_filters_to_active_series(qtbot):
    panel = DataTablePanel()
    qtbot.addWidget(panel)
    collector = TrackingCollector()
    first_series_id = collector.active_series_id
    assert first_series_id is not None
    second_series = collector.add_series("Second")
    collector.upsert_mark(0, 0.0, 10.0, 10.0, series_id=first_series_id)
    collector.upsert_mark(1, 0.1, 11.0, 11.0, series_id=second_series.id)

    panel.refresh(
        collector,
        CoordinatePipeline(),
        series_id=first_series_id,
        gap_after_frames=set(),
    )

    assert panel.rowCount() == 1
    assert panel.item(0, 0).text() == "1"
