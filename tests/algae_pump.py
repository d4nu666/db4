from machine import Pin
import time

ALGAE_IN1 = Pin(23, Pin.OUT)
ALGAE_IN2 = Pin(14, Pin.OUT)

def algae_pump_on():
    ALGAE_IN1.value(1)
    ALGAE_IN2.value(0)

def algae_pump_off():
    ALGAE_IN1.value(0)
    ALGAE_IN2.value(0)

while True:
    print("Algae pump ON full speed")
    algae_pump_on()
    time.sleep(5)

    print("Algae pump OFF")
    algae_pump_off()
    time.sleep(5)