from machine import Pin, PWM, ADC, I2C
import time
import math
import ssd1306


# =========================
# SETUP HARDWARE
# =========================

fan_relay = Pin(17, Pin.OUT)    # Relay IN1 = fan
heat_relay = Pin(16, Pin.OUT)   # Relay IN2 = heating

# Relay is ACTIVE LOW:
# 0 = ON
# 1 = OFF


# =========================
# OLED + TCS34725 RGB SENSOR
# =========================

i2c = I2C(0, scl=Pin(22), sda=Pin(21), freq=100000)

print("I2C devices:", [hex(x) for x in i2c.scan()])
# Expected: ['0x29', '0x3c']
# 0x29 = TCS34725
# 0x3c = OLED

oled = ssd1306.SSD1306_I2C(128, 64, i2c, addr=0x3c)


# =========================
# TCS34725 RGB SENSOR
# =========================

TCS_ADDR = 0x29
TCS_COMMAND = 0x80

TCS_ENABLE = 0x00
TCS_ATIME = 0x01
TCS_CONTROL = 0x0F
TCS_ID = 0x12

TCS_CDATAL = 0x14
TCS_RDATAL = 0x16
TCS_GDATAL = 0x18
TCS_BDATAL = 0x1A


def tcs_write8(reg, value):
    i2c.writeto_mem(TCS_ADDR, TCS_COMMAND | reg, bytes([value]))


def tcs_read8(reg):
    return i2c.readfrom_mem(TCS_ADDR, TCS_COMMAND | reg, 1)[0]


def tcs_read16(reg):
    data = i2c.readfrom_mem(TCS_ADDR, TCS_COMMAND | reg, 2)
    return data[0] | (data[1] << 8)


def tcs_init():
    try:
        sensor_id = tcs_read8(TCS_ID)
        print("TCS34725 ID:", hex(sensor_id))

        # Integration time around 50 ms
        tcs_write8(TCS_ATIME, 0xEB)

        # Gain:
        # 0x00 = 1x
        # 0x01 = 4x
        # 0x02 = 16x
        # 0x03 = 60x
        tcs_write8(TCS_CONTROL, 0x01)

        # Power ON
        tcs_write8(TCS_ENABLE, 0x01)
        time.sleep(0.01)

        # Enable ADC
        tcs_write8(TCS_ENABLE, 0x03)
        time.sleep(0.1)

        print("TCS34725 initialized")
        return True

    except Exception as e:
        print("TCS34725 init error:", e)
        return False


def read_rgb_sensor():
    try:
        clear = tcs_read16(TCS_CDATAL)
        red = tcs_read16(TCS_RDATAL)
        green = tcs_read16(TCS_GDATAL)
        blue = tcs_read16(TCS_BDATAL)
        return red, green, blue, clear
    except Exception as e:
        print("RGB sensor read error:", e)
        return None, None, None, None


# =========================
# RGB LED
# YOUR TEST PINS
# =========================

# WARNING:
# GPIO25 is also used by pump ENA.
# So red LED and pump ENA share the same pin.
# I keep it because you said do not change pins.

red_led = Pin(25, Pin.OUT)
green_led = Pin(26, Pin.OUT)
blue_led = Pin(27, Pin.OUT)


def rgb_off():
    red_led.value(0)
    green_led.value(0)
    blue_led.value(0)


def rgb_red_only():
    rgb_off()
    red_led.value(1)


def rgb_green_only():
    rgb_off()
    green_led.value(1)


def rgb_blue_only():
    rgb_off()
    blue_led.value(1)


def rgb_white():
    red_led.value(1)
    green_led.value(1)
    blue_led.value(1)


# =========================
# PUMP MOTOR DRIVER
# ORIGINAL PINS - NOT CHANGED
# =========================

INA = Pin(18, Pin.OUT)
INB = Pin(19, Pin.OUT)
ENA = PWM(Pin(25), freq=1000)


def pump_on(speed=900):
    INA.value(1)
    INB.value(0)
    ENA.duty(speed)


def pump_off():
    INA.value(0)
    INB.value(0)
    ENA.duty(0)


# =========================
# THERMISTOR
# ORIGINAL PIN - NOT CHANGED
# =========================

adc = ADC(Pin(34))
adc.atten(ADC.ATTN_11DB)
adc.width(ADC.WIDTH_12BIT)

