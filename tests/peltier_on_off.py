from machine import Pin
import time

# Change these if your relay inputs are on different GPIOs
RELAY1_PIN = 16
RELAY2_PIN = 17

# Most relay modules are active LOW:
# 0 = ON, 1 = OFF
RELAY_ON = 0
RELAY_OFF = 1

relay1 = Pin(RELAY1_PIN, Pin.OUT)
relay2 = Pin(RELAY2_PIN, Pin.OUT)

def all_off():
    relay1.value(RELAY_OFF)
    relay2.value(RELAY_OFF)

all_off()
time.sleep(2)

print("Relay channel test started")
print("Watch which device turns on")

while True:
    print("\nRelay 1 ON for 5 seconds")
    relay1.value(RELAY_ON)
    relay2.value(RELAY_OFF)
    time.sleep(5)

    print("All OFF for 5 seconds")
    all_off()
    time.sleep(5)

    print("\nRelay 2 ON for 5 seconds")
    relay1.value(RELAY_OFF)
    relay2.value(RELAY_ON)
    time.sleep(5)

    print("All OFF for 5 seconds")
    all_off()
    time.sleep(5)