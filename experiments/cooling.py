# ==================================================
# DB4 COOLING TEST - PUMP SPEED VARIATION
# Tests how pump speed affects cooling performance
#
# Output CSV:
# /code/pump_speed_cooling_test.csv
#
# Hardware:
# Thermistor: GPIO12
# Cooling relay: GPIO16
# Pump L298N:
#   IN1 -> GPIO18
#   IN2 -> GPIO19
#   ENA -> GPIO32 PWM
# OLED:
#   SDA -> GPIO21
#   SCL -> GPIO22
# ==================================================

from machine import Pin, PWM, ADC, I2C
import time
import math
import os
import sys

# ==================================================
# FOLDER SETUP
# ==================================================

try:
    os.chdir("/code")
except:
    pass

sys.path.append("/code")

import ssd1306


# ==================================================
# TEST SETTINGS
# ==================================================

LOG_FILE = "pump_speed_cooling_test.csv"

# Pump speeds to test
# You can change these values
PUMP_SPEEDS = [300, 500, 700, 900, 1023]

# How long each pump speed runs
# Start with 3 minutes for testing.
# Use 10 minutes for better data.
STAGE_DURATION_S = 3 * 60

# Time between temperature measurements
SAMPLE_INTERVAL_S = 2

# Safety temperature
# Cooling will turn OFF if water reaches this temperature
MIN_SAFE_TEMP = 18.0

# Thermistor pin
# GPIO34 is damaged. Use GPIO12.
TEMP_ADC_PIN = 12

# Cooling relay pin
COOLING_RELAY_PIN = 16

# Your latest relay logic:
# 1 = ON
# 0 = OFF
RELAY_ON = 1
RELAY_OFF = 0

# Pump L298N pins
PUMP_INA_PIN = 18
PUMP_INB_PIN = 19
PUMP_PWM_PIN = 32

# OLED I2C pins
I2C_SDA_PIN = 21
I2C_SCL_PIN = 22


# ==================================================
# HARDWARE SETUP
# ==================================================

cooling_relay = Pin(COOLING_RELAY_PIN, Pin.OUT)
cooling_relay.value(RELAY_OFF)

INA = Pin(PUMP_INA_PIN, Pin.OUT)
INB = Pin(PUMP_INB_PIN, Pin.OUT)
ENA = PWM(Pin(PUMP_PWM_PIN), freq=1000)

temp_adc = ADC(Pin(TEMP_ADC_PIN))
temp_adc.atten(ADC.ATTN_11DB)
temp_adc.width(ADC.WIDTH_12BIT)

i2c = I2C(
    0,
    scl=Pin(I2C_SCL_PIN),
    sda=Pin(I2C_SDA_PIN),
    freq=400000
)

oled = ssd1306.SSD1306_I2C(128, 64, i2c)


# ==================================================
# THERMISTOR SETTINGS
# Adafruit 10K NTC thermistor
#
# Wiring assumed:
# 3.3V --- 10k resistor --- GPIO12 --- thermistor --- GND
# ==================================================

SERIES_RESISTOR = 10000.0
NOMINAL_RESISTANCE = 10000.0
NOMINAL_TEMP_C = 25.0
BETA = 3950.0
ADC_MAX = 4095.0


# ==================================================
# HARDWARE FUNCTIONS
# ==================================================

def pump_on(pwm_value):
    INA.value(1)
    INB.value(0)
    ENA.duty(pwm_value)


def pump_off():
    ENA.duty(0)
    INA.value(0)
    INB.value(0)


def cooling_on():
    cooling_relay.value(RELAY_ON)


def cooling_off():
    cooling_relay.value(RELAY_OFF)


def stop_everything():
    cooling_off()
    pump_off()

    try:
        oled.fill(0)
        oled.text("TEST FINISHED", 0, 0)
        oled.text("Cooling OFF", 0, 18)
        oled.text("Pump OFF", 0, 32)
        oled.show()
    except:
        pass

    print("Everything stopped safely.")


# ==================================================
# TEMPERATURE FUNCTION
# ==================================================

