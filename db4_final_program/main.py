# ============================================================
# DB4 FINAL MAIN.PY
# Integrated mussel/algae system:
#   - Keeps mussel tank at 18 C using cooling PID
#   - Reads OD from circulation/cooling tube
#   - Feeds mussels from a second algae tank at 5000 cells/mL
#   - Uses a separate algae pump on GPIO23/GPIO14/GPIO33
#   - Logs all data to CSV
#
# Put these files in the ROOT of the ESP32:
#   main.py, pid.py, od_sensor.py, ssd1306.py
# ============================================================

from machine import Pin, PWM, ADC, I2C
import time
import math
import os
import sys

sys.path.append("/")

import ssd1306
from pid import CoolingPID
from od_sensor import TCS34725, RGBLight, ODSensor, AlgaeODModel

# ============================================================
# MAIN SETTINGS
# ============================================================

TARGET_TEMP_C = 18.0
RUN_TIME_S = 6 * 60 * 60          # 6 hours
SAMPLE_INTERVAL_S = 2             # temperature loop interval
OD_INTERVAL_S = 20                 # OD is slower because it averages many readings
LOG_FILE = "db4_final_log.csv"

# Temperature PID values tuned from your cooling behaviour.
Kp = 45.0
Ki = 0.006
Kd = 0.0
DEADBAND_C = 0.2
CONTROL_WINDOW_S = 30

COOL_PUMP_MIN_PWM = 500
COOL_PUMP_MAX_PWM = 1023

# ============================================================
# ALGAE / MUSSEL FEEDING MODEL
# ============================================================

# Your second tank concentration.
ALGAE_STOCK_CELLS_ML = 5000.0

# Best practical mussel tank range from the filtration data.
# Keep tank near 2500 cells/mL, feed below 2000, stop above 3000.
TARGET_CELLS_ML = 2500.0
LOW_CELLS_ML = 2000.0
HIGH_CELLS_ML = 3000.0
TANK_VOLUME_ML = 1000.0

# From your data: around 1000 cells/mL/hour are removed near 2k-3k range.
MUSSEL_CONSUMPTION_CELLS_ML_H = 1000.0

# Your 5k algae OD test gave OD_mean around 0.030.
OD_AT_5000_CELLS_ML = 0.030

# Since stock is only 5k cells/mL, replacing 1000 cells/mL/hour in 1L needs:
# 1000 * 1000 / 5000 = 200 mL/hour.
# Dose in smaller pulses instead of one big dose.
FEED_INTERVAL_S = 15 * 60          # do not feed more often than every 15 min
FEED_DOSE_ML = 50.0                # 50 mL every 15 min = about 200 mL/hour
MAX_DOSE_ML = 50.0                 # safety limit per dose

# IMPORTANT: calibrate this for the NEW algae pump.
# Example calibration: run pump 30 s, measure mL, flow = mL * 2.
# Change this value after testing your algae pump.
ALGAE_PUMP_PWM = 800
ALGAE_PUMP_FLOW_ML_MIN = 100.0

# ============================================================
# PIN MAP
# ============================================================

# Thermistor. GPIO34 is damaged; do not use it.
TEMP_ADC_PIN = 12

# Cooling relay / Peltier fan relay. Latest logic from your setup: 1=ON, 0=OFF.
COOLING_RELAY_PIN = 16
RELAY_ON = 1
RELAY_OFF = 0

# Cooling pump L298N
COOL_IN1_PIN = 18
COOL_IN2_PIN = 19
COOL_PWM_PIN = 32

# New algae feeding pump driver
ALGAE_IN1_PIN = 23
ALGAE_IN2_PIN = 14
ALGAE_PWM_PIN = 33

# OD + OLED I2C
I2C_SDA_PIN = 21
I2C_SCL_PIN = 22

# RGB LED used for OD illumination
RGB_R_PIN = 25
RGB_G_PIN = 26
RGB_B_PIN = 27

# ============================================================
# HARDWARE INIT
# ============================================================

cooling_relay = Pin(COOLING_RELAY_PIN, Pin.OUT)
cooling_relay.value(RELAY_OFF)

cool_in1 = Pin(COOL_IN1_PIN, Pin.OUT)
cool_in2 = Pin(COOL_IN2_PIN, Pin.OUT)
cool_pwm = PWM(Pin(COOL_PWM_PIN), freq=1000)

