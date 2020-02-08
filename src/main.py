from DemoApp.DemoApp import DemoApp
from WebApp.WebApp import WebApp
from upyiot.comm.NetCon.NetCon import NetCon

# Other
from micropython import const
import machine
import ubinascii
import utime


ID = str(ubinascii.hexlify(machine.unique_id()).decode('utf-8'))
DIR = "./"
ApCfg = {"ssid": "SmartSensor-" + ID, "pwd": "mato", "ip": "192.168.0.200"}


if __name__ == '__main__':

    netcon = NetCon(DIR, ApCfg)
    app = None

    if netcon.StationSettingsAreSet():
        print("[App] Found station settings.")
        print("[App] Booting Main App.")
        app = DemoApp(netcon)
    else:
        print("[App] No station settings.")
        print("[App] Booting Web App.")
        app = WebApp(netcon)

    app.Setup()
    app.Run()
