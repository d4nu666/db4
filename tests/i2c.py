from machine import Pin, I2C
import time

i2c = I2C(0, scl=Pin(22), sda=Pin(21), freq=100000)

while True:
    devices = i2c.scan()
    print("I2C devices:", [hex(d) for d in devices])
    time.sleep(1)