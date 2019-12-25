from upyiot.middleware.SubjectObserver import Observer
from upyiot.drivers.Led.RgbLed import RgbLed
from upyiot.drivers.Led.Led import Led
from upyiot.system.Service.Service import Service
from micropython import const
import utime


class NotificationRange:

    def __init__(self, min, max):
        self.Min = min
        self.Max = max


class Notification(Observer):

    STATE_UNSET    = const(0)
    STATE_SET      = const(1)
    STATE_ACTIVE   = const(2)

    PRIO_MIN        = const(0)
    PRIO_MAX        = const(100)

    def __init__(self, val_threshold_range, color_map_params, prio, on_time_sec):
        """

        :param val_threshold_range: Range object with min and max threshold values.
        :param color_map_params: Dictionary containing a Range object as value for each
        RGB_COLOR_* key.
        :param prio: Notification priority. If multiple notifications are active, the highest
        priority is shown first.
        :param on_time_sec: Amount of time the LED is on for.
        """
        self.State = Notification.STATE_UNSET
        self.Value = 0
        self.ThresholdRange = val_threshold_range
        self.ColorMapParams = color_map_params
        self.Prio = prio
        self.OnTimeSec = on_time_sec

    def Update(self, arg):
        self.Value = arg
        if self.State is Notification.STATE_UNSET:
            if self.Value >= self.ThresholdRange.Min and \
            self.Value <= self.ThresholdRange.Max:
                self.State = self.STATE_SET
        else:
            if self.Value < self.ThresholdRange.Min or \
                    self.Value > self.ThresholdRange.Max:
                self.State = self.STATE_UNSET


class Notifyer(Service):
    
    def __init__(self, rgbled_obj):
        super().__init__()
        self.RgbLed = rgbled_obj
        self.Notifications = set()
        self.ActiveNotification = None

    def SvcInit(self):
        return

    def SvcRun(self):
        if self.ActiveNotification.State is Notification.STATE_UNSET:
            self.ActiveNotification.Prio = self.PRIO_MIN

        for notf in self.Notifications:
            if notf.State is Notification.STATE_SET:
                if notf.Prio > self.ActiveNotification.Prio:
                    self.ActiveNotification = notf

        self.ActiveNotification.State = Notification.STATE_ACTIVE
        if RgbLed.RGB_COLOR_RED in self.ActiveNotification.ColorMapParams.keys():
            red_val = Notifyer.MapValue(self.ActiveNotification.Value,
                                        self.ActiveNotification.ColorMapParams[RgbLed.RGB_COLOR_RED].Min,
                                        self.ActiveNotification.ColorMapParams[RgbLed.RGB_COLOR_RED].Max)
        else:
            red_val = 0

        if RgbLed.RGB_COLOR_GREEN in self.ActiveNotification.ColorMapParams.keys():
            green_val = Notifyer.MapValue(self.ActiveNotification.Value,
                                          self.ActiveNotification.ColorMapParams[RgbLed.RGB_COLOR_GREEN].Min,
                                          self.ActiveNotification.ColorMapParams[RgbLed.RGB_COLOR_GREEN].Max)
        else:
            green_val = 0

        if RgbLed.RGB_COLOR_BLUE in self.ActiveNotification.ColorMapParams.keys():
            blue_val = Notifyer.MapValue(self.ActiveNotification.Value,
                                         self.ActiveNotification.ColorMapParams[RgbLed.RGB_COLOR_BLUE].Min,
                                         self.ActiveNotification.ColorMapParams[RgbLed.RGB_COLOR_BLUE].Max)
        else:
            blue_val = 0

        self.RgbLed.ColorsSet(red_val, green_val, blue_val)
        utime.sleep(self.ActiveNotification.OnTimeSec)
        self.RgbLed.Off()

    def NotificationSet(self, notification):
        notification.Status = Notification.STATUS_SET
        if notification.Prio > self.ActiveNotification.Prio:
            self.ActiveNotification = notification
            # Active new notification

        return

    def NotificationRegister(self, notification):
        self.Notifications.add(notification)
        return

    @staticmethod
    def MapValue(value, in_min, in_max, out_min=Led.PWM_DUTY_MIN, out_max=Led.PWM_DUTY_MAX):
        return out_min + (out_max - out_min) * ((value - in_min) / (in_max - in_min))

