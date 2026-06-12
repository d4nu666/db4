from machine import Pin
import time

red = Pin(25, Pin.OUT)
green = Pin(26, Pin.OUT)
blue = Pin(27, Pin.OUT)

def off():
    red.value(0)
    green.value(0)
    blue.value(0)

while True:
    off()
    red.value(1)
    time.sleep(1)

    off()
    green.value(1)
    time.sleep(1)

    off()
    blue.value(1)
    time.sleep(1)

    off()
    red.value(1)
    green.value(1)
    blue.value(1)   # white-ish
    time.sleep(1)