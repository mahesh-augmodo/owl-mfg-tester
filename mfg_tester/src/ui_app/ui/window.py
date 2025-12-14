import sys
import logging
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLineEdit,
    QPushButton, QLabel, QTextEdit, QGroupBox, QFrame
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QIcon

from ui_app.core.signals import TestSignals
from ui_app.core.runner import OpenHtfRunner
from plugs.GuiPlug import GuiPlug
from ui_app.ui.styles import STYLESHEET


class HtfTestApp(QWidget):
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

        # 1. SN Input Column
        input_col = QWidget()
        input_v = QVBoxLayout(input_col)
        input_v.setContentsMargins(0, 0, 0, 0)

        self.input_wrapper = QFrame()
        self.input_wrapper.setObjectName("InputWrapper")
        self.input_wrapper.setFixedSize(600, 50)

        iw_layout = QHBoxLayout(self.input_wrapper)
        iw_layout.setContentsMargins(0, 0, 0, 0)
        iw_layout.setSpacing(0)

        self.sn_input = QLineEdit()
        self.sn_input.setPlaceholderText("Scan Serial Number...")
        self.sn_input.setFixedHeight(50)
        self.sn_input.setTextMargins(15, 0, 0, 0)
        self.sn_input.returnPressed.connect(self.start_test)

        self.btn_start = QPushButton("START TEST")
        self.btn_start.setObjectName("StartButton")
        # PyQt6 Change: Full Enum Path for Cursor
        self.btn_start.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_start.setFixedSize(150, 50)
        self.btn_start.clicked.connect(self.start_test)

        iw_layout.addWidget(self.sn_input)
        iw_layout.addWidget(self.btn_start)

        input_v.addWidget(QLabel("SERIAL NUMBER", objectName="LabelMeta"))
        input_v.addWidget(self.input_wrapper)

        # 2. Result Column
        res_col = QWidget()
        res_v = QVBoxLayout(res_col)
        res_v.setContentsMargins(0, 0, 0, 0)

        self.lbl_result = QLabel("READY", objectName="ResultLabel")
        # PyQt6 Change: Full Enum Path for Alignment
        self.lbl_result.setAlignment(Qt.AlignmentFlag.AlignCenter)

        res_v.addWidget(self.lbl_result)

        header.addWidget(input_col, stretch=6)
        header.addWidget(res_col, stretch=4)
        main_layout.addLayout(header)

        # --- MIDDLE SECTION ---
        middle = QHBoxLayout()

        # 1. Instructions Column
        inst_col = QWidget()
        inst_v = QVBoxLayout(inst_col)
        inst_v.setContentsMargins(0, 0, 0, 0)

        inst_v.addWidget(
            QLabel(
                "OPERATOR INSTRUCTIONS",
                objectName="LabelMeta"))

        grp_inst = QGroupBox()
        inst_lay = QVBoxLayout()
        inst_lay.setContentsMargins(1, 1, 1, 1)
        self.txt_inst = QTextEdit()
        self.txt_inst.setReadOnly(True)
        self.txt_inst.setText("Waiting for Unit...")
        inst_lay.addWidget(self.txt_inst)
        grp_inst.setLayout(inst_lay)
        inst_v.addWidget(grp_inst)

        middle.addWidget(inst_col, stretch=3)

        # 2. Actions Column
        self.action_container = QWidget()
        act_v = QVBoxLayout(self.action_container)
        act_v.setContentsMargins(0, 0, 0, 0)

        act_v.addWidget(QLabel("ACTIONS", objectName="LabelMeta"))

        self.grp_feedback = QGroupBox()
        self.grp_feedback.setObjectName("ActionGroup")
        fb_lay = QVBoxLayout()
        self.lbl_question = QLabel("...", objectName="QuestionLabel")
        # PyQt6 Change: Full Enum Path
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

        # --- LOGS SECTION ---
        main_layout.addWidget(QLabel("TEST LOGS", objectName="LabelMeta"))

        grp_logs = QGroupBox()
        l_lay = QVBoxLayout()
        l_lay.setContentsMargins(1, 1, 1, 1)
        self.txt_logs = QTextEdit()
        self.txt_logs.setReadOnly(True)
        self.txt_logs.setObjectName("LogText")
        # PyQt6 Change: Full Enum Path for LineWrapMode
        self.txt_logs.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        l_lay.addWidget(self.txt_logs)
        grp_logs.setLayout(l_lay)

        main_layout.addWidget(grp_logs, stretch=2)

    # --- Logic (Same as before) ---
    def start_test(self):
        sn = self.sn_input.text().strip()
        if not sn:
            return self.sn_input.setFocus()

        self.txt_logs.clear()
        self.txt_inst.setText("Initializing...")
        self.lbl_result.setText("RUNNING")
        self.lbl_result.setStyleSheet(
            "#ResultLabel { background-color: #007BFF; color: white; border: none; }")
        self.action_container.setVisible(False)
        self.sn_input.setEnabled(False)
        self.btn_start.setEnabled(False)

        self.runner = OpenHtfRunner(sn, self.test_factory, self.signals)
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
            # PyQt6 Change: Full Enum Path
            btn.setCursor(Qt.CursorShape.PointingHandCursor)

            color = "#6C757D"
            if c.lower() in ['yes', 'pass', 'ok', '是', 'green', '绿色的']:
                color = "#28A745"
            elif c.lower() in ['no', 'fail', '否', 'red', '红色的']:
                color = "#DC3545"
            elif c.lower() in ['blue', '蓝色的']:
                color = "#237CD5"

            btn.setStyleSheet(
                f"background-color: {color}; color: white; border-radius: 6px; font-weight: bold; font-size: 18px;")
            btn.clicked.connect(lambda _, x=c: self.handle_input(x))
            self.btn_layout.addWidget(btn)

    def handle_input(self, choice):
        self.action_container.setVisible(False)
        GuiPlug.set_user_response(choice)

    def show_instruction(self, text):
        formatted_text = text.replace("\n", "<br>")
        html_content = f"""<div style="line-height: 150%;">{formatted_text}</div>"""
        self.txt_inst.setHtml(html_content)

    def append_log(self, msg, level):
        color = "#DC3545" if level >= logging.ERROR else "#212529"
        self.txt_logs.append(
            f'<div style="line-height: 150%; color:{color}">{msg}</div>')
        self.txt_logs.verticalScrollBar().setValue(
            self.txt_logs.verticalScrollBar().maximum())

    def show_result(self, passed):
        if passed:
            self.lbl_result.setText("PASS")
            self.lbl_result.setStyleSheet(
                "#ResultLabel { background-color: #28A745; color: white; border: none; }")
            self.txt_inst.setText("TEST PASSED.\nRemove Unit.")
        else:
            self.lbl_result.setText("FAIL")
            self.lbl_result.setStyleSheet(
                "#ResultLabel { background-color: #DC3545; color: white; border: none; }")
            self.txt_inst.setText("TEST FAILED.\nSegregate Unit.")

        self.sn_input.setEnabled(True)
        self.sn_input.clear()
        self.sn_input.setFocus()
        self.btn_start.setEnabled(True)
