from upyiot.drivers.Switches.TactSwitch import TactSwitch


class UserButton:

    def __init__(self, btn_pin_nr):
        self.ButtonCbs = (self._ButtonPressed, self._ButtonReleased, self._ButtonHold)
        self.Button = TactSwitch(btn_pin_nr, self.ButtonCbs, 2000, True)

        return

    @staticmethod
    def _ButtonPressed(cb_type):
        return

    @staticmethod
    def _ButtonReleased(cb_type):
        return

    @staticmethod
    def _ButtonHold(cb_type):
        return

