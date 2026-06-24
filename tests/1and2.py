from machine import Pin
import time


ALGAE_PIN = 23
WASTE_PIN = 19

algae_pump = Pin(ALGAE_PIN, Pin.OUT)
waste_pump = Pin(WASTE_PIN, Pin.OUT)


# 1 = pump ON
# 0 = pump OFF
ON = 0
OFF = 1

def algae_on():
    algae_pump.value(ON)

def algae_off():
    algae_pump.value(OFF)

def waste_on():
    waste_pump.value(ON)

def waste_off():
    waste_pump.value(OFF)

def stop_all_pumps():
    algae_off()
    waste_off()


print("Algae pump ON")
algae_on()
time.sleep(3)

print("Algae pump OFF")
algae_off()
time.sleep(2)

print("Waste pump ON")
waste_on()
time.sleep(3)

print("Waste pump OFF")
waste_off()
time.sleep(2)

print("Both pumps ON")
algae_on()
waste_on()
time.sleep(3)

print("STOP ALL")
stop_all_pumps()