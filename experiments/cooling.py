from machine import Pin, PWM, ADC, I2C
import time
import math
import sys

sys.path.append("/experiments")

import ssd1306

# ==================================================
# DB4 TEMPERATURE COOLING TEST
# Saves temperature data to cooling_test.csv on ESP32
# ==================================================

LOG_FILE = "cooling_test.csv"

# ==================================================
# PIN SETUP - based on your current working wiring
# ==================================================

# Cooling / fan relay on GPIO16
# IMPORTANT: choose relay logic here.
# In your latest test_main.py you used: 1 = ON, 0 = OFF
RELAY_ON = 1
RELAY_OFF = 0
fan_relay = Pin(16, Pin.OUT)

# L298N pump motor driver
# IN1 -> GPIO18
# IN2 -> GPIO19
# ENA -> GPIO32
INA = Pin(18, Pin.OUT)
INB = Pin(19, Pin.OUT)
ENA = PWM(Pin(32), freq=1000)

# Thermistor ADC
TEMP_ADC_PIN = 12
temp_adc = ADC(Pin(TEMP_ADC_PIN))
temp_adc.atten(ADC.ATTN_11DB)
temp_adc.width(ADC.WIDTH_12BIT)

# OLED on I2C
# SDA -> GPIO21
# SCL -> GPIO22
i2c = I2C(0, scl=Pin(22), sda=Pin(21), freq=400000)
oled = ssd1306.SSD1306_I2C(128, 64, i2c)

# ==================================================
# TEST SETTINGS
# ==================================================

TARGET_TEMP = 18.0

# From your pump calibration:
# PWM 500 is about 241 mL/min
PUMP_SPEED = 1023

MAX_TEST_TIME = 20 * 60      # 20 minutes
SAMPLE_INTERVAL = 2          # seconds

# Thermistor parameters
SERIES_RESISTOR = 10000
NOMINAL_RESISTANCE = 10000
NOMINAL_TEMP = 25
BETA = 3950
ADC_MAX = 4095

# Pump boost helps the pump start reliably
PUMP_START_BOOST = True
PUMP_BOOST_TIME = 1.0


# ==================================================
# FAN / COOLING FUNCTIONS
# ==================================================

def fan_on():
    fan_relay.value(RELAY_ON)


def fan_off():
    fan_relay.value(RELAY_OFF)


# ==================================================
# PUMP FUNCTIONS
# ==================================================

def pump_on(speed=PUMP_SPEED):
    speed = max(0, min(1023, speed))

    INA.value(1)
    INB.value(0)

    if PUMP_START_BOOST and speed > 0:
        ENA.duty(1023)
        time.sleep(PUMP_BOOST_TIME)

    ENA.duty(speed)


def pump_off():
    ENA.duty(0)
    INA.value(0)
    INB.value(0)


def pump_set_speed(speed):
    speed = max(0, min(1023, speed))
    INA.value(1)
    INB.value(0)
    ENA.duty(speed)


# ==================================================
# TEMPERATURE FUNCTIONS
# ==================================================

def read_temp_c():
    raw = temp_adc.read()

    if raw <= 0 or raw >= ADC_MAX:
        return None, raw

    try:
        # Same thermistor equation style as your earlier main.py
        resistance = SERIES_RESISTOR * raw / (ADC_MAX - raw)

        steinhart = resistance / NOMINAL_RESISTANCE
        steinhart = math.log(steinhart)
        steinhart /= BETA
        steinhart += 1.0 / (NOMINAL_TEMP + 273.15)
        steinhart = 1.0 / steinhart

        temp_c = steinhart - 273.15
        return temp_c, raw

    except Exception:
        return None, raw


def read_temp_average(samples=8):
    values = []
    raw_values = []

    for i in range(samples):
        temp, raw = read_temp_c()
        raw_values.append(raw)
        if temp is not None:
            values.append(temp)
        time.sleep_ms(30)

    avg_raw = sum(raw_values) / len(raw_values)

    if len(values) == 0:
        return None, avg_raw

    return sum(values) / len(values), avg_raw


# ==================================================
# OLED FUNCTIONS
# ==================================================

def show_screen(elapsed, temp, raw, fan_state, pump_speed):
    oled.fill(0)
    oled.text("COOLING TEST", 0, 0)
    oled.text("Time:{}s".format(elapsed), 0, 12)

    if temp is None:
        oled.text("Temp: ERROR", 0, 24)
    else:
        oled.text("Temp:{:.1f}C".format(temp), 0, 24)

    oled.text("ADC:{}".format(int(raw)), 0, 36)
    oled.text("Fan:" + fan_state, 0, 48)
    oled.text("Pump:{}".format(pump_speed), 64, 48)
    oled.show()


def show_stop_screen(message):
    oled.fill(0)
    oled.text(message, 0, 8)
    oled.text("Fan OFF", 0, 24)
    oled.text("Pump OFF", 0, 40)
    oled.show()


# ==================================================
# CSV FUNCTIONS
# ==================================================

def create_log_file():
    with open(LOG_FILE, "w") as f:
        f.write("time_s,temp_c,adc_raw,fan_state,pump_speed,target_temp\n")
    print("Created log file:", LOG_FILE)


def log_data(elapsed, temp, raw, fan_state, pump_speed):
    with open(LOG_FILE, "a") as f:
        f.write("{},{},{},{},{},{}\n".format(
            elapsed,
            temp,
            raw,
            fan_state,
            pump_speed,
            TARGET_TEMP
        ))


# ==================================================
# MAIN TEST
# ==================================================

def run_cooling_test():
    print("")
    print("===================================")
    print("TEMPERATURE COOLING TEST STARTED")
    print("===================================")
    print("Relay GPIO16 | relay ON value:", RELAY_ON)
    print("Pump IN1 GPIO18 | IN2 GPIO19 | ENA GPIO32")
    print("Thermistor GPIO34")
    print("Pump speed:", PUMP_SPEED)
    print("Target temp:", TARGET_TEMP, "C")
    print("Data saved to:", LOG_FILE)
    print("")

    fan_off()
    pump_off()
    time.sleep(1)

    create_log_file()

    print("Starting pump at PWM:", PUMP_SPEED)
    pump_on(PUMP_SPEED)

    start_time = time.time()

    while True:
        elapsed = int(time.time() - start_time)
        temp, raw = read_temp_average()

        if elapsed >= MAX_TEST_TIME:
            print("Max test time reached. Stopping.")
            fan_off()
            pump_off()
            show_stop_screen("STOP TIME")
            break

        if temp is not None and temp > TARGET_TEMP:
            fan_on()
            fan_state = "ON"
        else:
            fan_off()
            fan_state = "OFF"

        pump_set_speed(PUMP_SPEED)

        show_screen(elapsed, temp, raw, fan_state, PUMP_SPEED)
        log_data(elapsed, temp, raw, fan_state, PUMP_SPEED)

        print("Time:", elapsed,
              "s | Temp:", temp,
              "C | ADC:", raw,
              "| Fan:", fan_state,
              "| Pump:", PUMP_SPEED)

        time.sleep(SAMPLE_INTERVAL)


try:
    run_cooling_test()

except KeyboardInterrupt:
    print("Stopped by user")

finally:
    fan_off()
    pump_off()

    try:
        show_stop_screen("STOPPED")
    except Exception:
        pass

    print("System stopped safely.")
    print("CSV file:", LOG_FILE)

