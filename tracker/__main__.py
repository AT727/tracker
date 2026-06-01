"""Entry point: python -m tracker"""

import sys

from PyQt5.QtWidgets import QApplication

from tracker.app.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Tracker")

    # Load stylesheet
    try:
        from pathlib import Path
        style_path = Path(__file__).parent / "app" / "style.qss"
        if style_path.exists():
            with open(style_path, "r", encoding="utf-8") as f:
                app.setStyleSheet(f.read())
    except Exception as e:
        print(f"Warning: Failed to load stylesheet: {e}")

    window = MainWindow()
    window.show()
    return app.exec_()


if __name__ == "__main__":
    raise SystemExit(main())
