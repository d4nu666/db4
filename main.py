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
# OLED
# =========================

i2c = I2C(0, scl=Pin(22), sda=Pin(21), freq=400000)
oled = ssd1306.SSD1306_I2C(128, 64, i2c)

# =========================
# PUMP MOTOR DRIVER
# =========================

INA = Pin(18, Pin.OUT)
INB = Pin(19, Pin.OUT)
ENA = PWM(Pin(25), freq=1000)

# =========================
# THERMISTOR
# =========================

adc = ADC(Pin(34))
adc.atten(ADC.ATTN_11DB)
adc.width(ADC.WIDTH_12BIT)

SERIES_RESISTOR = 10000
THERMISTOR_NOMINAL = 10000
TEMPERATURE_NOMINAL = 25
BETA = 3950


def pump_on(speed=900):
    INA.value(1)
    INB.value(0)
    ENA.duty(speed)


def pump_off():
    INA.value(0)
    INB.value(0)
    ENA.duty(0)


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


def show_screen(pump_state, temp_c, raw):
    oled.fill(0)
    oled.text("DB4 SYSTEM", 0, 0)
    oled.text("Fan: ON", 0, 16)
    oled.text("Pump: " + pump_state, 0, 28)

    if temp_c is None:
        oled.text("Temp: ERROR", 0, 42)
        oled.text("ADC: " + str(raw), 0, 54)
    else:
        oled.text("Temp: " + str(round(temp_c, 1)) + " C", 0, 42)
        oled.text("ADC: " + str(raw), 0, 54)

    oled.show()


def run_system():
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

        for i in range(5):
            fan_relay.value(0)
            temp_c, raw = read_temp_c()
            show_screen("ON", temp_c, raw)
            print("Fan ON | Pump ON | Temp:", temp_c, "ADC:", raw)
            time.sleep(1)

        # Pump OFF
        pump_off()

        for i in range(5):
            fan_relay.value(0)
            temp_c, raw = read_temp_c()
            show_screen("OFF", temp_c, raw)
            print("Fan ON | Pump OFF | Temp:", temp_c, "ADC:", raw)
            time.sleep(1)


# This lets you run main.py directly too
if __name__ == "__main__":
    run_system()