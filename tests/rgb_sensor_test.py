from machine import Pin, I2C
import time

SDA_PIN = 21
SCL_PIN = 22
TCS34725_ADDR = 0x29

i2c = I2C(0, scl=Pin(SCL_PIN), sda=Pin(SDA_PIN), freq=100000)

print("OD sensor detect test started")
print("Looking for TCS34725 at address 0x29")

while True:
    devices = i2c.scan()

    if TCS34725_ADDR in devices:
        print("OD sensor found at 0x29")
    else:
        print("OD sensor NOT found. Devices:", [hex(d) for d in devices])

    time.sleep(1)