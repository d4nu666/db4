from machine import Pin
import time

# Use GPIO16 only if it is free
relay1 = Pin(16, Pin.OUT)
relay2 = Pin(17, Pin.OUT)

# Most relay modules are active LOW
ON = 0
OFF = 1

relay1.value(OFF)
relay2.value(OFF)
time.sleep(2)

print("Waste pump ON")
relay1.value(ON)
time.sleep(3)

print("Waste pump OFF")
relay1.value(OFF)