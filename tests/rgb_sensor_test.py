from machine import Pin, I2C
import lib.ssd1306 as ssd1306
import time

i2c = I2C(0, scl=Pin(22), sda=Pin(21), freq=100000)

print("Devices:", [hex(x) for x in i2c.scan()])

oled = ssd1306.SSD1306_I2C(128, 64, i2c, addr=0x3c)

oled.fill(0)
oled.text("OLED WORKS", 0, 0)
oled.text("TCS: 0x29", 0, 16)
oled.text("OLED: 0x3c", 0, 28)
oled.show()

while True:
    time.sleep(1)