def read_temperature():
    total = 0
    samples = 20

    for i in range(samples):
        total += temp_adc.read()
        time.sleep_ms(5)

    raw = total / samples

    if raw <= 0 or raw >= ADC_MAX:
        return None, raw

    resistance = SERIES_RESISTOR * raw / (ADC_MAX - raw)

    steinhart = resistance / NOMINAL_RESISTANCE
    steinhart = math.log(steinhart)
    steinhart = steinhart / BETA
    steinhart = steinhart + (1.0 / (NOMINAL_TEMP_C + 273.15))
    steinhart = 1.0 / steinhart

    temp_c = steinhart - 273.15

    return temp_c, raw


# ==================================================
# OLED DISPLAY
# ==================================================

def update_oled(stage_index, pump_pwm, temp, elapsed_s, stage_time_s, cooling_state):
    oled.fill(0)

    oled.text("Cooling Test", 0, 0)
    oled.text("Stage: %d/%d" % (stage_index + 1, len(PUMP_SPEEDS)), 0, 12)
    oled.text("Pump: %d" % pump_pwm, 0, 24)

    if temp is None:
        oled.text("Temp: ERROR", 0, 36)
    else:
        oled.text("Temp: %.2f C" % temp, 0, 36)

    if cooling_state:
        oled.text("Cool: ON", 0, 50)
    else:
        oled.text("Cool: OFF", 0, 50)

    oled.show()


# ==================================================
# CSV LOGGING
# ==================================================

def create_log_file():
    with open(LOG_FILE, "w") as f:
        f.write(
            "time_s,stage,stage_time_s,pump_pwm,temp_c,raw_adc,cooling_on,notes\n"
        )


def log_data(time_s, stage, stage_time_s, pump_pwm, temp_c, raw_adc, cooling_state, notes):
    with open(LOG_FILE, "a") as f:
        f.write("{},{},{},{},{},{},{},{}\n".format(
            time_s,
            stage,
            stage_time_s,
            pump_pwm,
            temp_c if temp_c is not None else "",
            raw_adc,
            1 if cooling_state else 0,
            notes
        ))


# ==================================================
# MAIN COOLING TEST
# ==================================================

def main():
    print("====================================")
    print("DB4 COOLING TEST STARTED")
    print("Testing pump speeds:", PUMP_SPEEDS)
    print("Stage duration:", STAGE_DURATION_S, "seconds")
    print("CSV file:", LOG_FILE)
    print("Thermistor: GPIO", TEMP_ADC_PIN)
    print("====================================")

    create_log_file()

    start_time = time.time()

    try:
        for stage_index, pump_pwm in enumerate(PUMP_SPEEDS):
            print("")
            print("====================================")
            print("Starting stage", stage_index + 1)
            print("Pump PWM:", pump_pwm)
            print("====================================")

            pump_on(pump_pwm)
            stage_start = time.time()

            while True:
                now = time.time()
                elapsed_s = int(now - start_time)
                stage_time_s = int(now - stage_start)

                if stage_time_s >= STAGE_DURATION_S:
                    break

                temp, raw = read_temperature()

                # Safety logic:
                # Cooling ON while temperature is above 18 C.
                # Cooling OFF at or below 18 C.
                if temp is not None and temp > MIN_SAFE_TEMP:
                    cooling_on()
                    cooling_state = True
                    notes = "cooling"
                else:
                    cooling_off()
                    cooling_state = False
                    notes = "target_reached"

                update_oled(
                    stage_index,
                    pump_pwm,
                    temp,
                    elapsed_s,
                    stage_time_s,
                    cooling_state
                )

                log_data(
                    elapsed_s,
                    stage_index + 1,
                    stage_time_s,
                    pump_pwm,
                    temp,
                    raw,
                    cooling_state,
                    notes
                )

                print(
                    "Time: %ds | Stage: %d | Pump PWM: %d | Temp: %s C | Cooling: %s" % (
                        elapsed_s,
                        stage_index + 1,
                        pump_pwm,
                        "%.2f" % temp if temp is not None else "ERROR",
                        "ON" if cooling_state else "OFF"
                    )
                )

                time.sleep(SAMPLE_INTERVAL_S)

            print("Stage", stage_index + 1, "finished.")

        print("")
        print("All pump speed stages finished.")

    except KeyboardInterrupt:
        print("Cooling test stopped by user.")

    finally:
        stop_everything()


# ==================================================
# AUTO START
# ==================================================

main()