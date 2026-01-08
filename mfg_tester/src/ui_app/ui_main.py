import sys
# PyQt6 Import
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont, QIcon, QFontDatabase
from PyQt6.QtCore import Qt

from ui_app.ui.window import HtfTestApp
from utils.bundle_utils import get_resource_path


def main(test_factory=None):
    # REMOVED: AA_EnableHighDpiScaling (Enabled by default in PyQt6)

    app = QApplication(sys.argv)
    QFontDatabase.addApplicationFont(
        get_resource_path("resources/fonts/NotoSansSC.ttf"))
    font = QFont("NotoSansSC", 10)
    if not font.exactMatch():
        font = QFont("Arial", 10)

    font.setStyleStrategy(QFont.StyleStrategy.PreferQuality)
    app.setFont(font)
    app.setWindowIcon(QIcon(get_resource_path("resources/OwlCheckIcon.png")))

    test_func = test_factory

    window = HtfTestApp(
        window_title="OWL Manufacturing Tester",
        test_factory=test_func
    )

    window.show()
    # PyQt6 Change: use .exec() instead of .exec_()
    sys.exit(app.exec())
