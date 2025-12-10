STYLESHEET = """
    /* GLOBAL FONT & COLOR */
    QWidget {
        background-color: #F4F6F9;
        color: #333;
        font-family: "Helvetica", "Arial", sans-serif;
    }

    /* THE MASTER LABEL STYLE */
    #LabelMeta {
        font-size: 12px;
        font-weight: bold;
        color: #6C757D;
        margin-left: 2px;
        margin-bottom: 2px; /* Reduced spacing slightly */
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    /* --- INTEGRATED INPUT GROUP --- */
    #InputWrapper {
        background-color: white;
        border: 1px solid #007BFF; /* REDUCED: 2px -> 1px */
        border-radius: 6px;
    }
    QLineEdit {
        border: none; background: transparent;
        font-size: 18px; color: #333;
    }
    #StartButton {
        background-color: #007BFF; color: white; border: none;
        border-top-right-radius: 5px; border-bottom-right-radius: 5px;
        font-weight: bold; font-size: 15px;
    }
    #StartButton:hover { background-color: #0056b3; }
    #StartButton:pressed { background-color: #004494; }
    #StartButton:disabled { background-color: #BDC3C7; }
    /* --- END INPUT GROUP --- */

    /* Result Box */
    #ResultLabel {
        background-color: #E9ECEF;
        color: #ADB5BD;
        border-radius: 6px;
        font-size: 40px;
        font-weight: 900;
        border: 1px solid #DEE2E6; /* REDUCED: 2px -> 1px */
    }

    /* Group Boxes */
    QGroupBox {
        border: 1px solid #CED4DA; /* Kept at 1px (Standard) */
        border-radius: 6px;
        background-color: white;
        margin-top: 0px;
    }

    /* Instructions */
    QTextEdit { border: none; }
    QTextEdit[readOnly="true"] {
        font-size: 22px; color: #212529; padding: 20px; line-height: 140%;
    }

    /* Action Area */
    #ActionGroup {
        border: 1px solid #FFC107; /* REDUCED: 2px -> 1px */
        background-color: #FFF9DB;
    }
    #QuestionLabel { font-size: 20px; font-weight: bold; color: #D35400; margin-bottom: 15px; }

    /* Logs */
    #LogText {
        font-family: "Menlo", "Consolas", "Courier New", monospace;
        font-size: 13px; color: #343A40;
        background-color: #F8F9FA; border: none; padding: 10px;
    }
"""
