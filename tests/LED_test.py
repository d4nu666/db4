from machine import Pin
import time

RED_PIN = 27
GREEN_PIN = 26
BLUE_PIN = 25

red = Pin(RED_PIN, Pin.OUT)
green = Pin(GREEN_PIN, Pin.OUT)
blue = Pin(BLUE_PIN, Pin.OUT)

def off():
    red.value(0)
    green.value(0)
    blue.value(0)

print("HW-479 RGB LED test started")

while True:
    off()
    red.value(1)
    print("RED")
    time.sleep(1)

    off()
    green.value(1)
    print("GREEN")
    time.sleep(1)

    off()
    blue.value(1)
    print("BLUE")
    time.sleep(1)

    off()
    red.value(1)
    green.value(1)
    blue.value(1)
    print("WHITE")
    time.sleep(1)

    off()
    print("OFF")
    time.sleep(1)