algae_in1 = Pin(ALGAE_IN1_PIN, Pin.OUT)
algae_in2 = Pin(ALGAE_IN2_PIN, Pin.OUT)
algae_pwm = PWM(Pin(ALGAE_PWM_PIN), freq=1000)

temp_adc = ADC(Pin(TEMP_ADC_PIN))
temp_adc.atten(ADC.ATTN_11DB)
temp_adc.width(ADC.WIDTH_12BIT)

i2c = I2C(0, scl=Pin(I2C_SCL_PIN), sda=Pin(I2C_SDA_PIN), freq=400000)
oled = ssd1306.SSD1306_I2C(128, 64, i2c)

rgb_light = RGBLight(red_pin=RGB_R_PIN, green_pin=RGB_G_PIN, blue_pin=RGB_B_PIN)

try:
    tcs = TCS34725(i2c)
    od_sensor = ODSensor(tcs=tcs, light=rgb_light, samples=10, delay_ms=80)
    od_model = AlgaeODModel(
        od_at_5000_cells_ml=OD_AT_5000_CELLS_ML,
        reference_cells_ml=5000.0,
    )
    print("OD sensor initialized.")
except Exception as e:
    print("OD sensor error:", e)
    tcs = None
    od_sensor = None
    od_model = AlgaeODModel()
    rgb_light.off()

# ============================================================
# THERMISTOR SETTINGS
# Wiring assumed:
# 3.3V --- 10k resistor --- GPIO12 --- thermistor --- GND
# ============================================================

SERIES_RESISTOR = 10000.0
NOMINAL_RESISTANCE = 10000.0
NOMINAL_TEMP_C = 25.0
BETA = 3950.0
ADC_MAX = 4095.0
filtered_temp = None

# ============================================================
# ACTUATORS
# ============================================================

def cooling_pump_on(pwm_value):
    pwm_value = max(0, min(1023, int(pwm_value)))
    cool_in1.value(1)
    cool_in2.value(0)
    cool_pwm.duty(pwm_value)


def cooling_pump_off():
    cool_pwm.duty(0)
    cool_in1.value(0)
    cool_in2.value(0)


def cooling_on():
    cooling_relay.value(RELAY_ON)


def cooling_off():
    cooling_relay.value(RELAY_OFF)


def algae_pump_on(pwm_value=ALGAE_PUMP_PWM):
    pwm_value = max(0, min(1023, int(pwm_value)))
    algae_in1.value(1)
    algae_in2.value(0)
    algae_pwm.duty(pwm_value)


def algae_pump_off():
    algae_pwm.duty(0)
    algae_in1.value(0)
    algae_in2.value(0)


def stop_everything():
    cooling_off()
    cooling_pump_off()
    algae_pump_off()
    rgb_light.off()
    try:
        oled.fill(0)
        oled.text("SYSTEM STOPPED", 0, 0)
        oled.text("Cooling OFF", 0, 18)
        oled.text("Pumps OFF", 0, 32)
        oled.show()
    except Exception:
        pass
    print("Everything stopped safely.")

# ============================================================
# TEMPERATURE
# ============================================================

def read_temperature():
    total = 0
    samples = 20
    for _ in range(samples):
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


def filter_temperature(temp):
    global filtered_temp
    if temp is None:
        return None
    if filtered_temp is None:
        filtered_temp = temp
    else:
        filtered_temp = 0.75 * filtered_temp + 0.25 * temp
    return filtered_temp


def cooling_pwm_from_pid(pid_output):
    if pid_output <= 0:
        return 0
    span = COOL_PUMP_MAX_PWM - COOL_PUMP_MIN_PWM
    return int(COOL_PUMP_MIN_PWM + span * (pid_output / 100.0))

# ============================================================
# OD + FEEDING
# ============================================================

def read_od_safe():
    if od_sensor is None:
        return {
            "raw_clear": "", "raw_red": "", "raw_green": "", "raw_blue": "",
            "od_clear": "", "od_red": "", "od_green": "", "od_blue": "", "od_mean": "",
            "cells_ml": "", "od_status": "NO_SENSOR",
        }

    try:
        od = od_sensor.read_od()
        cells_ml = od_model.od_to_cells_ml(od["od_mean"])
        od["cells_ml"] = cells_ml

        if cells_ml is None:
            od["od_status"] = "OD_ERROR"
        elif cells_ml < LOW_CELLS_ML:
            od["od_status"] = "LOW_FEED"
        elif cells_ml > HIGH_CELLS_ML:
            od["od_status"] = "HIGH_STOP"
        else:
            od["od_status"] = "OK"
        return od
    except Exception as e:
        print("OD read error:", e)
        return {
            "raw_clear": "", "raw_red": "", "raw_green": "", "raw_blue": "",
            "od_clear": "", "od_red": "", "od_green": "", "od_blue": "", "od_mean": "",
            "cells_ml": "", "od_status": "OD_ERROR",
        }


