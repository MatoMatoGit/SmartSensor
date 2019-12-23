
# upyiot modules
from upyiot.system.ExtLogging import ExtLogging
from upyiot.system.SystemTime.SystemTime import SystemTime
from upyiot.system.Service.ServiceScheduler import ServiceScheduler
from upyiot.system.Service.ServiceScheduler import Service
# from upyiot.system.Power.BatteryMonitor import BatteryMonitor
from upyiot.comm.NetCon.NetCon import NetCon
from upyiot.comm.Messaging.MessageExchange import MessageExchange
from upyiot.comm.Messaging.MessageExchange import Endpoint
from upyiot.comm.Messaging.MessageSpecification import MessageSpecification
from upyiot.comm.Messaging.MessageFormatAdapter import MessageFormatAdapter
from upyiot.middleware.Sensor import Sensor

from upyiot.drivers.Sensors.CapMoisture import CapMoisture
from upyiot.drivers.Sensors.Mcp9700Temp import Mcp9700Temp
from upyiot.drivers.Sensors.PhTLight import PhTLight
# from upyiot.drivers.Sensors.BatteryLevel import BatteryLevel
from upyiot.drivers.Led.Led import Led

# SmartSensor modules
from Messages.LogMessage import LogMessage
from Messages.SensorReport import SensorReportTemp
from Messages.SensorReport import SensorReportMoist
from Messages.SensorReport import SensorReportLight
# from Messages.SensorReport import SensorReportVBat
from Config.Hardware import Pins

# micropython modules
import network
from network import WLAN
from umqtt.simple import MQTTClient
from micropython import const
import machine
import ubinascii
import utime


