from threading import Event
try:
    from openhtf.plugs import BasePlug
except ImportError:
    class BasePlug:
        pass


class GuiPlug(BasePlug):
    """
    Import this plug into your test files to control the UI.
    """
    signals = None
    response = None
    event = Event()

    def update_instruction(self, text):
        if self.signals:
            self.signals.instruction.emit(text)

    def prompt_user(self, question, choices=['OK']):
        if self.signals:
            self.signals.prompt.emit(question, choices)
            GuiPlug.event.clear()
            GuiPlug.event.wait()
            return GuiPlug.response
        return choices[0]

    @classmethod
    def set_user_response(cls, answer):
        cls.response = answer
        cls.event.set()
