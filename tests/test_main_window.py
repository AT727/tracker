from unittest.mock import MagicMock, patch

from tracker.app.main_window import MainWindow
from tracker.mutations.models import ColumnMutation


def test_main_window_has_mutations_attribute(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    assert isinstance(window._mutations, list)


def test_main_window_loads_mutations_from_store(qtbot):
    expected = [
        ColumnMutation(name="norm_x", formula="x * 2"),
    ]
    with patch("tracker.app.main_window.MutationStore.load", return_value=expected):
        window = MainWindow()
        qtbot.addWidget(window)
    assert window._mutations == expected


def test_main_window_refresh_table_passes_mutations(qtbot):
    mutations = [ColumnMutation(name="m", formula="x + 1")]
    with patch("tracker.app.main_window.MutationStore.load", return_value=mutations):
        window = MainWindow()
        qtbot.addWidget(window)

    with patch.object(window._data_table, "refresh") as mock_refresh:
        window._refresh_table()

    _, kwargs = mock_refresh.call_args
    assert kwargs.get("mutations") == mutations
