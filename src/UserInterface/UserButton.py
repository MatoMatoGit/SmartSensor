from upyiot.drivers.Switches.TactSwitch import TactSwitch
from micropython import const

class UserButton:

    REST_TIME_MS = const(500)
    HOLD_TIMES = (1500, 10000)

    CALLBACK_ARG_PRESS_COUNT = TactSwitch.CALLBACK_ARG_PRESS_COUNT
    CALLBACK_ARG_HOLD_INDEX = TactSwitch.CALLBACK_ARG_HOLD_INDEX

    CbPress = None
    CbRelease = None
    CbRest = None
    Context = None

    def __init__(self, btn_pin_nr, context=None, press_cb=None, release_cb=None):
        UserButton.CbPress = press_cb
        UserButton.CbRelease = release_cb
        UserButton.Context = context

        self.ButtonCbs = (self._ButtonPressed, self._ButtonReleased)
        self.Button = TactSwitch(btn_pin_nr, (0, -1), self.ButtonCbs,
                                 self.HOLD_TIMES, self.REST_TIME_MS)

        return

    def Enable(self):
        self.Button.Enable()

    def Disable(self):
        self.Button.Disable()

    @staticmethod
    def _ButtonPressed(args):
        press_count = args[TactSwitch.CALLBACK_ARG_PRESS_COUNT]
        print("[Btn] Pressed. N: {}".format(press_count))
        print("[Btn]: Press callback: {}".format(UserButton.CbPress))
        if UserButton.CbPress is not None:
            UserButton.CbPress(UserButton.Context, *args)
        return

    @staticmethod
    def _ButtonReleased(args):
        print("[Btn] Released.")
        hold_index = args[TactSwitch.CALLBACK_ARG_HOLD_INDEX]
        if hold_index >= 0:
            print("[Btn] Held for {}ms.".format(UserButton.HOLD_TIMES[hold_index]))
        if UserButton.CbRelease is not None:
            UserButton.CbRelease(UserButton.Context, *args)
        return
