from upyiot.drivers.Switches.TactSwitch import TactSwitch
from machine import Timer
from micropython import const

class UserButton:

    REST_TIME_MS = const(500)
    HOLD_TIMES = (1000, 5000, 10000)

    def __init__(self, btn_pin_nr):
        self.ButtonCbs = (self._ButtonPressed, self._ButtonReleased, self._ButtonRest)
        self.Button = TactSwitch(btn_pin_nr, (0, -1), self.ButtonCbs,
                                 self.HOLD_TIMES, self.REST_TIME_MS)
        return

    @staticmethod
    def _ButtonPressed(press_count):
        return

    @staticmethod
    def _ButtonReleased(hold_idx):
        return

    @staticmethod
    def _ButtonRest(press_count):
        return
