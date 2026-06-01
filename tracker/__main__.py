from __future__ import annotations

import sys

from PyQt5.QtWidgets import QApplication

from tracker.app.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Tracker")
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
