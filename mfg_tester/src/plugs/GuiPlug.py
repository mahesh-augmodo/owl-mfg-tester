from threading import Event
import asyncio
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

    async def async_prompt_user(self, question, choices=['OK']):
        if self.signals is None:
            return choices[0]

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            print("Error: asyncio event loop not running. Cannot create future.")
            return choices[0]

        GuiPlug.active_future = loop.create_future()

        self.signals.prompt.emit(question, choices)
        print("Prompt signal emitted. Awaiting user response...")

        user_response = await GuiPlug.active_future
        GuiPlug.active_future = None

        return user_response

    @classmethod
    def set_user_response(cls, answer):
        cls.response = answer
        cls.event.set()
