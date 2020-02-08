
# upyiot modules
from upyiot.system.ExtLogging import ExtLogging
from upyiot.system.SystemTime.SystemTime import SystemTime
from upyiot.system.Service.ServiceScheduler import ServiceScheduler
from upyiot.system.Service.ServiceScheduler import Service
from upyiot.system.Util import ResetReason
from upyiot.comm.NetCon.NetCon import NetCon
from upyiot.comm.Messaging.MessageExchange import MessageExchange
from upyiot.comm.Messaging.MessageExchange import Endpoint
from upyiot.comm.Messaging.MessageSpecification import MessageSpecification
from upyiot.comm.Messaging.MessageFormatAdapter import MessageFormatAdapter
from upyiot.middleware.Sensor import Sensor

from upyiot.drivers.Board.Supply import Supply
from upyiot.drivers.Sensors.CapMoisture import CapMoisture
from upyiot.drivers.Sensors.Mcp9700Temp import Mcp9700Temp
from upyiot.drivers.Sensors.PhTLight import PhTLight
from upyiot.drivers.Led.RgbLed import RgbLed

# SmartSensor modules
from Messages.LogMessage import LogMessage
from Messages.SensorReport import SensorReportMoist
from Messages.SensorReport import SensorReportTemp
from Messages.SensorReport import SensorReportLight
from Messages.SensorReport import SensorReportMoistCalibLow
from Messages.SensorReport import SensorReportMoistCalibHigh
from UserInterface.Notification import Notifyer
from UserInterface.Notification import NotificationRange
from UserInterface.Notification import Notification
from UserInterface.UserButton import UserButton
from Config.Hardware import Pins

# micropython modules
import network
from network import WLAN
from umqtt.simple import MQTTClient
from micropython import const
import machine
import ubinascii
import utime

BROKER_IP_PC = '192.168.0.103'
BROKER_IP_PI = '192.168.0.111'

