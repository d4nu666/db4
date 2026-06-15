from machine import Pin, ADC, I2C
import time
import math
import ssd1306

# =========================
# PIN SETUP
# =========================

peltier_relay = Pin(16, Pin.OUT)   # Relay for Peltier cooling
peltier_relay.value(1)             # OFF at startup because relay is ACTIVE LOW

# Thermistor ADC pin
TEMP_ADC_PIN = 34                  # Change if your thermistor is on another ADC pin
temp_adc = ADC(Pin(TEMP_ADC_PIN))
temp_adc.atten(ADC.ATTN_11DB)      # Allows reading up to around 3.3V
temp_adc.width(ADC.WIDTH_12BIT)    # 0 - 4095

# OLED
i2c = I2C(0, scl=Pin(22), sda=Pin(21), freq=400000)
oled = ssd1306.SSD1306_I2C(128, 64, i2c)

# =========================
# THERMISTOR SETTINGS
# =========================

SERIES_RESISTOR = 10000    # 10k resistor in voltage divider
NOMINAL_RESISTANCE = 10000 # thermistor resistance at 25C
NOMINAL_TEMP = 25          # Celsius
BETA = 3950                # common value for 10k NTC
ADC_MAX = 4095

# =========================
# TEST SETTINGS
# =========================

TARGET_TEMP = 18.0         # stop cooling at or below this temp
MAX_TEST_TIME = 20 * 60    # 20 minutes max safety limit
ON_TIME = 30               # Peltier ON for 30 sec
OFF_TIME = 10              # Peltier OFF for 10 sec between cycles


# =========================
# FUNCTIONS
# =========================

def peltier_on():
    peltier_relay.value(0)     # ACTIVE LOW = ON


def peltier_off():
    peltier_relay.value(1)     # ACTIVE LOW = OFF


def read_temp_c():
    raw = temp_adc.read()

    if raw <= 0:
        return None

    # Voltage divider calculation
    resistance = SERIES_RESISTOR / ((ADC_MAX / raw) - 1)

    # Beta equation
    steinhart = resistance / NOMINAL_RESISTANCE
    steinhart = math.log(steinhart)
    steinhart /= BETA
    steinhart += 1.0 / (NOMINAL_TEMP + 273.15)
    steinhart = 1.0 / steinhart
    temp_c = steinhart - 273.15

    return temp_c


def show_screen(temp, state, elapsed):
    oled.fill(0)
    oled.text("PELTIER TEST", 0, 0)

    if temp is None:
        oled.text("Temp: ERROR", 0, 16)
    else:
        oled.text("Temp: {:.1f} C".format(temp), 0, 16)

    oled.text("State: " + state, 0, 32)
    oled.text("Time: {}s".format(elapsed), 0, 48)
    oled.show()


# =========================
# MAIN TEST
# =========================

def run_peltier_test():
    print("Starting Peltier cooling test")
    print("Relay is ACTIVE LOW: 0 = ON, 1 = OFF")

    start_time = time.time()
    state = "OFF"
    peltier_off()

    while True:
        elapsed = time.time() - start_time
        temp = read_temp_c()

        if temp is not None:
            print("Time:", int(elapsed), "s | Temp:", round(temp, 2), "C | State:", state)
        else:
            print("Temperature read error")

        # Safety stop after max time
        if elapsed >= MAX_TEST_TIME:
            print("Max test time reached. Stopping Peltier.")
            peltier_off()
            show_screen(temp, "STOP TIME", int(elapsed))
            break

        # Stop cooling if target reached
        if temp is not None and temp <= TARGET_TEMP:
            print("Target temperature reached. Stopping Peltier.")
            peltier_off()
            show_screen(temp, "TARGET OK", int(elapsed))
            break

        # Turn Peltier ON
        state = "ON"
        peltier_on()
        for i in range(ON_TIME):
            elapsed = time.time() - start_time
            temp = read_temp_c()

            if temp is not None and temp <= TARGET_TEMP:
                peltier_off()
                show_screen(temp, "TARGET OK", int(elapsed))
                print("Target reached during ON cycle.")
                return

            show_screen(temp, state, int(elapsed))
            time.sleep(1)

        # Turn Peltier OFF briefly
        state = "OFF"
        peltier_off()
        for i in range(OFF_TIME):
            elapsed = time.time() - start_time
            temp = read_temp_c()
            show_screen(temp, state, int(elapsed))
            time.sleep(1)


# Run the test
try:
    run_peltier_test()

except KeyboardInterrupt:
    print("Stopped by user")
    peltier_off()
    oled.fill(0)
    oled.text("Test stopped", 0, 20)
    oled.text("Peltier OFF", 0, 40)
    oled.show()