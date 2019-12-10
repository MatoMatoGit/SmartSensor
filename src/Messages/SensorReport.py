from upyiot.comm.Messaging.MessageSpecification import MessageSpecification
from micropython import const


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


class SensorReportLight(SensorReport):

    NAME_LIGHT = "light"
    SUBTYPE_LIGHT = const(3)

    def __init__(self):
        super().__init__(SensorReportMoist.SUBTYPE_LIGHT, SensorReportMoist.NAME_LIGHT)


class SensorReportVBat(SensorReport):

    NAME_VBAT = "vbat"
    SUBTYPE_VBAT = const(4)

    def __init__(self):
        super().__init__(SensorReportMoist.SUBTYPE_VBAT, SensorReportMoist.NAME_VBAT)

