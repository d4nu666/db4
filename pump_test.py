from machine import Pin
import time


INA = Pin(18, Pin.OUT)
INB = Pin(19, Pin.OUT)

ON_TIME = 5
OFF_TIME = 3

def pump_forward():
    INA.value(1)
    INB.value(0)

def pump_reverse():
    INA.value(0)
    INB.value(1)

def pump_stop():
    INA.value(0)
    INB.value(0)

print("Pump full speed test started")
print("ENA connected to 5V = full speed")

while True:
    print("Pump ON full speed")
    pump_forward()
    time.sleep(ON_TIME)

    print("Pump OFF")
    pump_stop()
    time.sleep(OFF_TIME)

    
    # print("Pump reverse full speed")
    # pump_reverse()
    # time.sleep(ON_TIME)
    # pump_stop()
    # time.sleep(OFF_TIME)