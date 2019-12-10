from machine import Pin
import time
from upyiot.drivers.Sensors.CapMoisture import CapMoisture
from upyiot.drivers.Sensors.Mcp9700Temp import Mcp9700Temp
from upyiot.drivers.Sensors.PhTLight import PhTLight


def raw_temp_to_celsius(raw_temp):
    cel_temp = raw_temp * (2.5 / 1024)
    cel_temp -= 0.5
    cel_temp /= 0.01
    return cel_temp


def main():
    vsensor = Pin(0, Pin.OUT)
    temp = Mcp9700Temp(32)
    moist = CapMoisture(34, 0)
    light = PhTLight(33)

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
