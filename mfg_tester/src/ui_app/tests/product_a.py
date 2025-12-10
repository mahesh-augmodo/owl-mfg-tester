import time
import openhtf as htf
from ui_app.core.plug import GuiPlug


@htf.plug(gui=GuiPlug)
@htf.measures(htf.Measurement('visual_check').equals('Yes'))
def cable_connection_phase(test, gui):
    gui.update_instruction(
        "STEP 1: CONNECTION CHECK\n\n"
        "1. Connect USB Cable.\n"
        "2. Ensure Power Supply is ON."
    )
    gui.prompt_user("Connections Ready?", choices=['OK'])

    gui.update_instruction("STEP 2: LED INSPECTION\nLook at the Status LED.")
    result = gui.prompt_user("Is the LED Green?", choices=['Yes', 'No'])
    test.measurements.visual_check = result


@htf.plug(gui=GuiPlug)
def automated_phase(test, gui):
    gui.update_instruction("Running Automated Tests...\nDO NOT TOUCH.")
    test.logger.info("Initializing sensors...")
    time.sleep(1.0)
    test.logger.info("Verifying voltage rails...")
    time.sleep(1.0)


def get_test():
    """Factory function required by the Runner."""
    return htf.Test(cable_connection_phase, automated_phase)
