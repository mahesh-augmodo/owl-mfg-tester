import logging
from PyQt6.QtCore import QThread
from plugs.GuiPlug import GuiPlug
import openhtf as htf


class OpenHtfRunner(QThread):
    def __init__(self, serial_number, test_factory, signals):
        super().__init__()
        self.serial_number = serial_number
        self.test_factory = test_factory  # Function that returns the htf.Test object
        self.signals = signals

    def run(self):
        # Link the static plug to the instance signals
        GuiPlug.signals = self.signals

        # Setup Logging
        htf_logger = logging.getLogger('openhtf')
        self._setup_logging(htf_logger)

        try:
            # Build the specific test provided by main.py
            test = self.test_factory()
            result = test.execute(test_start=lambda: self.serial_number)
            self.signals.result.emit(result)
        except Exception as e:
            htf_logger.error(f"Test Execution Error: {e}")
            self.signals.result.emit(False)

    def _setup_logging(self, logger):
        """Redirects OpenHTF logs to the GUI signal."""
        class SignalHandler(logging.Handler):
            def __init__(self, sig):
                super().__init__()
                self.sig = sig

            def emit(self, record):
                self.sig.log.emit(self.format(record), record.levelno)

        # Avoid adding duplicate handlers if restarted
        logger.handlers = []
        handler = SignalHandler(self.signals)
        handler.setFormatter(
            logging.Formatter(
                '%(asctime)s - %(message)s',
                datefmt='%H:%M:%S'))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
