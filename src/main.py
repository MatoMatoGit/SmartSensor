import DummySensor
import network
from network import WLAN
from upyiot.system.ExtLogging import ExtLogging
from upyiot.system.SystemTime.SystemTime import SystemTime
from upyiot.system.Service.ServiceScheduler import ServiceScheduler
from upyiot.comm.NetCon.NetCon import NetCon
from upyiot.comm.Messaging.MessageExchange import MessageExchange
from upyiot.comm.Messaging.MessageExchange import Endpoint
from upyiot.comm.Messaging.MessageFormatAdapter import MessageFormatAdapter
from upyiot.comm.Messaging.MessageSpecification import MessageSpecification
from upyiot.comm.Web.Webserver import Webserver
from upyiot.middleware.Sensor import Sensor

# Other
from umqtt.simple import MQTTClient
from micropython import const
import machine
import ubinascii
import utime


class SensorReport(MessageSpecification):

    TYPE_SENSOR_REPORT        = const(0)
    BASE_URL_SENSOR_REPORT         = "<pn>/<id>/"
    DATA_KEY_SENSOR_REPORT_SAMPLES  = "smp"
    DIRECTION_SENSOR_REPORT   = MessageSpecification.MSG_DIRECTION_SEND

    def __init__(self, subtype, url_suffix):
        self.DataDef = {SensorReport.DATA_KEY_SENSOR_REPORT_SAMPLES: []}
        super().__init__(SensorReport.TYPE_SENSOR_REPORT,
                         subtype,
                         self.DataDef,
                         SensorReport.BASE_URL_SENSOR_REPORT + url_suffix,
                         SensorReport.DIRECTION_SENSOR_REPORT)


class SensorReportTemp(SensorReport):

    NAME_TEMP = "temp"
    SUBTYPE_TEMP = const(1)

    def __init__(self):
        super().__init__(SensorReportTemp.SUBTYPE_TEMP, SensorReportTemp.NAME_TEMP)


class SensorReportMoist(SensorReport):

    NAME_MOIST = "moist"
    SUBTYPE_MOIST = const(2)

    def __init__(self):
        super().__init__(SensorReportMoist.SUBTYPE_MOIST, SensorReportMoist.NAME_MOIST)


class LogMessage(MessageSpecification):

    TYPE_LOG_MSG        = const(1)
    SUBTYPE_LOG_MSG     = const(1)
    URL_LOG_MSG         = "<pn>/<id>/log"
    DATA_KEY_LOG_MSG  = "msg"
    DATA_DEF_LOG_MSG    = {DATA_KEY_LOG_MSG: ""}
    DIRECTION_LOG_MSG   = MessageSpecification.MSG_DIRECTION_SEND

    def __init__(self):
        super().__init__(LogMessage.TYPE_LOG_MSG,
                         LogMessage.SUBTYPE_LOG_MSG,
                         LogMessage.DATA_DEF_LOG_MSG,
                         LogMessage.URL_LOG_MSG,
                         LogMessage.DIRECTION_LOG_MSG)


