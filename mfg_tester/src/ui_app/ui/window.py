import sys
import logging
import os
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QTextEdit, QGroupBox, QFrame
)
from PyQt6.QtCore import Qt, QUrl, QSize
# NEW: Added QGuiApplication for font check
from PyQt6.QtGui import QFont, QIcon, QDesktopServices, QGuiApplication
from PyQt6.QtWidgets import QStyle  # NEW: QStyle import for standard icons

from ui_app.core.signals import TestSignals
from ui_app.core.runner import OpenHtfRunner
from plugs.GuiPlug import GuiPlug
from ui_app.ui.styles import STYLESHEET
from utils.i18n import _
from utils.bundle_utils import get_config_path

# --- UTILITY FUNCTION (Unchanged) ---


def open_file_in_default_editor(file_path):
    """
    Opens the specified file using the system's default application.
    """
    if not os.path.exists(file_path):
        print(f"Error: File not found at {file_path}")
        return False

    url = QUrl.fromLocalFile(os.path.abspath(file_path))
    success = QDesktopServices.openUrl(url)

    if not success:
        print(f"Warning: Could not launch default editor for {file_path}")

    return success
# ----------------------------------------


class HtfTestApp(QWidget):
    # NEW CONSTANT: Defines the target fixed height for header elements (50 *
    # 1.5 = 75)
    HEADER_HEIGHT = 75

    # NEW CONSTANT: Defines the font size for the result label (Original was
    # implicit, let's target something large)
    RESULT_FONT_SIZE = 36  # Adjust this value if 36 is too large or small

    def __init__(self, window_title, test_factory):
        super().__init__()
        self.setWindowTitle(window_title)
        self.test_factory = test_factory

        self.signals = TestSignals()
        self.signals.log.connect(self.append_log)
        self.signals.prompt.connect(self.show_prompt)
        self.signals.instruction.connect(self.show_instruction)
        self.signals.result.connect(self.show_result)

        self.setup_ui()
        self.resize_to_screen_percentage()
        self.setStyleSheet(STYLESHEET)

    def resize_to_screen_percentage(self):
        screen = QApplication.primaryScreen().availableGeometry()
        width = int(screen.width() * 0.75)
        height = int(screen.height() * 0.90)
        self.setGeometry(
            int((screen.width() - width) / 2),
            int((screen.height() - height) / 2),
            width, height
        )

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(30, 30, 30, 30)

        # --- HEADER ---
        header = QHBoxLayout()

        # 1. Start Button
        self.btn_start = QPushButton(_("START TEST"))
        self.btn_start.setObjectName("StartButton")
        self.btn_start.setCursor(Qt.CursorShape.PointingHandCursor)
        # <<< CHANGE 1: Increase fixed height by 50% >>>
        self.btn_start.setFixedSize(150, self.HEADER_HEIGHT)
        self.btn_start.clicked.connect(self.start_test)
        header.addWidget(self.btn_start)

        # 2. Add some stretch
        header.addStretch(1)

        # 3. Result Column
        res_col = QWidget()
        res_v = QVBoxLayout(res_col)
        res_v.setContentsMargins(0, 0, 0, 0)
        self.lbl_result = QLabel(_("READY"), objectName="ResultLabel")
        self.lbl_result.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # <<< CHANGE 2: Increase font size for better visibility in the larger header >>>
        font = QFont(QGuiApplication.font())
        font.setPointSize(self.RESULT_FONT_SIZE)
        self.lbl_result.setFont(font)

        # <<< CHANGE 3: Enforce minimum height for the result label >>>
        self.lbl_result.setMinimumHeight(self.HEADER_HEIGHT)

        res_v.addWidget(self.lbl_result)
        header.addWidget(res_col, stretch=4)

        # 4. Settings Button
        self.btn_settings = QPushButton()
        self.btn_settings.setObjectName("SettingsButton")
        # <<< CHANGE 4: Increase fixed size by 50% >>>
        self.btn_settings.setFixedSize(self.HEADER_HEIGHT, self.HEADER_HEIGHT)
        self.btn_settings.setCursor(Qt.CursorShape.PointingHandCursor)

        # Use a larger icon size for the larger button
        icon_size = self.HEADER_HEIGHT - 10  # 65x65 icon for a 75x75 button

        # Try to use a standard settings icon
        settings_icon = QIcon.fromTheme("preferences-system")
        if settings_icon.isNull():
            # Fallback to a predefined stock icon if theme icons are missing
            settingsettings_icon = self.style().standardIcon(
                QStyle.StandardPixmap.SP_DialogResetButton
            )

        self.btn_settings.setIcon(settings_icon)
        # <<< CHANGE 5: Set larger icon size >>>
        self.btn_settings.setIconSize(
            QSize(200, 200)  # QSize import would be needed, or just rely on CSS
        )
        self.btn_settings.setText(_("⚙️"))  # Fallback text/emoji if icon fails

        self.btn_settings.clicked.connect(self.open_settings_file)
        header.addWidget(self.btn_settings)

        main_layout.addLayout(header)

        # --- MIDDLE SECTION (Unchanged) ---
        middle = QHBoxLayout()

        # 1. Instructions Column
        inst_col = QWidget()
        inst_v = QVBoxLayout(inst_col)
        inst_v.setContentsMargins(0, 0, 0, 0)
        inst_v.addWidget(
            QLabel(_("OPERATOR INSTRUCTIONS"), objectName="LabelMeta")
        )
        grp_inst = QGroupBox()
        inst_lay = QVBoxLayout()
        inst_lay.setContentsMargins(1, 1, 1, 1)
        self.txt_inst = QTextEdit()
        self.txt_inst.setReadOnly(True)
        self.txt_inst.setText(_("Waiting for Unit..."))
        inst_lay.addWidget(self.txt_inst)
        grp_inst.setLayout(inst_lay)
        inst_v.addWidget(grp_inst)
        middle.addWidget(inst_col, stretch=3)

        # 2. Actions Column
        self.action_container = QWidget()
        act_v = QVBoxLayout(self.action_container)
        act_v.setContentsMargins(0, 0, 0, 0)
        act_v.addWidget(QLabel(_("ACTIONS"), objectName="LabelMeta"))
        self.grp_feedback = QGroupBox()
        self.grp_feedback.setObjectName("ActionGroup")
        fb_lay = QVBoxLayout()
        self.lbl_question = QLabel(_("..."), objectName="QuestionLabel")
        self.lbl_question.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_question.setWordWrap(True)
        self.btn_container = QWidget()
        self.btn_layout = QVBoxLayout(self.btn_container)
        self.btn_layout.setSpacing(10)
        fb_lay.addWidget(self.lbl_question)
        fb_lay.addWidget(self.btn_container)
        fb_lay.addStretch()
        self.grp_feedback.setLayout(fb_lay)
        act_v.addWidget(self.grp_feedback)
        self.action_container.setVisible(False)
        middle.addWidget(self.action_container, stretch=2)
        main_layout.addLayout(middle, stretch=3)

        # --- LOGS SECTION (Unchanged) ---
        main_layout.addWidget(QLabel(_("TEST LOGS"), objectName="LabelMeta"))
        grp_logs = QGroupBox()
        l_lay = QVBoxLayout()
        l_lay.setContentsMargins(1, 1, 1, 1)
        self.txt_logs = QTextEdit()
        self.txt_logs.setReadOnly(True)
        self.txt_logs.setObjectName("LogText")
        self.txt_logs.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        l_lay.addWidget(self.txt_logs)
        grp_logs.setLayout(l_lay)
        main_layout.addWidget(grp_logs, stretch=2)

    # --- Logic (Unchanged for this request) ---
    def open_settings_file(self):
        """
        Launches the default system editor for the station.yaml configuration file.
        """
        config_path = get_config_path()
        open_file_in_default_editor(config_path)

    def start_test(self):
        self.txt_logs.clear()
        self.txt_inst.setText(_("Initializing..."))
        self.lbl_result.setText(_("RUNNING"))
        self.lbl_result.setStyleSheet(
            "#ResultLabel { background-color: #007BFF; color: white; border: none; }")
        self.action_container.setVisible(False)
        self.btn_start.setEnabled(False)

        self.runner = OpenHtfRunner(self.test_factory, self.signals)
        self.runner.start()

    def show_prompt(self, question, choices):
        self.lbl_question.setText(question)
        self.action_container.setVisible(True)

        for i in reversed(range(self.btn_layout.count())):
            w = self.btn_layout.itemAt(i).widget()
            if w:
                w.setParent(None)

        for c in choices:
            btn = QPushButton(c)
            btn.setMinimumHeight(50)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)

            color = "#6C757D"
            if c.lower() in ['yes', 'pass', 'ok', '是', 'green', '绿色的']:
                color = "#28A745"
            elif c.lower() in ['no', 'fail', '否', 'red', '红色的']:
                color = "#DC3545"
            elif c.lower() in ['blue', '蓝色的']:
                color = "#1D81E4"

            btn.setStyleSheet(
                f"background-color: {color}; color: white; border-radius: 6px; font-weight: bold; font-size: 18px;")
            btn.clicked.connect(lambda _, x=c: self.handle_input(x))
            self.btn_layout.addWidget(btn)

    def handle_input(self, choice):
        self.action_container.setVisible(False)
        GuiPlug.set_user_response(choice)

    def show_instruction(self, text):
        formatted_text = text.replace("\n", "<br>")
        html_content = f"<div style=\"line-height: 150%;\">{formatted_text}</div>"
        self.txt_inst.setHtml(html_content)

    def append_log(self, msg, level):
        color = "#DC3545" if level >= logging.ERROR else "#212529"
        self.txt_logs.append(
            f'<div style=\"line-height: 150%; color:{color}\">{msg}</div>')
        self.txt_logs.verticalScrollBar().setValue(
            self.txt_logs.verticalScrollBar().maximum())

    def show_result(self, passed):
        if passed:
            self.lbl_result.setText(_("PASS"))
            self.lbl_result.setStyleSheet(
                "#ResultLabel { background-color: #28A745; color: white; border: none; }")
            self.txt_inst.setText(_("TEST PASSED.\nRemove Unit."))
        else:
            self.lbl_result.setText(_("FAIL"))
            self.lbl_result.setStyleSheet(
                "#ResultLabel { background-color: #DC3545; color: white; border: none; }")
            self.txt_inst.setText(_("TEST FAILED.\nSegregate Unit."))

        self.btn_start.setEnabled(True)
