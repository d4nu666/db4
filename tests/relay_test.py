from machine import Pin
import time

RELAY_PIN = 16

relay = Pin(RELAY_PIN, Pin.OUT)

RELAY_OFF = 0
RELAY_ON = 1

print("Peltier relay test started")
print("GPIO16 controls relay IN1")

while True:
    relay.value(RELAY_ON)
    print("Relay ON - Peltier should be ON")
    #time.sleep(3)

    #relay.value(RELAY_OFF)
    #print("Relay OFF - Peltier should be OFF")
    #time.sleep(3)