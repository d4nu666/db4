from machine import Pin
import time

RELAY_PIN = 16

relay_ch2 = Pin(RELAY_PIN, Pin.OUT)

# 0 = relay ON
# 1 = relay OFF
RELAY_ON = 0
RELAY_OFF = 1

# Start OFF for safety
relay_ch2.value(RELAY_OFF)

print("Relay channel 2 test started")
print("IN2 connected to GPIO16")
print("Relay should be OFF now")
time.sleep(3)

while True:
    print("Relay channel 2 ON")
    relay_ch2.value(RELAY_ON)
    time.sleep(3)

    print("Relay channel 2 OFF")
    relay_ch2.value(RELAY_OFF)
    time.sleep(3)