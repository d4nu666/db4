from machine import Pin, I2C
import time
import ssd1306

SDA_PIN = 21
SCL_PIN = 22

i2c = I2C(0, scl=Pin(SCL_PIN), sda=Pin(SDA_PIN), freq=100000)

oled = ssd1306.SSD1306_I2C(128, 64, i2c)

counter = 0

print("OLED display test started")

while True:
    oled.fill(0)
    oled.text("DB4 OLED TEST", 0, 0)
    oled.text("SDA: GPIO21", 0, 16)
    oled.text("SCL: GPIO22", 0, 26)
    oled.text("Count: {}".format(counter), 0, 42)
    oled.show()

    print("OLED count:", counter)

    counter += 1
    time.sleep(1)