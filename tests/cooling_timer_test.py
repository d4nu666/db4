from machine import Pin, PWM, ADC, I2C
import time
import math
import sys

# ==================================================
# DB4 TIMER COOLING TEST
# OLED shows ONLY:
#   Temperature
#   Time
# ==================================================

# -----------------------------
# OLED LIBRARY
# -----------------------------
try:
    import ssd1306
except ImportError:
    sys.path.append("/firmware/lib")
    import ssd1306

# ==================================================
# TEST SETTINGS
# ==================================================

TEST_DURATION_MINUTES = 60      # change this to 10, 30, 60, etc.
SAMPLE_TIME_SECONDS = 2

TARGET_TEMP = 18.0              # only for reference, not PID here

# ==================================================
# PIN SETUP - NEW PINS
# ==================================================

# Thermistor
THERMISTOR_PIN = 12

# Cooling pump
# New setup: only PWM GPIO32, no IN1/IN2
COOLING_PUMP_PWM_PIN = 32

# Peltier / cooling relay
PELTIER_RELAY_PIN = 16

# OLED
OLED_SDA = 21
OLED_SCL = 22

# Safety: keep biological pumps OFF during cooling test
ALGAE_PUMP_PIN = 23
WASTE_PUMP_PIN = 19

# ==================================================
# RELAY LOGIC
# ==================================================
# Most relay modules are ACTIVE LOW:
# 0 = ON
# 1 = OFF
#
# If your relay works reversed, swap these:
RELAY_ON = 0
RELAY_OFF = 1

# ==================================================
# PWM SETTINGS
# ==================================================

PUMP_FREQ = 1000
PUMP_PWM_VALUE = 800      # 0 to 1023. Use 700-900 for strong cooling flow.

# ==================================================
# THERMISTOR SETTINGS
# ==================================================

SERIES_RESISTOR = 10000
NOMINAL_RESISTANCE = 10000
NOMINAL_TEMPERATURE = 25
BETA = 3950
ADC_MAX = 4095

# ==================================================
# HARDWARE INIT
# ==================================================

# Relay
peltier_relay = Pin(PELTIER_RELAY_PIN, Pin.OUT)
peltier_relay.value(RELAY_OFF)

# Cooling pump PWM
cooling_pump = PWM(Pin(COOLING_PUMP_PWM_PIN), freq=PUMP_FREQ)
cooling_pump.duty(0)

# Biological pumps OFF
algae_pump = Pin(ALGAE_PUMP_PIN, Pin.OUT)
waste_pump = Pin(WASTE_PUMP_PIN, Pin.OUT)
algae_pump.value(0)
waste_pump.value(0)

# Thermistor ADC
adc = ADC(Pin(THERMISTOR_PIN))
adc.atten(ADC.ATTN_11DB)
adc.width(ADC.WIDTH_12BIT)

# OLED
i2c = I2C(0, scl=Pin(OLED_SCL), sda=Pin(OLED_SDA), freq=400000)
oled = ssd1306.SSD1306_I2C(128, 64, i2c)

# ==================================================
# FUNCTIONS
# ==================================================

def stop_everything():
    cooling_pump.duty(0)
    peltier_relay.value(RELAY_OFF)
    algae_pump.value(0)
    waste_pump.value(0)

def read_raw_average(samples=20):
    total = 0
    for _ in range(samples):
        total += adc.read()
        time.sleep_ms(5)
    return total // samples

def read_temperature():
    raw = read_raw_average()

    if raw <= 0 or raw >= ADC_MAX:
        return None

    resistance = SERIES_RESISTOR * raw / (ADC_MAX - raw)

    steinhart = resistance / NOMINAL_RESISTANCE
    steinhart = math.log(steinhart)
    steinhart /= BETA
    steinhart += 1.0 / (NOMINAL_TEMPERATURE + 273.15)
    steinhart = 1.0 / steinhart
    temp_c = steinhart - 273.15

    return temp_c

def format_time(seconds):
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    return "{:02d}:{:02d}:{:02d}".format(hours, minutes, secs)

def update_oled(temp, elapsed_seconds):
    oled.fill(0)

    oled.text("DB4 Cooling Test", 0, 0)

    if temp is None:
        oled.text("Temp: ERROR", 0, 22)
    else:
        oled.text("Temp: {:.2f} C".format(temp), 0, 22)

    oled.text("Time: " + format_time(elapsed_seconds), 0, 42)

    oled.show()

# ==================================================
# MAIN TEST
# ==================================================

try:
    print("DB4 timer cooling test started")
    print("Duration:", TEST_DURATION_MINUTES, "minutes")
    print("Thermistor GPIO:", THERMISTOR_PIN)
    print("Cooling pump PWM GPIO:", COOLING_PUMP_PWM_PIN)
    print("Peltier relay GPIO:", PELTIER_RELAY_PIN)

    oled.fill(0)
    oled.text("Cooling test", 0, 0)
    oled.text("Starting...", 0, 25)
    oled.show()
    time.sleep(2)

    # Start cooling
    peltier_relay.value(RELAY_ON)
    cooling_pump.duty(PUMP_PWM_VALUE)

    start_time = time.time()
    duration_seconds = TEST_DURATION_MINUTES * 60

    while True:
        now = time.time()
        elapsed = now - start_time

        if elapsed >= duration_seconds:
            break

        temp = read_temperature()
        update_oled(temp, elapsed)

        if temp is None:
            print("Time:", format_time(elapsed), "| Temp: ERROR")
        else:
            print("Time:", format_time(elapsed), "| Temp:", round(temp, 2), "C")

        time.sleep(SAMPLE_TIME_SECONDS)

    stop_everything()

    oled.fill(0)
    oled.text("Cooling test", 0, 0)
    oled.text("Finished", 0, 25)
    oled.text("Time: " + format_time(duration_seconds), 0, 45)
    oled.show()

    print("Cooling test finished. Everything stopped.")

except KeyboardInterrupt:
    stop_everything()
    oled.fill(0)
    oled.text("Test stopped", 0, 0)
    oled.text("Everything OFF", 0, 25)
    oled.show()
    print("Stopped manually. Everything OFF.")

except Exception as e:
    stop_everything()
    oled.fill(0)
    oled.text("ERROR", 0, 0)
    oled.text("Everything OFF", 0, 25)
    oled.show()
    print("Error:", e)
    print("Everything OFF.")