from upyiot.middleware.SubjectObserver import Observer
from upyiot.drivers.Led.RgbLed import RgbLed
from upyiot.drivers.Led.Led import Led
from upyiot.system.Service.Service import Service
from micropython import const

MOIST_VALUE_MAX = const(800)
MOIST_VALUE_MIN = const(20)


class Notifyer(Observer, Service):
    
    def __init__(self, rgbled_obj):
        super().__init__()
        self.MoistureLevel = 0
        self.RgbLed = rgbled_obj

    def SvcInit(self):
        return

    def SvcRun(self):
        self.RgbLed.Color(self._MapMoistureToRgb(
            self.Moisture.MoistureLevel))
        return

    def NotificationSet(self, notification):
        return

    def NotificationRegister(self, subject_obj, map_param, prio):
        return

    def Update(self, arg):
        self.MoistureLevel = arg

    def NotifyLowBattery(self):
        return 0

    @staticmethod
    def _MapMoistureToRgb(moisture):
        red_val = Notifyer.MapValue(moisture,
                                    MOIST_VALUE_MIN,
                                    MOIST_VALUE_MAX,
                                    Led.PWM_DUTY_MAX,
                                    Led.PWM_DUTY_MIN)
        blue_val = Notifyer.MapValue(moisture,
                                     MOIST_VALUE_MIN,
                                     MOIST_VALUE_MAX,
                                     Led.PWM_DUTY_MIN,
                                     Led.PWM_DUTY_MAX)

        green_val = 0
        return red_val, green_val, blue_val

    @staticmethod
    def MapValue(value, in_min, in_max, out_min, out_max):
        return out_min + (out_max - out_min) * ((value - in_min) / (in_max - in_min))