SERIES_RESISTOR = 10000
THERMISTOR_NOMINAL = 10000
TEMPERATURE_NOMINAL = 25
BETA = 3950


def read_temp_c():
    raw = adc.read()

    if raw <= 0 or raw >= 4095:
        return None, raw

    resistance = SERIES_RESISTOR * raw / (4095 - raw)

    steinhart = resistance / THERMISTOR_NOMINAL
    steinhart = math.log(steinhart)
    steinhart /= BETA
    steinhart += 1.0 / (TEMPERATURE_NOMINAL + 273.15)
    steinhart = 1.0 / steinhart
    temp_c = steinhart - 273.15

    return temp_c, raw


# =========================
# OLED SCREEN
# =========================

def show_screen(pump_state, temp_c, raw, r, g, b, c):
    oled.fill(0)
    oled.text("DB4 SYSTEM", 0, 0)
    oled.text("Fan: ON", 0, 12)
    oled.text("Pump: " + pump_state, 0, 22)

    if temp_c is None:
        oled.text("Temp: ERROR", 0, 32)
        oled.text("ADC:" + str(raw), 0, 42)
    else:
        oled.text("T:" + str(round(temp_c, 1)) + "C ADC:" + str(raw), 0, 32)

    if r is None:
        oled.text("RGB sensor ERR", 0, 52)
    else:
        oled.text("R:" + str(r) + " G:" + str(g), 0, 44)
        oled.text("B:" + str(b) + " C:" + str(c), 0, 54)

    oled.show()


# =========================
# STARTUP TEST
# =========================

def startup_test():
    print("Starting DB4 full test")

    oled.fill(0)
    oled.text("DB4 START", 0, 0)
    oled.text("I2C scan...", 0, 16)
    oled.show()
    time.sleep(1)

    devices = i2c.scan()
    print("I2C devices:", [hex(x) for x in devices])

    oled.fill(0)
    oled.text("I2C devices:", 0, 0)
    oled.text(str([hex(x) for x in devices]), 0, 16)
    oled.show()
    time.sleep(2)

    tcs_init()

    oled.fill(0)
    oled.text("RGB LED TEST", 0, 0)
    oled.text("GREEN", 0, 16)
    oled.show()
    rgb_green_only()
    time.sleep(1)

    oled.fill(0)
    oled.text("RGB LED TEST", 0, 0)
    oled.text("BLUE", 0, 16)
    oled.show()
    rgb_blue_only()
    time.sleep(1)

    oled.fill(0)
    oled.text("RGB LED TEST", 0, 0)
    oled.text("WHITE", 0, 16)
    oled.show()
    rgb_white()
    time.sleep(1)

    rgb_off()


# =========================
# MAIN PROGRAM
# =========================

def run_system():
    startup_test()

    # =========================
    # TURN FAN ON FIRST
    # =========================

    fan_relay.value(0)      # FAN ON immediately
    heat_relay.value(1)     # Heating OFF

    print("Fan relay should be ON now")
    time.sleep(2)

    print("Main program started")

    while True:
        # Keep forcing fan ON
        fan_relay.value(0)
        heat_relay.value(1)

        # Pump ON
        pump_on(1000)

        # Use blue LED for pump ON
        green_led.value(0)
        blue_led.value(1)

        for i in range(5):
            fan_relay.value(0)
            temp_c, raw = read_temp_c()
            r, g, b, c = read_rgb_sensor()

            show_screen("ON", temp_c, raw, r, g, b, c)

            print("Fan ON | Pump ON | Temp:", temp_c, "ADC:", raw,
                  "| RGB sensor:", r, g, b, "Clear:", c)

            time.sleep(1)

        # Pump OFF
        pump_off()

        # Use green LED for pump OFF
        green_led.value(1)
        blue_led.value(0)

        for i in range(5):
            fan_relay.value(0)
            temp_c, raw = read_temp_c()
            r, g, b, c = read_rgb_sensor()

            show_screen("OFF", temp_c, raw, r, g, b, c)

            print("Fan ON | Pump OFF | Temp:", temp_c, "ADC:", raw,
                  "| RGB sensor:", r, g, b, "Clear:", c)

            time.sleep(1)


# This lets you run main.py directly too
if __name__ == "__main__":
    run_system()