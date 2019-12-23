import DummySensor
from upyiot.system.ExtLogging import ExtLogging
from upyiot.system.SystemTime.SystemTime import SystemTime
from upyiot.system.Service.ServiceScheduler import ServiceScheduler
from upyiot.system.Service.ServiceScheduler import Service
from upyiot.comm.NetCon.NetCon import NetCon
from upyiot.comm.Web.Webserver import Webserver
from upyiot.drivers.Led.Led import Led

# SmartSensor modules
from Config.Hardware import Pins

# Other
import network
from network import WLAN
from micropython import const
import machine
import ubinascii
import utime


class WebApp:

    PRODUCT_NAME = "smartsensor"
    DIR = "./"
    ID = str(ubinascii.hexlify(machine.unique_id()).decode('utf-8'))
    RETRIES = 3
    BROKER = '192.168.0.103'
    PORT = 1883
    ApCfg = {"ssid": "SmartSensor-" + ID, "pwd": "mato", "ip": "192.168.0.200"}

    Time = None
    NetCon = None

    WebserverInterval   = const(1)
    WebpageTitle = "SmartSensor - WiFi instellingen"

    Webpage = """<html><head>
        <title>""" + WebpageTitle + """</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link rel="icon" href="data:,">
        <style>html{font-family: Helvetica; display:inline-block; margin: 0px auto; text-align: center;}
        h1{color: #0F3376; padding: 2vh;}p{font-size: 1.5rem;}.button{display: inline-block; background-color: #e7bd3b; border: none;
        border-radius: 4px; color: white; padding: 16px 40px; text-decoration: none; font-size: 30px; margin: 2px; cursor: pointer;}
        .button2{background-color: #4286f4;}
        </style>
        </head>
        <body> <h1>""" + WebpageTitle + """</h1>
        <h2>Sensor ID: """ + ID + """</h2>
        <form action="/wifi_settings.php">
        Netwerk naam (SSID): <input type="text" name="ssid" value=""><br>
        Wachtwoord:          <input type="password" name="pwd" value=""><br>
        <input type="submit" value="Opslaan">
        </form>
        </body>
        </html>"""

    Ssid = None
    Pwd = None

    def __init__(self, netcon_obj):

        # Create objects.
        self.Time = SystemTime.InstanceGet()
        WebApp.NetCon = netcon_obj
        self.Scheduler = ServiceScheduler()

    def Setup(self):
        # Create LED driver instances.
        self.LedRed = Led(Pins.CFG_HW_PIN_LED_RED)
        self.LedGreen = Led(Pins.CFG_HW_PIN_LED_GREEN)
        self.LedBlue = Led(Pins.CFG_HW_PIN_LED_BLUE)

        wlan_ap = WLAN(network.AP_IF)
        self.NetCon.WlanInterface(wlan_ap, NetCon.MODE_ACCESS_POINT)

        self.Webserver = Webserver(self.Webpage)

        self.Webserver.RegisterQueryHandle('ssid', WebApp.QueryHandleWifiSsid)
        self.Webserver.RegisterQueryHandle('pwd', WebApp.QueryHandleWifiPwd)

        self.Webserver.SvcDependencies({self.NetCon: Service.DEP_TYPE_RUN_ALWAYS_BEFORE_INIT})

        self.Scheduler.ServiceRegister(self.NetCon)
        self.Scheduler.ServiceRegister(self.Webserver)

        self.Webserver.SvcIntervalSet(self.WebserverInterval)

    def Reset(self):
        return

    def Run(self):
        self.Scheduler.Run()

    @staticmethod
    def QueryHandleWifiSsid(query, value):
        print("{}:{}".format(query, value))
        WebApp.Ssid = value
        if WebApp.Pwd is not None:
            WebApp.SaveAndReset()

    @staticmethod
    def QueryHandleWifiPwd(query, value):
        print("{}:{}".format(query, value))
        WebApp.Pwd = value
        if WebApp.Ssid is not None:
            WebApp.SaveAndReset()

    @staticmethod
    def SaveAndReset():
        WebApp.NetCon.StationSettingsStore(WebApp.Ssid, WebApp.Pwd)
        WebApp.NetCon.AccessPointStop()
        utime.sleep(1)
        machine.reset()



