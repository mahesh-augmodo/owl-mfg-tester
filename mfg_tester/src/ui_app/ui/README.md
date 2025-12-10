OpenHTF Manufacturing Test Runner (PyQt6)

A professional-grade, modular Graphical User Interface (GUI) for running OpenHTF manufacturing test sequences. Built with PyQt6, it features a responsive dashboard layout, integrated barcode scanning, and a clear separation between the User Interface and Test Logic.

1. Core Architecture

This application is built on the Model-View-Controller (MVC) design pattern. This ensures that long-running manufacturing tests do not freeze the User Interface.

Key Concepts

1. Asynchronous Execution (QThread)

The Problem: Manufacturing tests are "blocking" operations (e.g., waiting 5 seconds for a voltage reading). If ran on the Main Thread, the application window would freeze and become unresponsive (the "White Screen of Death").

The Solution: We run the OpenHTF test logic in a separate background thread (OpenHtfRunner), while the Main Thread handles only UI drawing and user interaction.

2. Thread-Safe Communication (Signals & Slots)

The Rule: In Qt, only the Main Thread is allowed to update the UI. A background thread trying to change a Label text directly will cause the application to crash.

The Mechanism: We use the Signal/Slot system. The background thread "emits" a signal (data), and the main thread "connects" that signal to a function (slot) that safely updates the UI.

3. The Interface Plug (GuiPlug)

To keep your test code clean, it does not know about PyQt.

It interacts with a generic GuiPlug (e.g., gui.prompt_user()).

The Plug handles the thread synchronization, pausing the test execution until the operator clicks a button in the GUI.

2. Project Structure

The codebase is organized to separate the generic runner logic from specific product test definitions.

mfg_tester/
│
├── main.py                # ENTRY POINT: Sets up HighDpi, Fonts, and launches the App.
│
├── core/                  # THE ENGINE (Generic Logic)
│   ├── signals.py         # Defines the Signal channels (Log, Result, Prompt).
│   ├── plug.py            # The OpenHTF Plug API used inside test phases.
│   └── runner.py          # The QThread that wraps the OpenHTF execution.
│
├── ui/                    # THE VIEW (GUI Layout & Style)
│   ├── window.py          # Layout logic (Widgets, Hiding/Showing elements).
│   └── styles.py          # CSS-like styling (Colors, Borders, Fonts).
│
└── tests/                 # THE MODEL (Test Definitions)
    └── product_a.py       # Specific test phases for Product A.


3. Installation & Usage

Prerequisites

Python 3.8+

PyQt6 (pip install PyQt6)

OpenHTF (pip install openhtf)

Running the Application

From the root directory:

python main.py


Operator Workflow

Scan Serial Number: The cursor defaults to the input box. Scanning a barcode (ending in Enter) automatically triggers the test start.

Follow Instructions: The central Blue box displays step-by-step instructions.

Operator Actions: If the test requires manual verification (e.g., "Is LED Green?"), the "Actions" panel will appear. The test blocks until an option is selected.

Result: The status indicator updates to PASS (Green) or FAIL (Red) upon completion.

4. Developer Guide

A. How to Add a New Test Sequence

You do not need to touch ui/ files to add new tests. Create a new file in tests/.

Template (tests/product_b.py):

import openhtf as htf
from core.plug import GuiPlug

@htf.plug(gui=GuiPlug)
def visual_inspection(test, gui):
    # Update the Instruction Box
    gui.update_instruction("Check: Is the case free of scratches?")
    
    # Prompt user (Returns the text of the button clicked)
    response = gui.prompt_user("Visual Check", choices=['Pass', 'Fail'])
    
    if response == 'Fail':
        test.logger.error("Visual inspection failed")

def get_test():
    """Factory function to return the Test object"""
    return htf.Test(visual_inspection)


Registering in main.py:

from tests.product_b import get_test
# ...
window = HtfTestApp(window_title="Product B Test", test_factory=get_test)


B. Styling the UI (ui/styles.py)

The app uses QSS (Qt Style Sheets), which functions almost exactly like CSS.

Global Font: Forced to Helvetica or Arial.

Colors:

Primary Blue: #007BFF

Success Green: #28A745

Danger Red: #DC3545

Integrated Input Group: The Serial Number input and Start Button use specific border-radius tricks to look like a single merged component. If you change the height (currently fixed at 50px), you must update it in both window.py (Geometry) and styles.py (Border Radius).

C. Layout Adjustments (ui/window.py)

The layout uses a 3-row system managed by QVBoxLayout and QHBoxLayout.

Header: Fixed Height.

Middle Section: Contains Instructions and Action Buttons.

Logs: Contains the scrolling log output.

Resizing: The vertical size ratio is controlled by layout.addWidget(widget, stretch=X).

Currently configured as 3:2 (Instructions vs Logs). Increase the Log stretch factor to make the console larger.

5. Troubleshooting

Issue

Cause

Solution

Console Warning: "Missing font family Consolas"

Running on macOS where Consolas is not installed.

The updated styles.py includes a font stack ("Menlo", "Consolas", "Courier New") to handle this.

Buttons look "floating" or misaligned

The layout engine is stretching widgets inconsistently.

Ensure setFixedSize or setFixedHeight is used on the Header elements in window.py.

App crashes immediately on start

GuiPlug might be missing or circular imports.

Ensure core.plug is imported in window.py and tests/product_a.py.

UI freezes during a test

The test logic is likely running on the Main Thread.

Ensure your test logic is inside the @htf.test definitions and executed via the OpenHtfRunner thread, not called directly from a button click.