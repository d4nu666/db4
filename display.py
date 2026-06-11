from machine import Pin, I2C
import ssd1306
import time



i2c = I2C(0, scl=Pin(22), sda=Pin(21), freq=400000)

oled = ssd1306.SSD1306_I2C(128, 64, i2c)

counter = 0

print("OLED display test started")

while True:
    oled.fill(0)

    oled.text("DB4 SYSTEM", 0, 0)
    oled.text("OLED WORKS", 0, 16)
    oled.text("Counter:", 0, 32)
    oled.text(str(counter), 72, 32)

    oled.show()

    print("OLED counter:", counter)

    counter += 1
    time.sleep(1)