class App:

    MODE_MAIN_APP   = const(0)
    MODE_WEB_APP    = const(1)

    PRODUCT_NAME = "smartsensor"
    DIR = "./"
    ID = str(ubinascii.hexlify(machine.unique_id()).decode('utf-8'))
    RETRIES = 3
    BROKER = '192.168.0.103'
    PORT = 1883
    ApCfg = {"ssid": "SmartSensor-" + ID, "pwd": "mato", "ip": "192.168.0.200"}

    MqttClient = None
    MsgEx = None
    Time = None
    NetCon = None
    UrlFields = {MessageSpecification.URL_FIELD_DEVICE_ID: ID,
                 MessageSpecification.URL_FIELD_PRODUCT_NAME: PRODUCT_NAME}

    TempSamples = [20, 21, 25, 30, 35, 35, 20, 12, 10, 40]
    MoistSamples = [200, 300, 350, 360, 290, 500, 250, 300, 240, 320]

    SamplesPerMessage   = const(3)
    MsgExInterval       = const(10)
    SensorReadInterval  = const(3)
    WebserverInterval   = const(2)
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
    AppMode = MODE_MAIN_APP

    def __init__(self):
        # Configure the URL fields.
        MessageSpecification.Config(self.UrlFields)

        # Create objects.
        self.Time = SystemTime.InstanceGet()
        App.NetCon = NetCon(self.DIR, self.ApCfg)
        self.Scheduler = ServiceScheduler()

        if self.NetCon.StationSettingsAreSet():
            print("[App] Found station settings.")
            print("[App] Setting up Main App.")
            self.SetupMainApp()
        else:
            print("[App] No station settings.")
            print("[App] Setting up Web App.")
            self.SetupWebApp()

    def Reset(self):
        self.MsgEx.Reset()
        self.TempSensor.SamplesDelete()
        self.MoistSensor.SamplesDelete()
        self.NetCon.StationSettingsReset()

    def Run(self):
        self.Scheduler.Run(20)

        if self.AppMode is App.MODE_MAIN_APP:
            self.NetCon.StationSettingsReset()
            self.MsgEx.Reset()
            self.TempSensor.SamplesDelete()
            self.MoistSensor.SamplesDelete()

    @staticmethod
    def QueryHandleWifiSsid(query, value):
        print("{}:{}".format(query, value))
        App.Ssid = value

    @staticmethod
    def QueryHandleWifiPwd(query, value):
        print("{}:{}".format(query, value))
        App.Pwd = value
        App.NetCon.StationSettingsStore(App.Ssid, App.Pwd)
        App.NetCon.AccessPointStop()
        utime.sleep(1)
        machine.reset()

    def SetupMainApp(self):
        filter_depth = len(self.TempSamples) / 2
        dummy_temp_sensor = DummySensor.DummySensor(self.TempSamples)
        dummy_moist_sensor = DummySensor.DummySensor(self.MoistSamples)

        wlan_ap = WLAN(network.STA_IF)
        self.NetCon.WlanInterface(wlan_ap, NetCon.MODE_STATION)

        self.TempSensor = Sensor.Sensor(self.DIR,
                                        SensorReportTemp.NAME_TEMP,
                                        filter_depth, dummy_temp_sensor)
        self.MoistSensor = Sensor.Sensor(self.DIR,
                                         SensorReportMoist.NAME_MOIST,
                                         filter_depth, dummy_moist_sensor)
        self.MqttClient = MQTTClient(self.ID,
                                     self.BROKER,
                                     self.PORT)
        self.MsgEx = MessageExchange(self.DIR,
                                     self.MqttClient,
                                     self.ID,
                                     self.RETRIES)

        self.MsgEp = Endpoint()

        # Set service dependencies.
        self.Time.SvcDependencies(())
        self.MsgEx.SvcDependencies((self.Time,))
        self.TempSensor.SvcDependencies((self.Time,))
        self.MoistSensor.SvcDependencies((self.Time,))

        self.NetCon.StationStart()

        # Register all services to the scheduler.
        self.Scheduler.ServiceRegister(self.Time)
        self.Scheduler.ServiceRegister(self.NetCon)
        self.Scheduler.ServiceRegister(self.MsgEx)
        self.Scheduler.ServiceRegister(self.TempSensor)
        self.Scheduler.ServiceRegister(self.MoistSensor)

        # Create message specifications.
        self.TempMsgSpec = SensorReportTemp()
        self.MoistMsgSpec = SensorReportMoist()
        self.LogMsgSpec = LogMessage()

        # Create a Messaging Endpoint and MessageFormatAdapters.
        self.TempAdapt = MessageFormatAdapter(self.MsgEp,
                                              MessageFormatAdapter.SEND_ON_COMPLETE,
                                              self.TempMsgSpec)
        self.MoistAdapt = MessageFormatAdapter(self.MsgEp,
                                               MessageFormatAdapter.SEND_ON_COMPLETE,
                                               self.MoistMsgSpec)
        self.LogAdapt = MessageFormatAdapter(self.MsgEp,
                                             MessageFormatAdapter.SEND_ON_COMPLETE,
                                             self.LogMsgSpec)

        # Register message specs.
        self.MsgEx.RegisterMessageType(self.TempMsgSpec)
        self.MsgEx.RegisterMessageType(self.MoistMsgSpec)
        self.MsgEx.RegisterMessageType(self.LogMsgSpec)

        # Create observers for the sensor data.
        self.TempObserver = self.TempAdapt.CreateObserver(
            SensorReportTemp.DATA_KEY_SENSOR_REPORT_SAMPLES, self.SamplesPerMessage)
        self.MoistObserver = self.MoistAdapt.CreateObserver(
            SensorReportMoist.DATA_KEY_SENSOR_REPORT_SAMPLES, self.SamplesPerMessage)

        # Link the observers to the sensors.
        self.TempSensor.ObserverAttachNewSample(self.TempObserver)
        self.MoistSensor.ObserverAttachNewSample(self.MoistObserver)

        # Create a stream for the log messages.
        self.LogStream = self.LogAdapt.CreateStream(LogMessage.DATA_KEY_LOG_MSG, ExtLogging.WRITES_PER_LOG)

        # Configure the ExtLogging class.
        ExtLogging.ConfigGlobal(level=ExtLogging.INFO, stream=self.LogStream)

        self.MsgEx.SvcIntervalSet(self.MsgExInterval)
        self.MoistSensor.SvcIntervalSet(self.SensorReadInterval)
        self.TempSensor.SvcIntervalSet(self.SensorReadInterval)

        self.AppMode = App.MODE_MAIN_APP

    def SetupWebApp(self):
        wlan_ap = WLAN(network.AP_IF)
        self.NetCon.WlanInterface(wlan_ap, NetCon.MODE_ACCESS_POINT)

        self.Webserver = Webserver(self.Webpage)

        self.Webserver.RegisterQueryHandle('ssid', App.QueryHandleWifiSsid)
        self.Webserver.RegisterQueryHandle('pwd', App.QueryHandleWifiPwd)

        self.NetCon.AccessPointStart()

        self.Scheduler.ServiceRegister(self.Webserver)

        self.Webserver.SvcIntervalSet(self.WebserverInterval)

        self.AppMode = App.MODE_WEB_APP

ApCfg = {"ssid": "SmartSensor-" + ID, "pwd": "mato", "ip": "192.168.0.200"}

if __name__ == '__main__':
    if self.NetCon.StationSettingsAreSet():
        print("[App] Found station settings.")
        print("[App] Setting up Main App.")
        self.SetupMainApp()
    else:
        print("[App] No station settings.")
        print("[App] Setting up Web App.")
        self.SetupWebApp()

    app = App()
    app.Run()
