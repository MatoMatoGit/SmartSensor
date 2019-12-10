from upyiot.drivers.Switches.TactSwitch import TactSwitch
from machine import Timer
from micropython import const

class UserButton:

    REST_TIME_MS = const(500)

    def __init__(self, btn_pin_nr):
        self.ButtonCbs = (self._ButtonPressed, self._ButtonReleased, self._ButtonHold)
        self.Button = TactSwitch(btn_pin_nr, self.ButtonCbs, 2000, True)
        self.RestTimer = Timer(-1)
        self.PressCount = 0
        return

    def _ButtonPressed(self, cb_type):
        self.RestTimer.init(period=UserButton.REST_TIME_MS,
                            mode=Timer.ONE_SHOT,
                            callback=UserButton._ButtonRest)
        return

    def _ButtonReleased(self, cb_type):
        self.RestTimer.deinit()
        self.PressCount += 1
        return

    @staticmethod
    def _ButtonHold(cb_type):

        return

    @staticmethod
    def _ButtonRest():
        UserButton.PressCount = 0
        return