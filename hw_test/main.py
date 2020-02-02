from machine import Pin
import time
from upyiot.drivers.Sensors.CapMoisture import CapMoisture
from upyiot.drivers.Sensors.Mcp9700Temp import Mcp9700Temp
from upyiot.drivers.Sensors.PhTLight import PhTLight
from upyiot.drivers.Switches.TactSwitch import TactSwitch
from upyiot.drivers.Led.RgbLed import RgbLed
from UserInterface.Notification import Notifyer
from UserInterface.Notification import NotificationRange
from UserInterface.Notification import Notification

hold_times = (1000, 5000, 10000)
timers = (0, -1)

def raw_temp_to_celsius(raw_temp):
    cel_temp = raw_temp * (2.5 / 1024)
    cel_temp -= 0.5
    cel_temp /= 0.01
    return cel_temp


def callback_pressed(press_count):
    print("Pressed: {}".format(press_count))


def callback_released(hold_idx):
    print("Released")
    if hold_idx is not -1:
        print("Held for {} ms".format(hold_times[hold_idx]))


def callback_rest(press_count):
    print("Rest. Pressed {} times".format(press_count))


def main():
    sw_callbacks = (callback_pressed, callback_released, callback_rest)

    vsensor = Pin(0, Pin.OUT)
    temp = Mcp9700Temp(32)
    moist = CapMoisture(34, 0)
    light = PhTLight(33)
    sw = TactSwitch(27, timers, sw_callbacks, hold_times, 500)
    rgb_led = RgbLed(21, 23, 22)

    sw.Enable()

    while True:
        vsensor.on()
        time.sleep(1)

        moist_val = moist.Read()

        vsensor.on()
        time.sleep(1)

        temp_val = temp.Read()
        light_val = light.Read()

        vsensor.off()

        temp_val = raw_temp_to_celsius(temp_val)

        print("Moist: {} | Temp: {}C | Light: {}".format(moist_val, temp_val, light_val))


        time.sleep(2)


if __name__ == '__main__':
    main()
