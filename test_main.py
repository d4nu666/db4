from machine import Pin, PWM, ADC, I2C
import time
import math
import ssd1306


# ==================================================
# TEST MODE
# Change to "BLANK" or "SAMPLE"
# ==================================================

TEST_NAME = "BLANK"     # "BLANK" = clean water, "SAMPLE" = algae/sample water

if TEST_NAME == "BLANK":
    LOG_FILE = "blank.csv"
else:
    LOG_FILE = "sample.csv"


# ==================================================
# PIN SETUP
# ==================================================

# Peltier relay
# GPIO16, ACTIVE LOW:
# 0 = ON
# 1 = OFF
peltier_relay = Pin(16, Pin.OUT)
peltier_relay.value(0)      # OFF at startup

# Pump L298N motor driver
INA = Pin(18, Pin.OUT)
INB = Pin(19, Pin.OUT)
ENA = PWM(Pin(25), freq=1000)

# Thermistor ADC
TEMP_ADC_PIN = 34
temp_adc = ADC(Pin(TEMP_ADC_PIN))
temp_adc.atten(ADC.ATTN_11DB)
temp_adc.width(ADC.WIDTH_12BIT)

# OLED + TCS34725 RGB/OD sensor
i2c = I2C(0, scl=Pin(22), sda=Pin(21), freq=400000)

print("I2C devices:", [hex(x) for x in i2c.scan()])
# Expected:
# 0x3c = OLED
# 0x29 = TCS34725

oled = ssd1306.SSD1306_I2C(128, 64, i2c)


# ==================================================
# THERMISTOR SETTINGS
# ==================================================

SERIES_RESISTOR = 10000
NOMINAL_RESISTANCE = 10000
NOMINAL_TEMP = 25
BETA = 3950
ADC_MAX = 4095


# ==================================================
# PELTIER / TEMPERATURE SETTINGS
# This uses your working test logic
# ==================================================

TARGET_TEMP = 18.0
MAX_TEST_TIME = 20 * 60     # 20 minutes
ON_TIME = 30                # Peltier ON for 30 sec
OFF_TIME = 10               # Peltier OFF for 10 sec


# ==================================================
# PUMP SETTINGS
# ==================================================

PUMP_SPEED = 700            # 0 - 1023
PUMP_ALWAYS_ON = True


# ==================================================
# TCS34725 SETTINGS
# ==================================================

TCS_ADDR = 0x29
COMMAND_BIT = 0x80

REG_ENABLE = 0x00
REG_ATIME = 0x01
REG_CONTROL = 0x0F
REG_CDATAL = 0x14

ENABLE_PON = 0x01
ENABLE_AEN = 0x02

# Integration time
ATIME_VALUE = 0xEB          # around 50 ms

# Gain:
# 0x00 = 1x
# 0x01 = 4x
# 0x02 = 16x
# 0x03 = 60x
GAIN_VALUE = 0x01


# ==================================================
# PELTIER FUNCTIONS
# ==================================================

def peltier_on():
    peltier_relay.value(1)      # ACTIVE LOW = ON


def peltier_off():
    peltier_relay.value(0)      # ACTIVE LOW = OFF


# ==================================================
# PUMP FUNCTIONS
# ==================================================

def pump_on(speed=PUMP_SPEED):
    INA.value(1)
    INB.value(0)
    ENA.duty(speed)


def pump_off():
    ENA.duty(0)
    INA.value(0)
    INB.value(0)


# ==================================================
# TEMPERATURE FUNCTION
# ==================================================

def read_temp_c():
    raw = temp_adc.read()

    if raw <= 0 or raw >= ADC_MAX:
        return None

    try:
        resistance = SERIES_RESISTOR / ((ADC_MAX / raw) - 1)

        steinhart = resistance / NOMINAL_RESISTANCE
        steinhart = math.log(steinhart)
        steinhart /= BETA
        steinhart += 1.0 / (NOMINAL_TEMP + 273.15)
        steinhart = 1.0 / steinhart

        temp_c = steinhart - 273.15
        return temp_c

    except:
        return None


# ==================================================
# TCS34725 FUNCTIONS
# ==================================================

def tcs_write(reg, value):
    i2c.writeto_mem(TCS_ADDR, COMMAND_BIT | reg, bytes([value]))


def tcs_read_u16(reg):
    data = i2c.readfrom_mem(TCS_ADDR, COMMAND_BIT | reg, 2)
    return data[0] | (data[1] << 8)


def tcs_init():
    tcs_write(REG_ENABLE, ENABLE_PON)
    time.sleep_ms(10)

    tcs_write(REG_ENABLE, ENABLE_PON | ENABLE_AEN)
    tcs_write(REG_ATIME, ATIME_VALUE)
    tcs_write(REG_CONTROL, GAIN_VALUE)

    time.sleep_ms(100)


def read_tcs34725():
    clear = tcs_read_u16(REG_CDATAL)
    red = tcs_read_u16(REG_CDATAL + 2)
    green = tcs_read_u16(REG_CDATAL + 4)
    blue = tcs_read_u16(REG_CDATAL + 6)

    return clear, red, green, blue


# ==================================================
# OLED FUNCTIONS
# ==================================================

