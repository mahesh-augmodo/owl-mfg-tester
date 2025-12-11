import sys
# PyQt6 Import
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt

from ui_app.ui.window import HtfTestApp


def main(test_factory=None):
    # REMOVED: AA_EnableHighDpiScaling (Enabled by default in PyQt6)

    app = QApplication(sys.argv)

    font = QFont("Helvetica", 10)
    if not font.exactMatch():
        font = QFont("Arial", 10)

    # PyQt6 Change: StyleStrategy enum is fully qualified
    font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    app.setFont(font)

    test_func = test_factory

    window = HtfTestApp(
        window_title="OWL Manufacturing Tester",
        test_factory=test_func
    )

    window.show()
    # PyQt6 Change: use .exec() instead of .exec_()
    sys.exit(app.exec())
