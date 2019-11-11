
# upyiot modules
import DummySensor
from upyiot.system.ExtLogging import ExtLogging
from upyiot.system.SystemTime.SystemTime import SystemTime
from upyiot.system.Service.ServiceScheduler import ServiceScheduler
from upyiot.comm.NetCon.NetCon import NetCon
from upyiot.comm.Messaging.MessageExchange import MessageExchange
from upyiot.comm.Messaging.MessageExchange import Endpoint
from upyiot.comm.Messaging.MessageSpecification import MessageSpecification
from upyiot.comm.Messaging.MessageFormatAdapter import MessageFormatAdapter
from upyiot.middleware.Sensor import Sensor

# SmartSensor modules
from Messages.LogMessage import LogMessage
from Messages.SensorReport import SensorReportTemp
from Messages.SensorReport import SensorReportMoist

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

    def __init__(self, netcon_obj):
        # Configure the URL fields.
        MessageSpecification.Config(self.UrlFields)

        # Create objects.
        self.Time = SystemTime.InstanceGet()
        MainApp.NetCon = netcon_obj
        self.Scheduler = ServiceScheduler()

    def Setup(self):
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

        # Connect to the configured AP.
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

    def Reset(self):
        self.MsgEx.Reset()
        self.TempSensor.SamplesDelete()
        self.MoistSensor.SamplesDelete()
        self.NetCon.StationSettingsReset()

    def Run(self):
        self.Scheduler.Run(20)
        self.Reset()