def algae_pump_seconds_for_ml(volume_ml):
    if ALGAE_PUMP_FLOW_ML_MIN <= 0:
        return 0
    return (volume_ml / ALGAE_PUMP_FLOW_ML_MIN) * 60.0


def run_algae_dose(volume_ml):
    volume_ml = max(0.0, min(float(volume_ml), MAX_DOSE_ML))
    run_s = algae_pump_seconds_for_ml(volume_ml)
    if run_s <= 0:
        return 0.0, 0.0

    print("Algae dose: %.1f mL, pump ON %.1f s" % (volume_ml, run_s))
    algae_pump_on(ALGAE_PUMP_PWM)
    time.sleep(run_s)
    algae_pump_off()
    return volume_ml, run_s


def feeding_decision_and_dose(od, elapsed_s, last_feed_s):
    cells_ml = od.get("cells_ml", "")

    if not isinstance(cells_ml, float):
        return "NO_FEED_OD_ERROR", 0.0, 0.0, last_feed_s

    if cells_ml > HIGH_CELLS_ML:
        algae_pump_off()
        return "NO_FEED_HIGH", 0.0, 0.0, last_feed_s

    if cells_ml >= LOW_CELLS_ML:
        return "NO_FEED_OK", 0.0, 0.0, last_feed_s

    if elapsed_s - last_feed_s < FEED_INTERVAL_S:
        return "WAIT_NEXT_FEED", 0.0, 0.0, last_feed_s

    # Because the stock is 5k cells/mL, a 50 mL pulse every 15 min gives
    # about 250,000 cells per pulse, or about 1,000,000 cells/hour.
    dose_ml = FEED_DOSE_ML
    given_ml, run_s = run_algae_dose(dose_ml)
    return "FED", given_ml, run_s, elapsed_s

# ============================================================
# DISPLAY + LOGGING
# ============================================================

def update_oled(elapsed_s, temp_c, pid_output, cooling_state, cool_pwm_value, od, feed_status):
    oled.fill(0)
    h = elapsed_s // 3600
    m = (elapsed_s % 3600) // 60
    s = elapsed_s % 60

    oled.text("DB4 Mussel", 0, 0)
    oled.text("%02d:%02d:%02d" % (h, m, s), 0, 10)

    if temp_c is None:
        oled.text("T: ERROR", 0, 22)
    else:
        oled.text("T:%.2fC->18" % temp_c, 0, 22)

    oled.text("PID:%3.0f P:%d" % (pid_output, cool_pwm_value), 0, 34)
    oled.text("Cool:%s" % ("ON" if cooling_state else "OFF"), 0, 44)

    cells_ml = od.get("cells_ml", "")
    if isinstance(cells_ml, float):
        oled.text("A:%d %s" % (int(cells_ml), feed_status[:4]), 0, 54)
    else:
        oled.text("A:" + od.get("od_status", "ERR"), 0, 54)

    oled.show()


def create_log_file():
    with open(LOG_FILE, "w") as f:
        f.write(
            "time_s,temp_c,filtered_temp_c,raw_adc,target_temp_c,temp_error,pid_output,"
            "cooling_on,cooling_pump_pwm,"
            "raw_clear,raw_red,raw_green,raw_blue,"
            "od_clear,od_red,od_green,od_blue,od_mean,estimated_cells_ml,od_status,"
            "algae_stock_cells_ml,target_cells_ml,low_cells_ml,high_cells_ml,"
            "feed_status,dose_ml,dose_run_s,algae_pump_pwm,"
            "tank_volume_ml,estimated_consumption_cells_ml_h\n"
        )


def v(value):
    if value is None:
        return ""
    return value


