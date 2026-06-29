#!/usr/bin/env python3
"""Launch the Wave Aligner GUI."""

import sys

from PyQt5.QtWidgets import QApplication

from wavealigner.app import WaveAlignerWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Wave Aligner")
    window = WaveAlignerWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
