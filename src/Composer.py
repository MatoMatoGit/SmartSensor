
# Drivers
from lib import Led
from lib import RgbLed
from lib import Battery

# Middleware
from lib import Sensor
from lib import DummySensor

# Comm
from lib import NetCon

# Modules
from lib import Notifyer
from lib import Power
from lib import SensorDaq
from lib import SystemTime

# uPy
import ujson
import machine
import ubinascii


class Composer(object):
    
    
    BATTERY_SAMPLES = [range(4.2, 3, -0.1)]
    TEMPERATURE_SAMPES = [20, 21, 25, 30, 35, 35, 20, 12, 10, 40]
    MOISTURE_SAMPLES = [20, 21, 25, 30, 35, 35, 20, 12, 10, 40]
    LIGHT_SAMPLES = [20, 21, 25, 30, 35, 35, 20, 12, 10, 40]
    
    def __init__(self):
        return 0
    
    
    def Execute(self):
        
        # Load the config file
        f = open('config.json', 'r')
        cfg = ujson.load(f)
        print('\nLoaded sensor config file:\n')
        print(cfg)
        
        # Read the Device ID
        self.DeviceId = str(ubinascii.hexlify(machine.unique_id()).decode('utf-8'))
        
        # Create Sensor instances
        self.SensorBattery = DummySensor(Composer.BATTERY_SAMPLES)
        self.SensorMoisture = DummySensor(Composer.MOISTURE_SAMPLES)
        self.SensorTemp = DummySensor(Composer.TEMPERATURE_SAMPES)
        self.SensorLight = DummySensor(Composer.LIGHT_SAMPLES)
        
        self.SensorBattery = Sensor.Sensor("/sensors", "batt", 50, self.SensorBattery)
        self.SensorMoisture = Sensor.Sensor("/sensors", "moist", 30, self.SensorMoisture)
        self.SensorTemp = Sensor.Sensor("/sensors", "temp", 30, self.SensorTemp)
        self.SensorLight = Sensor.Sensor("/sensors", "light", 30, self.SensorLight)     
             
        # Create Driver instances
        self.RgbLed = RgbLed(Led(0, True), Led(1, True),Led(2, True))
        self.Battery = Battery(1, self.SensorBattery)        

        # Create Module instances
        self.Notifyer = Notifyer(self.Mapping, self.RgbLed)
        self.Power = Power(25)
        self.SystemTime = SystemTime()
        
        # Create Comm instances
        self.NetCon = NetCon.NetCon("/", (cfg["ap"]["ssid_prefix"] + self.DeviceId + cfg["ap"]["ssid_suffix"], 
                                          cfg["ap"]["pw"], cfg["ap"]["ip"]), True)
        
        # Create connections between components
        self.SensorMoisture.ObserverAttachNewSample(self.Notifyer.MoistureObserver())
        
        self.Battery.ObserverAttachLevel(self.Power.BatteryObserver())
        
        
    
        
        
        
        
        