"""Entry point: python -m tracker"""

import sys

from PyQt5.QtWidgets import QApplication

from tracker.app.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Tracker")
    window = MainWindow()
    window.show()
    return app.exec_()


if __name__ == "__main__":
    raise SystemExit(main())
