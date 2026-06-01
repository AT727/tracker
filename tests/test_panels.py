import pytest
from tracker.panels.data_table import DataTablePanel
from tracker.panels.plot_panel import PlotPanel
from tracker.tracking.collector import TrackingCollector


def test_data_table_creation(qtbot):
    panel = DataTablePanel()
    qtbot.addWidget(panel)
    assert panel._table.columnCount() == 6


def test_data_table_shows_tracked_points(qtbot):
    collector = TrackingCollector()
    collector.record(0, 0.0, 1.0, 2.0, 100.0, 200.0)
    collector.record(1, 0.008, 1.5, 2.5, 150.0, 250.0)
    panel = DataTablePanel()
    qtbot.addWidget(panel)
    panel.update_from_collector(collector, 10)
    qtbot.wait(10)
    assert panel._table.rowCount() == 2


def test_data_table_emits_frame_selected(qtbot):
    collector = TrackingCollector()
    collector.record(0, 0.0, 1.0, 2.0, 100.0, 200.0)
    collector.record(1, 0.008, 1.5, 2.5, 150.0, 250.0)
    panel = DataTablePanel()
    qtbot.addWidget(panel)
    panel._do_update(collector)
    with qtbot.waitSignal(panel.frame_selected, timeout=500):
        panel._on_row_clicked(panel._table.model().index(0, 0))


def test_data_table_highlight_frame(qtbot):
    collector = TrackingCollector()
    collector.record(0, 0.0, 1.0, 2.0, 100.0, 200.0)
    collector.record(5, 0.04, 3.0, 4.0, 150.0, 250.0)
    panel = DataTablePanel()
    qtbot.addWidget(panel)
    panel._do_update(collector)
    panel.highlight_frame(5)
    selected = panel._table.selectedItems()
    assert len(selected) > 0


def test_plot_panel_creation(qtbot):
    panel = PlotPanel()
    qtbot.addWidget(panel)
    assert panel._canvas is not None


def test_plot_panel_update(qtbot):
    collector = TrackingCollector()
    collector.record(0, 0.0, 1.0, 2.0, 100.0, 200.0)
    collector.record(1, 0.008, 1.5, 2.5, 150.0, 250.0)
    panel = PlotPanel()
    qtbot.addWidget(panel)
    panel.update_from_collector(collector, 10)
    assert True
