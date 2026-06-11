from machine import Pin
import time

relay1 = Pin(16, Pin.OUT)
relay2 = Pin(17, Pin.OUT)

# active LOW relay: 0 = ON, 1 = OFF
relay1.value(1)
relay2.value(1)

print("Relay test running")

while True:
    print("Relay 1 ON")
    relay1.value(0)
    time.sleep(2)

    print("Relay 1 OFF")
    relay1.value(1)
    time.sleep(2)

    print("Relay 2 ON")
    relay2.value(0)
    time.sleep(2)

    print("Relay 2 OFF")
    relay2.value(1)
    time.sleep(2)