def show_screen(temp, state, elapsed, clear, red, green, blue):
    oled.fill(0)

    oled.text(TEST_NAME + " TEST", 0, 0)

    if temp is None:
        oled.text("Temp: ERROR", 0, 12)
    else:
        oled.text("Temp:{:.1f}C".format(temp), 0, 12)

    oled.text("Peltier:" + state, 0, 24)
    oled.text("Time:{}s".format(elapsed), 0, 36)
    oled.text("OD C:{}".format(clear), 0, 48)

    oled.show()


def show_stop_screen(message):
    oled.fill(0)
    oled.text(message, 0, 16)
    oled.text("Peltier OFF", 0, 32)
    oled.text("Pump OFF", 0, 48)
    oled.show()


# ==================================================
# LOGGING FUNCTIONS
# ==================================================

def create_log_file():
    try:
        with open(LOG_FILE, "w") as f:
            f.write("time_s,test,temp_c,peltier_state,clear,red,green,blue\n")

        print("Created log file:", LOG_FILE)

    except Exception as e:
        print("Could not create log file:", e)


def log_data(elapsed, temp, state, clear, red, green, blue):
    try:
        with open(LOG_FILE, "a") as f:
            f.write("{},{},{},{},{},{},{},{}\n".format(
                elapsed,
                TEST_NAME,
                temp,
                state,
                clear,
                red,
                green,
                blue
            ))

    except Exception as e:
        print("Log error:", e)


# ==================================================
# MAIN TEST
# ==================================================

def run_od_temperature_test():
    print("Starting", TEST_NAME, "test")
    print("Peltier relay on GPIO16")
    print("Relay is ACTIVE LOW: 0 = ON, 1 = OFF")
    print("Data saved to", LOG_FILE)
    print("Make sure the fan is powered and spinning before starting.")

    # Safe startup
    peltier_off()
    pump_off()

    # Start pump
    if PUMP_ALWAYS_ON:
        pump_on(PUMP_SPEED)

    # Start OD sensor
    tcs_init()

    # Create CSV file
    create_log_file()

    start_time = time.time()
    state = "OFF"

    while True:
        elapsed = time.time() - start_time
        elapsed_int = int(elapsed)

        temp = read_temp_c()
        clear, red, green, blue = read_tcs34725()

        if temp is not None:
            print(
                "Time:", elapsed_int,
                "s | Temp:", round(temp, 2),
                "C | Peltier:", state,
                "| Clear:", clear,
                "| R:", red,
                "| G:", green,
                "| B:", blue
            )
        else:
            print("Temperature read error")

        show_screen(temp, state, elapsed_int, clear, red, green, blue)
        log_data(elapsed_int, temp, state, clear, red, green, blue)

        # Safety stop after max time
        if elapsed >= MAX_TEST_TIME:
            print("Max test time reached. Stopping system.")
            peltier_off()
            pump_off()
            show_stop_screen("STOP TIME")
            break

        # Stop cooling if target reached
        if temp is not None and temp <= TARGET_TEMP:
            print("Target temperature reached. Stopping Peltier.")
            peltier_off()
            state = "OFF"
            show_screen(temp, "TARGET", elapsed_int, clear, red, green, blue)

            # Keep pump running and keep measuring OD
            # This does NOT stop the whole test.
            time.sleep(2)
            continue

        # Turn Peltier ON
        state = "ON"
        peltier_on()

        for i in range(ON_TIME):
            elapsed = time.time() - start_time
            elapsed_int = int(elapsed)

            temp = read_temp_c()
            clear, red, green, blue = read_tcs34725()

            if temp is not None and temp <= TARGET_TEMP:
                peltier_off()
                state = "OFF"
                show_screen(temp, "TARGET", elapsed_int, clear, red, green, blue)
                log_data(elapsed_int, temp, state, clear, red, green, blue)
                print("Target reached during ON cycle.")
                break

            show_screen(temp, state, elapsed_int, clear, red, green, blue)
            log_data(elapsed_int, temp, state, clear, red, green, blue)

            print(
                "Time:", elapsed_int,
                "s | Temp:", temp,
                "C | Peltier:", state,
                "| Clear:", clear,
                "| R:", red,
                "| G:", green,
                "| B:", blue
            )

            time.sleep(1)

        # Turn Peltier OFF briefly
        state = "OFF"
        peltier_off()

        for i in range(OFF_TIME):
            elapsed = time.time() - start_time
            elapsed_int = int(elapsed)

            temp = read_temp_c()
            clear, red, green, blue = read_tcs34725()

            show_screen(temp, state, elapsed_int, clear, red, green, blue)
            log_data(elapsed_int, temp, state, clear, red, green, blue)

            print(
                "Time:", elapsed_int,
                "s | Temp:", temp,
                "C | Peltier:", state,
                "| Clear:", clear,
                "| R:", red,
                "| G:", green,
                "| B:", blue
            )

            time.sleep(1)


# ==================================================
# RUN
# ==================================================

try:
    run_od_temperature_test()

except KeyboardInterrupt:
    print("Stopped by user")

    peltier_off()
    pump_off()

    oled.fill(0)
    oled.text("Test stopped", 0, 16)
    oled.text("Peltier OFF", 0, 32)
    oled.text("Pump OFF", 0, 48)
    oled.show()