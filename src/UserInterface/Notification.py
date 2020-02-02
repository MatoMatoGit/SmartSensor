from upyiot.middleware.SubjectObserver.SubjectObserver import Observer
from upyiot.drivers.Led.RgbLed import RgbLed
from upyiot.drivers.Led.Led import Led
from upyiot.system.Service.Service import Service
from micropython import const
import utime


class NotifiyerService(Service):
    SENSOR_SERVICE_MODE = Service.MODE_RUN_PERIODIC

    def __init__(self):
        super().__init__("Notif", self.SENSOR_SERVICE_MODE, {})


class NotificationRange:

    def __init__(self, min, max):
        self.Min = min
        self.Max = max


class Notification(Observer):

    PRIO_MIN        = const(0)
    PRIO_MAX        = const(100)

    def __init__(self, val_threshold_range, color_map_params, prio, on_time_sec):
        """

        :param val_threshold_range: Range object with min and max threshold values.
        :param color_map_params: Dictionary containing a Range object value for each
        RGB_COLOR_* key.
        :param prio: Notification priority. If multiple notifications are active, the highest
        priority is shown first.
        :param on_time_sec: Amount of time the LED is on for.
        """
        self.Value = 0
        self.ThresholdRange = val_threshold_range
        self.ColorMapParams = color_map_params
        self.Prio = prio
        self.OnTimeSec = on_time_sec
        self.Active = False

    def Update(self, arg):
        self.Value = arg
        if self.Value >= self.ThresholdRange.Min and \
        self.Value <= self.ThresholdRange.Max:
            self.Active = True
        elif self.Value < self.ThresholdRange.Min or \
        self.Value > self.ThresholdRange.Max:
            self.Active = False


class Notifyer(NotifiyerService):

    DELAY_BETWEEN_NOTIFS_MSEC = const(500)

    def __init__(self, rgbled_obj):
        super().__init__()
        self.RgbLed = rgbled_obj
        self.Notifications = set()
        self.ActiveNotifications = list()

    def SvcInit(self):
        return

    def SvcRun(self):

        # Add activated notifications to the ActiveNotifications list if it is
        # not in that list.
        for notif in self.Notifications:
            if notif.Active is True and notif not in self.ActiveNotifications:
                self.ActiveNotifications.append(notif)

        # Remove de-activated notifications from the ActiveNotifications list.
        for notif in self.ActiveNotifications:
            if notif.Active is False:
                self.ActiveNotifications.remove(notif)

        # Sort the list on priority.
        sorted(self.ActiveNotifications, key=lambda notif: notif.Prio)

        # Loop through the list once and show all notifications.
        for notif in self.ActiveNotifications:

            # Map the notification to color values.
            red_val, green_val, blue_val = self._MapColorValues(notif)

            # Set the colors of the LED.
            self.RgbLed.ColorsSet(red_val, green_val, blue_val)

            # Sleep while the LED is on.
            utime.sleep(notif.OnTimeSec)

            # Turn the LED off.
            self.RgbLed.Off()

            utime.sleep_ms(self.DELAY_BETWEEN_NOTIFS_MSEC)

    def NotificationSet(self, notification):
        notification.Active = True
        return

    def NotificationRegister(self, notification):
        self.Notifications.add(notification)
        return

    def _MapColorValues(self, notif):
        # If a color mapping param red exists, map the value to the color intensity.
        if RgbLed.RGB_COLOR_RED in notif.ColorMapParams.keys():
            red_val = Notifyer._CheckIfStaticValue(notif, RgbLed.RGB_COLOR_RED)
            if red_val is -1:
                red_val = Notifyer.MapValue(notif.Value,
                                            notif.ColorMapParams[RgbLed.RGB_COLOR_RED].Min,
                                            notif.ColorMapParams[RgbLed.RGB_COLOR_RED].Max)
        else:
            red_val = 0

        # If a color mapping param for green exists, map the value to the color intensity.
        if RgbLed.RGB_COLOR_GREEN in notif.ColorMapParams.keys():
            green_val = Notifyer._CheckIfStaticValue(notif, RgbLed.RGB_COLOR_GREEN)
            if green_val is -1:
                green_val = Notifyer.MapValue(notif.Value,
                                              notif.ColorMapParams[RgbLed.RGB_COLOR_GREEN].Min,
                                              notif.ColorMapParams[RgbLed.RGB_COLOR_GREEN].Max)
        else:
            green_val = 0

        # If a color mapping param blue exists, map the value to the color intensity.
        if RgbLed.RGB_COLOR_BLUE in notif.ColorMapParams.keys():
            blue_val = Notifyer._CheckIfStaticValue(notif, RgbLed.RGB_COLOR_BLUE)
            if blue_val is -1:
                blue_val = Notifyer.MapValue(notif.Value,
                                             notif.ColorMapParams[RgbLed.RGB_COLOR_BLUE].Min,
                                             notif.ColorMapParams[RgbLed.RGB_COLOR_BLUE].Max)
        else:
            blue_val = 0

        return red_val, green_val, blue_val

    @staticmethod
    def MapValue(value, in_min, in_max, out_min=Led.PWM_DUTY_MIN, out_max=Led.PWM_DUTY_MAX):
        return int(out_min + (out_max - out_min) * ((value - in_min) / (in_max - in_min)))


    @staticmethod
    def _CheckIfStaticValue(notif, color):
        if notif.ColorMapParams[color].Min is notif.ColorMapParams[color].Max:
            return notif.ColorMapParams[color].Max

        return -1