class MainApp:

    PRODUCT_NAME = "smartsensor"
    DIR = "./"
    ID = str(ubinascii.hexlify(machine.unique_id()).decode('utf-8'))
    RETRIES = 3
    BROKER = '192.168.0.103'
    PORT = 1883
    FILTER_DEPTH = const(20)
    DEEPSLEEP_THRESHOLD_SEC = const(5)

    MqttClient = None
    MsgEx = None
    Time = None
    NetCon = None
    UrlFields = {MessageSpecification.URL_FIELD_DEVICE_ID: ID,
                 MessageSpecification.URL_FIELD_PRODUCT_NAME: PRODUCT_NAME}

    SamplesPerMessage   = const(1)

    # Service intervals in seconds.
    MsgExInterval           = const(60)
    EnvSensorReadInterval   = const(10)
    VBatSensorReadInterval  = const(20)

    def __init__(self, netcon_obj):
        # Configure the URL fields.
        MessageSpecification.Config(self.UrlFields)

        MainApp.NetCon = netcon_obj

    def Setup(self):

        # Create sensor driver instances.
        self.CapMoist = CapMoisture(Pins.CFG_HW_PIN_CAP_MOIST_PULSE, Pins.CFG_HW_PIN_VSENSOR_EN)
        self.Mcp9700Temp = Mcp9700Temp(Pins.CFG_HW_PIN_TEMP)
        self.PhTLight = PhTLight(Pins.CFG_HW_PIN_PHOTO)
        # self.VBat = BatteryLevel(1, Pins.CFG_HW_PIN_VBAT_MEAS, Pins.CFG_HW_PIN_VBAT_MEAS_EN)

        # Create LED driver instances.
        self.LedRed = Led(Pins.CFG_HW_PIN_LED_RED)
        self.LedGreen = Led(Pins.CFG_HW_PIN_LED_GREEN)
        self.LedBlue = Led(Pins.CFG_HW_PIN_LED_BLUE)

        # Create the WLAN station interface.
        wlan_ap = WLAN(network.STA_IF)

        self.Time = SystemTime.InstanceGet()
        self.NetCon.WlanInterface(wlan_ap, NetCon.MODE_STATION)

        self.TempSensor = Sensor.Sensor(self.DIR,
                                        SensorReportTemp.NAME_TEMP,
                                        self.FILTER_DEPTH, self.Mcp9700Temp)

        self.MoistSensor = Sensor.Sensor(self.DIR,
                                         SensorReportMoist.NAME_MOIST,
                                         self.FILTER_DEPTH, self.CapMoist)

        self.LightSensor = Sensor.Sensor(self.DIR,
                                         SensorReportLight.NAME_LIGHT,
                                         self.FILTER_DEPTH, self.PhTLight)

        # self.VBatSensor = Sensor.Sensor(self.DIR,
        #                                 SensorReportVbat.NAME_VBAT,
        #                                 self.FILTER_DEPTH, self.VBat)
        #
        # self.VBatMon = BatteryMonitor(self.DIR, self.VBat, 20)

        self.MqttClient = MQTTClient(self.ID,
                                     self.BROKER,
                                     self.PORT)
        self.MsgEx = MessageExchange(self.DIR,
                                     self.MqttClient,
                                     self.ID,
                                     self.RETRIES)

        self.MsgEp = Endpoint()

        self.Scheduler = ServiceScheduler(self.DEEPSLEEP_THRESHOLD_SEC)

        # Set service dependencies.
        self.Time.SvcDependencies({self.NetCon: Service.DEP_TYPE_RUN_ALWAYS_BEFORE_RUN})
        self.MsgEx.SvcDependencies({self.Time: Service.DEP_TYPE_RUN_ONCE_BEFORE_RUN,
                                    self.NetCon: Service.DEP_TYPE_RUN_ALWAYS_BEFORE_INIT})
        self.TempSensor.SvcDependencies({self.Time: Service.DEP_TYPE_RUN_ONCE_BEFORE_RUN})
        self.MoistSensor.SvcDependencies({self.Time: Service.DEP_TYPE_RUN_ONCE_BEFORE_RUN})
        self.LightSensor.SvcDependencies({self.Time: Service.DEP_TYPE_RUN_ONCE_BEFORE_RUN})

        # Register all services to the scheduler.
        self.Scheduler.ServiceRegister(self.Time)
        self.Scheduler.ServiceRegister(self.NetCon)
        self.Scheduler.ServiceRegister(self.MsgEx)
        self.Scheduler.ServiceRegister(self.TempSensor)
        self.Scheduler.ServiceRegister(self.MoistSensor)
        self.Scheduler.ServiceRegister(self.LightSensor)
        # self.Scheduler.ServiceRegister(self.VBatMon.BatteryLevelSensor)

        # Create message specifications.
        self.TempMsgSpec = SensorReportTemp()
        self.MoistMsgSpec = SensorReportMoist()
        self.LightMsgSpec = SensorReportLight()
        self.LogMsgSpec = LogMessage()
        # self.VBatMsgSpec = SensorReportVBat()

        # Create MessageFormatAdapters and couple them with their message specs.
        self.TempAdapt = MessageFormatAdapter(self.MsgEp,
                                              MessageFormatAdapter.SEND_ON_COMPLETE,
                                              self.TempMsgSpec)
        self.MoistAdapt = MessageFormatAdapter(self.MsgEp,
                                               MessageFormatAdapter.SEND_ON_COMPLETE,
                                               self.MoistMsgSpec)
        self.LightAdapt = MessageFormatAdapter(self.MsgEp,
                                               MessageFormatAdapter.SEND_ON_COMPLETE,
                                               self.LightMsgSpec)
        self.LogAdapt = MessageFormatAdapter(self.MsgEp,
                                             MessageFormatAdapter.SEND_ON_COMPLETE,
                                             self.LogMsgSpec)
        # self.VBatAdapt = MessageFormatAdapter(self.MsgEp,
        #                                       MessageFormatAdapter.SEND_ON_COMPLETE,
        #                                       self.VBatMsgSpec)

        # Register message specs for exchange.
        self.MsgEx.RegisterMessageType(self.TempMsgSpec)
        self.MsgEx.RegisterMessageType(self.MoistMsgSpec)
        self.MsgEx.RegisterMessageType(self.LightMsgSpec)
        self.MsgEx.RegisterMessageType(self.LogMsgSpec)
        # self.MsgEx.RegisterMessageType(self.VBatMsgSpec)

        # Create observers for the sensor data.
        self.TempObserver = self.TempAdapt.CreateObserver(
            SensorReportTemp.DATA_KEY_SENSOR_REPORT_SAMPLES,
            self.SamplesPerMessage)
        self.MoistObserver = self.MoistAdapt.CreateObserver(
            SensorReportMoist.DATA_KEY_SENSOR_REPORT_SAMPLES,
            self.SamplesPerMessage)
        self.LightObserver = self.LightAdapt.CreateObserver(
            SensorReportLight.DATA_KEY_SENSOR_REPORT_SAMPLES,
            self.SamplesPerMessage)
        # self.VBatObserver = self.VBatAdapt.CreateObserver(
        #     SensorReportVBat.DATA_KEY_SENSOR_REPORT_SAMPLES,
        #     self.SamplesPerMessage)

        # Link the observers to the sensors.
        self.TempSensor.ObserverAttachNewSample(self.TempObserver)
        self.MoistSensor.ObserverAttachNewSample(self.MoistObserver)
        self.LightSensor.ObserverAttachNewSample(self.LightObserver)
        # self.VBatMon.BatteryLevelSensor.ObserverAttachNewSample(self.VBatObserver)

        # Create a stream for the log messages.
        self.LogStream = self.LogAdapt.CreateStream(LogMessage.DATA_KEY_LOG_MSG,
                                                    ExtLogging.WRITES_PER_LOG)

        # Configure the ExtLogging class.
        ExtLogging.ConfigGlobal(level=ExtLogging.INFO, stream=self.LogStream)

        # Set intervals for all services.
        self.MsgEx.SvcIntervalSet(self.MsgExInterval)
        self.MoistSensor.SvcIntervalSet(self.EnvSensorReadInterval)
        self.TempSensor.SvcIntervalSet(self.EnvSensorReadInterval)
        self.LightSensor.SvcIntervalSet(self.EnvSensorReadInterval)
        # self.VBatMon.BatteryLevelSensor.SvcIntervalSet(self.VBatSensorReadInterval)

    def Reset(self):
        self.MsgEx.Reset()
        self.TempSensor.SamplesDelete()
        self.MoistSensor.SamplesDelete()
        self.LightSensor.SamplesDelete()
        self.NetCon.StationSettingsReset()

    def Run(self):
        self.LedRed.Toggle()
        utime.sleep(1)
        self.LedRed.Toggle()

        self.LedGreen.Toggle()
        utime.sleep(1)
        self.LedGreen.Toggle()

        self.LedBlue.Toggle()
        utime.sleep(1)
        self.LedBlue.Toggle()

        self.Scheduler.Run()
