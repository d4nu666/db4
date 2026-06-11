from machine import Pin
import time

relay1 = Pin(17, Pin.OUT)  # fan relay
relay2 = Pin(16, Pin.OUT)  # heating relay

# Active LOW relay:
# 0 = ON / click
# 1 = OFF

relay1.value(1)
relay2.value(1)

print("Simple relay test started")

while True:
    print("Relay 1 ON")
    relay1.value(0)
    relay2.value(1)
    time.sleep(3)

    print("Relay 1 OFF")
    relay1.value(1)
    time.sleep(3)

    print("Relay 2 ON")
    relay1.value(1)
    relay2.value(0)
    time.sleep(3)

    print("Relay 2 OFF")
    relay2.value(1)
    time.sleep(3)

    print("Both OFF")
    relay1.value(1)
    relay2.value(1)
    time.sleep(3)