def log_data(elapsed_s, temp, filtered, raw_adc, error, pid_output, cooling_state, cool_pwm_value, od, feed_status, dose_ml, dose_run_s):
    with open(LOG_FILE, "a") as f:
        f.write(
            "{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{}\n".format(
                elapsed_s,
                v(temp),
                v(filtered),
                raw_adc,
                TARGET_TEMP_C,
                error,
                pid_output,
                1 if cooling_state else 0,
                cool_pwm_value,
                od.get("raw_clear", ""),
                od.get("raw_red", ""),
                od.get("raw_green", ""),
                od.get("raw_blue", ""),
                od.get("od_clear", ""),
                od.get("od_red", ""),
                od.get("od_green", ""),
                od.get("od_blue", ""),
                od.get("od_mean", ""),
                od.get("cells_ml", ""),
                od.get("od_status", ""),
                ALGAE_STOCK_CELLS_ML,
                TARGET_CELLS_ML,
                LOW_CELLS_ML,
                HIGH_CELLS_ML,
                feed_status,
                dose_ml,
                dose_run_s,
                ALGAE_PUMP_PWM,
                TANK_VOLUME_ML,
                MUSSEL_CONSUMPTION_CELLS_ML_H,
            )
        )

# ============================================================
# MAIN LOOP
# ============================================================

def main():
    print("====================================")
    print("DB4 FINAL SYSTEM WITH ALGAE FEEDING")
    print("Target temperature:", TARGET_TEMP_C, "C")
    print("Mussel tank target:", TARGET_CELLS_ML, "cells/mL")
    print("Feed below:", LOW_CELLS_ML, "cells/mL")
    print("Stop feed above:", HIGH_CELLS_ML, "cells/mL")
    print("Algae stock:", ALGAE_STOCK_CELLS_ML, "cells/mL")
    print("Dose:", FEED_DOSE_ML, "mL every", FEED_INTERVAL_S, "s when low")
    print("CSV:", LOG_FILE)
    print("====================================")

    create_log_file()

    pid = CoolingPID(
        setpoint=TARGET_TEMP_C,
        kp=Kp,
        ki=Ki,
        kd=Kd,
        deadband=DEADBAND_C,
        window_s=CONTROL_WINDOW_S,
    )

    start_time = time.time()
    last_od_time = -OD_INTERVAL_S
    last_feed_s = -FEED_INTERVAL_S
    last_od = read_od_safe()
    feed_status = "START"

    try:
        while True:
            elapsed_s = int(time.time() - start_time)

            if RUN_TIME_S is not None and elapsed_s >= RUN_TIME_S:
                print("Experiment finished after", RUN_TIME_S, "seconds.")
                break

            temp, raw = read_temperature()
            filtered = filter_temperature(temp)

            pid_output, cooling_state, error = pid.update(filtered)
            cool_pwm_value = cooling_pwm_from_pid(pid_output)

            if cooling_state:
                cooling_on()
                cooling_pump_on(cool_pwm_value)
            else:
                cooling_off()
                cooling_pump_off()
                cool_pwm_value = 0

            dose_ml = 0.0
            dose_run_s = 0.0

            if elapsed_s - last_od_time >= OD_INTERVAL_S:
                last_od = read_od_safe()
                last_od_time = elapsed_s

                feed_status, dose_ml, dose_run_s, last_feed_s = feeding_decision_and_dose(
                    last_od, elapsed_s, last_feed_s
                )

            update_oled(elapsed_s, filtered, pid_output, cooling_state, cool_pwm_value, last_od, feed_status)

            log_data(
                elapsed_s, temp, filtered, raw, error, pid_output,
                cooling_state, cool_pwm_value, last_od,
                feed_status, dose_ml, dose_run_s
            )

            cells_txt = ""
            if isinstance(last_od.get("cells_ml", ""), float):
                cells_txt = "%d" % int(last_od["cells_ml"])

            print(
                "Time:%02d:%02d:%02d | Temp:%s | Cool:%s | PWM:%d | OD:%s | cells/mL:%s | Feed:%s" % (
                    elapsed_s // 3600,
                    (elapsed_s % 3600) // 60,
                    elapsed_s % 60,
                    "%.2f" % filtered if filtered is not None else "ERROR",
                    "ON" if cooling_state else "OFF",
                    cool_pwm_value,
                    "%.4f" % last_od["od_mean"] if isinstance(last_od.get("od_mean", ""), float) else "",
                    cells_txt,
                    feed_status,
                )
            )

            time.sleep(SAMPLE_INTERVAL_S)

    except KeyboardInterrupt:
        print("Stopped by user.")

    finally:
        stop_everything()


main()
