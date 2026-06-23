from machine import Pin, PWM, ADC, I2C
import time
import math
import sys

# ==================================================
# DB4 CONSTANT TEMPERATURE TEST
# Only cooling pump + OLED + thermistor
# Algae pump OFF
# Waste pump OFF
# Logs data to temp_test.csv
# ==================================================

LOG_FILE = "temp_test.csv"

# ==================================================
# PIN SETUP
# ==================================================

# Thermistor
THERMISTOR_PIN = 35

# Cooling pump on L298N
# IN1 -> GPIO18
# IN2 -> GPIO19
# ENA -> GPIO32
PUMP_IN1_PIN = 18
PUMP_IN2_PIN = 19
PUMP_PWM_PIN = 32

# OLED I2C
OLED_SDA = 21
OLED_SCL = 22

# ==================================================
# PUMP SETTINGS
# ==================================================

PUMP_PWM = 700          # 0 to 1023
PUMP_FREQ = 1000

# ==================================================
# TEMPERATURE SETTINGS
# ==================================================

SERIES_RESISTOR = 10000
NOMINAL_RESISTANCE = 10000
NOMINAL_TEMPERATURE = 25
BETA = 3950
ADC_MAX = 4095

SAMPLES = 20
SAMPLE_DELAY_MS = 5

LOG_INTERVAL_SECONDS = 2

# ==================================================
# HARDWARE INIT
# ==================================================

# Cooling pump
pump_in1 = Pin(PUMP_IN1_PIN, Pin.OUT)
pump_in2 = Pin(PUMP_IN2_PIN, Pin.OUT)
pump_pwm = PWM(Pin(PUMP_PWM_PIN), freq=PUMP_FREQ)


# Thermistor ADC
adc = ADC(Pin(THERMISTOR_PIN))
adc.atten(ADC.ATTN_11DB)
adc.width(ADC.WIDTH_12BIT)

# OLED
oled = None
try:
    import ssd1306
    i2c = I2C(0, scl=Pin(OLED_SCL), sda=Pin(OLED_SDA), freq=400000)
    devices = i2c.scan()
    print("I2C devices:", [hex(d) for d in devices])

    if 0x3C in devices:
        oled = ssd1306.SSD1306_I2C(128, 64, i2c)
        oled.fill(0)
        oled.text("DB4 Temp Test", 0, 0)
        oled.text("OLED ready", 0, 15)
        oled.show()
        print("OLED ready")
    else:
        print("OLED not found at 0x3C")
except Exception as e:
    print("OLED init error:", e)
    oled = None

# ==================================================
# FUNCTIONS
# ==================================================

def cooling_pump_on(pwm_value=PUMP_PWM):
    pump_in1.value(1)
    pump_in2.value(0)
    pump_pwm.duty(pwm_value)

def cooling_pump_off():
    pump_pwm.duty(0)
    pump_in1.value(0)
    pump_in2.value(0)


def read_raw_average():
    total = 0
    valid = 0

    for _ in range(SAMPLES):
        raw = adc.read()

        if 0 < raw < ADC_MAX:
            total += raw
            valid += 1

        time.sleep_ms(SAMPLE_DELAY_MS)

    if valid == 0:
        return None

    return total / valid

def read_temperature():
    raw = read_raw_average()

    if raw is None:
        return None, None, None

    try:
        resistance = SERIES_RESISTOR * raw / (ADC_MAX - raw)

        steinhart = resistance / NOMINAL_RESISTANCE
        steinhart = math.log(steinhart)
        steinhart /= BETA
        steinhart += 1.0 / (NOMINAL_TEMPERATURE + 273.15)
        steinhart = 1.0 / steinhart
        temp_c = steinhart - 273.15

        return raw, resistance, temp_c

    except Exception:
        return raw, None, None

def format_time(seconds):
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    return "{:02d}:{:02d}:{:02d}".format(h, m, s)

def update_oled(elapsed_s, temp_c, raw, pump_pwm_value):
    if oled is None:
        return

    try:
        oled.fill(0)
        oled.text("DB4 Temp Test", 0, 0)
        oled.text("Time " + format_time(elapsed_s), 0, 12)

        if temp_c is not None:
            oled.text("Temp {:.2f} C".format(temp_c), 0, 26)
        else:
            oled.text("Temp ERROR", 0, 26)

        if raw is not None:
            oled.text("Raw {:.0f}".format(raw), 0, 40)
        else:
            oled.text("Raw ERROR", 0, 40)

        oled.text("Cool PWM {}".format(pump_pwm_value), 0, 54)
        oled.show()

    except Exception as e:
        print("OLED update error:", e)

def create_log_file():
    try:
        with open(LOG_FILE, "w") as f:
            f.write("time_s,time_hms,raw,resistance_ohm,temp_c,cooling_pwm,algae_pump,waste_pump\n")
        print("Logging to", LOG_FILE)
    except Exception as e:
        print("Log file error:", e)

def write_log(elapsed_s, raw, resistance, temp_c, pump_pwm_value):
    try:
        with open(LOG_FILE, "a") as f:
            f.write("{},{},{},{},{},{},OFF,OFF\n".format(
                elapsed_s,
                format_time(elapsed_s),
                "" if raw is None else round(raw, 2),
                "" if resistance is None else round(resistance, 2),
                "" if temp_c is None else round(temp_c, 2),
                pump_pwm_value
            ))
    except Exception as e:
        print("Write log error:", e)

def safe_stop():
    print("Stopping everything...")
    cooling_pump_off()

    if oled is not None:
        try:
            oled.fill(0)
            oled.text("TEST STOPPED", 0, 0)
            oled.text("Cooling OFF", 0, 16)
            oled.text("Algae OFF", 0, 32)
            oled.text("Waste OFF", 0, 48)
            oled.show()
        except:
            pass

# ==================================================
# MAIN LOOP
# ==================================================

print("====================================")
print("DB4 constant temperature test started")
print("ONLY cooling pump + OLED + thermistor active")
print("Algae pump forced OFF")
print("Waste pump forced OFF")
print("Thermistor pin: GPIO{}".format(THERMISTOR_PIN))
print("Cooling PWM pin: GPIO{}".format(PUMP_PWM_PIN))
print("Cooling PWM value:", PUMP_PWM)
print("Press CTRL+C to stop")
print("====================================")

create_log_file()

start_ms = time.ticks_ms()
last_log_ms = 0

try:
    cooling_pump_on(PUMP_PWM)

    while True:
        now_ms = time.ticks_ms()
        elapsed_s = time.ticks_diff(now_ms, start_ms) // 1000

    

        # Keep cooling pump ON permanently
        cooling_pump_on(PUMP_PWM)

        raw, resistance, temp_c = read_temperature()

        print("Time: {} | Temp: {} C | Raw: {} | Cooling PWM: {}".format(
            format_time(elapsed_s),
            "ERROR" if temp_c is None else "{:.2f}".format(temp_c),
            "ERROR" if raw is None else "{:.0f}".format(raw),
            PUMP_PWM
        ))

        update_oled(elapsed_s, temp_c, raw, PUMP_PWM)

        if time.ticks_diff(now_ms, last_log_ms) >= LOG_INTERVAL_SECONDS * 1000:
            write_log(elapsed_s, raw, resistance, temp_c, PUMP_PWM)
            last_log_ms = now_ms

        time.sleep(1)

except KeyboardInterrupt:
    print("Keyboard interrupt")

except Exception as e:
    print("Fatal error:", e)

finally:
    safe_stop()