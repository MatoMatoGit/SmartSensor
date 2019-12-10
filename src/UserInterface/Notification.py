from upyiot.middleware.SubjectObserver import Observer
from upyiot.drivers.Led.RgbLed import RgbLed
from upyiot.drivers.Led.Led import Led
from upyiot.system.Service.Service import Service
from micropython import const

MOIST_VALUE_MAX = const(800)
MOIST_VALUE_MIN = const(20)


class Notification:

    STATUS_UNSET    = const(0)
    STATUS_SET      = const(1)
    STATUS_ACTIVE   = const(2)

    def __init__(self, subject_obj, threshold, map_param, colors, prio):
        self.Status = Notification.STATUS_UNSET
        return


class Notifyer(Observer, Service):
    
    def __init__(self, rgbled_obj):
        super().__init__()
        self.MoistureLevel = 0
        self.RgbLed = rgbled_obj
        self.Notifications = set()
        self.ActiveNotification = None

    def SvcInit(self):
        return

    def SvcRun(self):
        self.RgbLed.Color(self._MapMoistureToRgb(
            self.Moisture.MoistureLevel))
        return

    def NotificationSet(self, notification):
        notification.Status = Notification.STATUS_SET
        if notification.Prio > self.ActiveNotification.Prio:
            self.ActiveNotification = notification
            # Active new notification

        return

    def NotificationRegister(self, notification):
        """

        :param subject_obj:
        :param map_param: Tuple containing the input's minimum and maximum value.
        :param colors: Tuple containing the color
        :param prio:
        :return:
        """
        self.Notifications.add(notification)
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

