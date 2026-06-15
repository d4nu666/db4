from machine import Pin, PWM, ADC, I2C
import time
import math
import ssd1306

# =========================
# SETTINGS
# =========================

TARGET_TEMP = 18.0
UPDATE_DELAY = 1
LOG_FILE = "cooling_log.csv"

# =========================
# PINS
# =========================

fan_relay = Pin(17, Pin.OUT)

INA = Pin(18, Pin.OUT)
INB = Pin(19, Pin.OUT)
ENA = PWM(Pin(23), freq=1000)

thermistor_adc = ADC(Pin(34))
thermistor_adc.atten(ADC.ATTN_11DB)
thermistor_adc.width(ADC.WIDTH_12BIT)

i2c = I2C(0, scl=Pin(22), sda=Pin(21), freq=400000)
oled = ssd1306.SSD1306_I2C(128, 64, i2c)

# =========================
# THERMISTOR SETTINGS
# =========================

SERIES_RESISTOR = 10000
NOMINAL_RESISTANCE = 10000
NOMINAL_TEMP = 25
B_COEFFICIENT = 3950

# =========================
# FAN RELAY
# =========================
# Active LOW relay:
# 0 = ON
# 1 = OFF

def fan_on():
    fan_relay.value(0)

def fan_off():
    fan_relay.value(1)

# =========================
# PUMP CONTROL
# =========================

def pump_on(speed=850):
    INA.value(1)
    INB.value(0)
    ENA.duty(speed)

def pump_off():
    ENA.duty(0)
    INA.value(0)
    INB.value(0)

# =========================
# TEMPERATURE
# =========================

def read_adc_average(samples=20):
    total = 0
    for _ in range(samples):
        total += thermistor_adc.read()
        time.sleep_ms(5)
    return total / samples

def read_temperature():
    adc_value = read_adc_average()

    if adc_value <= 0:
        return None

    resistance = SERIES_RESISTOR * (4095 / adc_value - 1)

    # If temp goes opposite direction, replace above line with:
    # resistance = SERIES_RESISTOR / (4095 / adc_value - 1)

    steinhart = resistance / NOMINAL_RESISTANCE
    steinhart = math.log(steinhart)
    steinhart /= B_COEFFICIENT
    steinhart += 1.0 / (NOMINAL_TEMP + 273.15)
    steinhart = 1.0 / steinhart
    temp_c = steinhart - 273.15

    return temp_c

# =========================
# TIME FORMAT
# =========================

def format_time(seconds):
    minutes = seconds // 60
    secs = seconds % 60
    return "{:02d}:{:02d}".format(minutes, secs)

# =========================
# OLED
# =========================

def update_oled(temp, elapsed, cooling_active):
    oled.fill(0)

    oled.text("COOLING TEST", 0, 0)

    if temp is None:
        oled.text("Temp: ERROR", 0, 16)
    else:
        oled.text("Temp: {:.1f} C".format(temp), 0, 16)

    oled.text("Target: 18.0 C", 0, 28)
    oled.text("Time: " + format_time(elapsed), 0, 40)

    if cooling_active:
        oled.text("Fan:ON Pump:ON", 0, 52)
    else:
        oled.text("Fan:OFF Pump:OFF", 0, 52)

    oled.show()

# =========================
# CSV LOGGING
# =========================

def create_log_file():
    with open(LOG_FILE, "w") as file:
        file.write("time_s,temp_c,cooling\n")

def save_log(elapsed, temp, cooling_active):
    with open(LOG_FILE, "a") as file:
        if temp is None:
            temp_text = "ERROR"
        else:
            temp_text = "{:.2f}".format(temp)

        cooling_text = "ON" if cooling_active else "OFF"

        file.write("{},{},{}\n".format(elapsed, temp_text, cooling_text))

# =========================
# MAIN TEST
# =========================

def cooling_test():
    fan_off()
    pump_off()

    create_log_file()

    start_time = time.time()
    cooling_active = False

    oled.fill(0)
    oled.text("Starting test", 0, 0)
    oled.text("Saving CSV...", 0, 16)
    oled.text(LOG_FILE, 0, 28)
    oled.show()
    time.sleep(2)

    while True:
        temp = read_temperature()
        elapsed = int(time.time() - start_time)

        if temp is None:
            fan_off()
            pump_off()
            cooling_active = False

        elif temp > TARGET_TEMP:
            fan_on()
            pump_on(850)
            cooling_active = True

        else:
            fan_off()
            pump_off()
            cooling_active = False

        update_oled(temp, elapsed, cooling_active)
        save_log(elapsed, temp, cooling_active)

        print("Time:", elapsed, "Temp:", temp, "Cooling:", cooling_active)

        time.sleep(UPDATE_DELAY)

# =========================
# SAFE RUN
# =========================

try:
    cooling_test()

except KeyboardInterrupt:
    fan_off()
    pump_off()

    oled.fill(0)
    oled.text("Test stopped", 0, 0)
    oled.text("Data saved:", 0, 16)
    oled.text(LOG_FILE, 0, 28)
    oled.show()

    print("Stopped safely")
    print("Data saved in:", LOG_FILE)