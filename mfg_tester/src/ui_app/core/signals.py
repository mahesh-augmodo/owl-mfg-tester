from PyQt6.QtCore import QObject, pyqtSignal


class TestSignals(QObject):
    log = pyqtSignal(str, int)          # Message, Level
    result = pyqtSignal(bool)           # Pass/Fail
    prompt = pyqtSignal(str, list)      # Question, Choices
    instruction = pyqtSignal(str)       # Instruction Text