class DemoApp:

    PRODUCT_NAME = "smartsensor"
    DIR = "./"
    ID = str(ubinascii.hexlify(machine.unique_id()).decode('utf-8'))
    RETRIES = 3
    BROKER = BROKER_IP_PC
    PORT = 1883
    FILTER_DEPTH = const(6)
    DEEPSLEEP_THRESHOLD_SEC = const(5)

    MOIST_RANGE_MIN = const(200)
    MOIST_RANGE_MAX = const(2000)
    MOIST_NOTIF_TIME = const(1)
    MOIST_NOTIF_PRIO = const(5)

    SUPPLY_SETTLE_TIME_MS = const(100)

    NetCon = None
    UrlFields = {MessageSpecification.URL_FIELD_DEVICE_ID: ID,
                 MessageSpecification.URL_FIELD_PRODUCT_NAME: PRODUCT_NAME}

    SamplesPerMessage   = const(1)

    # Service intervals in seconds.
    MsgExInterval           = const(20)
    MoistSensorReadInterval = const(2)
    EnvSensorReadInterval   = const(15)
    NotificationInterval    = const(2)

    APP_MODE_SCAN = const(0)
    APP_MODE_CALIBRATION    = const(1)

    Mode = APP_MODE_SCAN
    StartApp = False

    CALIB_STATE_SET_LOW = const(0)
    CALIB_STATE_SET_HIGH = const(1)
    CALIB_STATE_SET_SYNC = const(2)

    CalibState = CALIB_STATE_SET_LOW

    def __init__(self, netcon_obj):
        # Configure the URL fields.
        MessageSpecification.Config(self.UrlFields)

        DemoApp.NetCon = netcon_obj

    def Setup(self):

        rst_reason = ResetReason.ResetReason()
        print("[Setup] Reset reason: {}".format(ResetReason.ResetReasonToString(rst_reason)))

        # Create driver instances.
        self.VSensor = Supply(Pins.CFG_HW_PIN_MOIST_EN, self.SUPPLY_SETTLE_TIME_MS)

        self.CapMoist = CapMoisture(Pins.CFG_HW_PIN_MOIST, self.VSensor)
        self.Mcp9700Temp = Mcp9700Temp(Pins.CFG_HW_PIN_TEMP, self.VSensor)
        self.Ldr = PhTLight(Pins.CFG_HW_PIN_LDR, self.VSensor)

        self.RgbLed = RgbLed(Pins.CFG_HW_PIN_LED_RED,
                             Pins.CFG_HW_PIN_LED_GREEN, Pins.CFG_HW_PIN_LED_BLUE)

        self.Button = UserButton(Pins.CFG_HW_PIN_BTN_0, context=self, press_cb=DemoApp.ButtonPressed,
                                 release_cb=DemoApp.ButtonRelease)
        self.Button.Enable()

        # Wait until mode has been selected by the user.
        while DemoApp.StartApp is False:
            utime.sleep(1)

        # Continued common setup sequence after mode selection:

        # Create the WLAN station interface.
        wlan_ap = WLAN(network.STA_IF)

        self.Time = SystemTime.InstanceGet()
        self.NetCon.WlanInterface(wlan_ap, NetCon.MODE_STATION)

        self.TempSensor = Sensor.Sensor(self.DIR,
                                        SensorReportTemp.NAME_TEMP,
                                        self.FILTER_DEPTH, self.Mcp9700Temp,
                                        self.FILTER_DEPTH)

        self.MoistSensor = Sensor.Sensor(self.DIR,
                                         SensorReportMoist.NAME_MOIST,
                                         self.FILTER_DEPTH, self.CapMoist,
                                         self.FILTER_DEPTH)

        self.LightSensor = Sensor.Sensor(self.DIR,
                                         SensorReportLight.NAME_LIGHT,
                                         self.FILTER_DEPTH, self.Ldr,
                                         self.FILTER_DEPTH)

        self.MqttClient = MQTTClient(self.ID,
                                     self.BROKER,
                                     self.PORT)
        self.MsgEx = MessageExchange(self.DIR,
                                     self.MqttClient,
                                     self.ID,
                                     self.RETRIES)

        self.MsgEp = Endpoint()

        self.Scheduler = ServiceScheduler(self.DEEPSLEEP_THRESHOLD_SEC)

        # Execute mode specific setup.
        if DemoApp.Mode is DemoApp.APP_MODE_SCAN:
            self.SetupScanMode()
        else:
            self.SetupCalibMode()


    def SetupCalibMode(self):

        # Set service dependencies.
        self.Time.SvcDependencies({self.NetCon: Service.DEP_TYPE_RUN_ALWAYS_BEFORE_RUN})
        self.MsgEx.SvcDependencies({self.Time: Service.DEP_TYPE_RUN_ONCE_BEFORE_RUN,
                                    self.NetCon: Service.DEP_TYPE_RUN_ALWAYS_BEFORE_INIT})
        self.MoistSensor.SvcDependencies({self.Time: Service.DEP_TYPE_RUN_ONCE_BEFORE_RUN})

        # Register all services to the scheduler.
        self.Scheduler.ServiceRegister(self.Time)
        self.Scheduler.ServiceRegister(self.NetCon)
        self.Scheduler.ServiceRegister(self.MsgEx)
        self.Scheduler.ServiceRegister(self.MoistSensor)

        # Create message specifications.
        self.MoistCalibLowMsgSpec = SensorReportMoistCalibLow()
        self.MoistCalibHighMsgSpec = SensorReportMoistCalibHigh()
        self.LogMsgSpec = LogMessage()

        # Create MessageFormatAdapters and couple them with their message specs.
        self.MoistCalibLowAdapt = MessageFormatAdapter(self.MsgEp,
                                                       MessageFormatAdapter.SEND_ON_COMPLETE,
                                                       self.MoistCalibLowMsgSpec)
        self.MoistCalibHighAdapt = MessageFormatAdapter(self.MsgEp,
                                                        MessageFormatAdapter.SEND_ON_COMPLETE,
                                                        self.MoistCalibHighMsgSpec)
        self.LogAdapt = MessageFormatAdapter(self.MsgEp,
                                             MessageFormatAdapter.SEND_ON_COMPLETE,
                                             self.LogMsgSpec)

        # Register message specs for exchange.
        self.MsgEx.RegisterMessageType(self.MoistCalibLowMsgSpec)
        self.MsgEx.RegisterMessageType(self.MoistCalibHighMsgSpec)
        self.MsgEx.RegisterMessageType(self.LogMsgSpec)

        # Create observer for the low calibration.
        self.MoistObserver = self.MoistCalibLowAdapt.CreateObserver(
            SensorReportMoistCalibLow.DATA_KEY_SENSOR_REPORT_SAMPLES,
            self.SamplesPerMessage)

        # Link the observers to the sensors.
        self.MoistSensor.ObserverAttachNewSample(self.MoistObserver)

        # Create a stream for the log messages.
        self.LogStream = self.LogAdapt.CreateStream(LogMessage.DATA_KEY_LOG_MSG,
                                                    ExtLogging.WRITES_PER_LOG)

        # Configure the ExtLogging class.
        ExtLogging.ConfigGlobal(level=ExtLogging.INFO, stream=self.LogStream)

        # Set service modes.
        self.MsgEx.SvcMode = Service.MODE_RUN_ONCE

        # Set intervals for periodic services.
        self.MoistSensor.SvcIntervalSet(self.MoistSensorReadInterval)

        return

    def SetupScanMode(self):

        self.Notifyer = Notifyer(self.RgbLed)

        # Set service dependencies.
        self.Time.SvcDependencies({self.NetCon: Service.DEP_TYPE_RUN_ALWAYS_BEFORE_RUN})
        self.MoistSensor.SvcDependencies({self.Time: Service.DEP_TYPE_RUN_ONCE_BEFORE_RUN})

        self.Notifyer.SvcDependencies({self.MoistSensor: Service.DEP_TYPE_RUN_ALWAYS_BEFORE_RUN})

        self.TempSensor.SvcDependencies({self.Time: Service.DEP_TYPE_RUN_ONCE_BEFORE_RUN})
        self.LightSensor.SvcDependencies({self.Time: Service.DEP_TYPE_RUN_ONCE_BEFORE_RUN})

        self.MsgEx.SvcDependencies({self.Time: Service.DEP_TYPE_RUN_ONCE_BEFORE_RUN,
                                    self.NetCon: Service.DEP_TYPE_RUN_ALWAYS_BEFORE_INIT,
                                    self.TempSensor: Service.DEP_TYPE_RUN_ONCE_BEFORE_RUN,
                                    self.LightSensor: Service.DEP_TYPE_RUN_ONCE_BEFORE_RUN})


        # Register all services to the scheduler.
        self.Scheduler.ServiceRegister(self.Time)
        self.Scheduler.ServiceRegister(self.NetCon)
        self.Scheduler.ServiceRegister(self.MsgEx)
        self.Scheduler.ServiceRegister(self.MoistSensor)
        self.Scheduler.ServiceRegister(self.Notifyer)
        self.Scheduler.ServiceRegister(self.LightSensor)
        self.Scheduler.ServiceRegister(self.TempSensor)

        # Create message specifications.
        self.TempMsgSpec = SensorReportTemp()
        self.MoistMsgSpec = SensorReportMoist()
        self.LightMsgSpec = SensorReportLight()
        self.LogMsgSpec = LogMessage()

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

        # Register message specs for exchange.
        self.MsgEx.RegisterMessageType(self.TempMsgSpec)
        self.MsgEx.RegisterMessageType(self.MoistMsgSpec)
        self.MsgEx.RegisterMessageType(self.LightMsgSpec)
        self.MsgEx.RegisterMessageType(self.LogMsgSpec)

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

        # Set the notification ranges and colors.
        moist_th_range = NotificationRange(self.MOIST_RANGE_MIN, self.MOIST_RANGE_MAX)
        moist_color_map = {RgbLed.RGB_COLOR_RED: NotificationRange(self.MOIST_RANGE_MAX,
                                                                   self.MOIST_RANGE_MIN),
                           RgbLed.RGB_COLOR_BLUE: NotificationRange(self.MOIST_RANGE_MIN,
                                                                    self.MOIST_RANGE_MAX)}
        self.MoistNotif = Notification(moist_th_range, moist_color_map,
                                       self.MOIST_NOTIF_PRIO,
                                       self.MOIST_NOTIF_TIME)

        self.Notifyer.NotificationRegister(self.MoistNotif)

        # Link the observers to the sensors.
        self.TempSensor.ObserverAttachNewSample(self.TempObserver)
        self.MoistSensor.ObserverAttachNewSample(self.MoistObserver)
        self.MoistSensor.ObserverAttachNewSample(self.MoistNotif)
        self.LightSensor.ObserverAttachNewSample(self.LightObserver)

        # Create a stream for the log messages.
        self.LogStream = self.LogAdapt.CreateStream(LogMessage.DATA_KEY_LOG_MSG,
                                                    ExtLogging.WRITES_PER_LOG)

        # Configure the ExtLogging class.
        ExtLogging.ConfigGlobal(level=ExtLogging.INFO, stream=self.LogStream)

        # Set service modes.
        self.MsgEx.SvcMode =  Service.MODE_RUN_ONCE
        self.TempSensor.SvcMode = Service.MODE_RUN_ONCE
        self.LightSensor.SvcMode = Service.MODE_RUN_ONCE

        # Set intervals for periodic services.
        self.MoistSensor.SvcIntervalSet(self.MoistSensorReadInterval)
        self.Notifyer.SvcIntervalSet(self.NotificationInterval)

    def Run(self):
        # Execute mode run function.
        if DemoApp.Mode is DemoApp.APP_MODE_SCAN:
            self.RunScanMode()
        else:
            self.RunCalibMode()

    def RunScanMode(self):
        self.Button.Disable()

        self.Scheduler.Run(50)

        self.MoistSensor.SvcDisable()
        self.Notifyer.SvcDisable()

        self.MsgEx.SvcActivate()
        self.TempSensor.SvcActivate()
        self.LightSensor.SvcActivate()

        self.Scheduler.Run(15)
        self.Scheduler.RequestDeepSleep(0)

    def RunCalibMode(self):
        while DemoApp.CalibState is not DemoApp.CALIB_STATE_SET_SYNC:
            self.Scheduler.Run(10)

        self.MoistSensor.SvcDisable()
        self.MsgEx.SvcActivate()

        self.Scheduler.Run(15)
        self.Scheduler.RequestDeepSleep(0)

    def Reset(self):
        self.MsgEx.Reset()
        self.TempSensor.SamplesDelete()
        self.MoistSensor.SamplesDelete()
        self.LightSensor.SamplesDelete()
        self.NetCon.StationSettingsReset()

    def ButtonPressed(self, *args):
        self.RgbLed.Green.On()

    def ButtonRelease(self, *args):
        if DemoApp.StartApp is False:
            self.RgbLed.Green.Off()
            hold_index = args[UserButton.CALLBACK_ARG_HOLD_INDEX]
            press_count = args[UserButton.CALLBACK_ARG_PRESS_COUNT]
            if hold_index is -1:
                DemoApp.Mode = DemoApp.APP_MODE_SCAN
            else:
                DemoApp.Mode = DemoApp.APP_MODE_CALIBRATION
                self.RgbLed.Red.On()

            DemoApp.StartApp = True

        # Activate the Message Exchange service to
        # sync the calibration with the server.
        elif DemoApp.StartApp is True and DemoApp.Mode is DemoApp.APP_MODE_CALIBRATION:

            if DemoApp.CalibState is DemoApp.CALIB_STATE_SET_LOW:
                self.RgbLed.Red.Off()
                DemoApp.CalibState = DemoApp.CALIB_STATE_SET_HIGH
                print("[App] Setting low calibration value")
                self.RgbLed.Blue.On()

            elif DemoApp.CalibState is DemoApp.CALIB_STATE_SET_HIGH:
                self.RgbLed.Blue.Off()
                DemoApp.CalibState = DemoApp.CALIB_STATE_SET_SYNC
                print("[App] Setting high calibration value")

            return
            # if calib_low:
            #     self.Calibration.SvcActivate()
            # else:
            #     # Create observer for the high calibration. Replace the low calibration.
            #     self.MoistObserver = self.MoistCalibHighAdapt.CreateObserver(
            #         SensorReportMoistCalibHigh.DATA_KEY_SENSOR_REPORT_SAMPLES,
            #         self.SamplesPerMessage)
            # self.MsgEx.SvcActivate()
