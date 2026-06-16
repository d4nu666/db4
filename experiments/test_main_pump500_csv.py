from machine import Pin, PWM, ADC, I2C
import time
import math
import lib.ssd1306 as ssd1306


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

# Fan / cooling relay on GPIO16
# Your relay logic:
# 1 = ON
# 0 = OFF
fan_relay = Pin(16, Pin.OUT)
fan_relay.value(0)      # OFF at startup

# Pump L298N motor driver
# ENA must be jumpered/enabled physically
# because GPIO25 is used by RGB red
INA = Pin(18, Pin.OUT)
INB = Pin(19, Pin.OUT)

# RGB LED for white / 4150K-like illumination
rgb_red = PWM(Pin(25), freq=1000)
rgb_green = PWM(Pin(26), freq=1000)
rgb_blue = PWM(Pin(27), freq=1000)

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
# WHITE LED SETTINGS
# ==================================================

# Approximate 4150K white from RGB LED
WHITE_R = 1023
WHITE_G = 720
WHITE_B = 430


# ==================================================
# THERMISTOR SETTINGS
# ==================================================

SERIES_RESISTOR = 10000
NOMINAL_RESISTANCE = 10000
NOMINAL_TEMP = 25
BETA = 3950
ADC_MAX = 4095


# ==================================================
# TEMPERATURE SETTINGS
# ==================================================

TARGET_TEMP = 18.0
MAX_TEST_TIME = 20 * 60     # 20 minutes
SAMPLE_INTERVAL = 2         # seconds


# ==================================================
# PUMP SETTINGS
# ==================================================

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

ATIME_VALUE = 0xEB          # around 50 ms

# Gain:
# 0x00 = 1x
# 0x01 = 4x
# 0x02 = 16x
# 0x03 = 60x
GAIN_VALUE = 0x01


# ==================================================
# FAN FUNCTIONS
# ==================================================

def fan_on():
    fan_relay.value(1)      # ON for your relay


def fan_off():
    fan_relay.value(0)      # OFF for your relay


# ==================================================
# PUMP FUNCTIONS
# ==================================================

def pump_on():
    INA.value(1)
    INB.value(0)


def pump_off():
    INA.value(0)
    INB.value(0)


# ==================================================
# WHITE LED FUNCTIONS
# ==================================================

def white_led_on():
    rgb_red.duty(WHITE_R)
    rgb_green.duty(WHITE_G)
    rgb_blue.duty(WHITE_B)


def white_led_off():
    rgb_red.duty(0)
    rgb_green.duty(0)
    rgb_blue.duty(0)


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


def read_temp_average(samples=8):
    values = []

    for i in range(samples):
        temp = read_temp_c()
        if temp is not None:
            values.append(temp)
        time.sleep_ms(30)

    if len(values) == 0:
        return None

    return sum(values) / len(values)


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

def show_screen(temp, fan_state, elapsed, clear, red, green, blue):
    oled.fill(0)

    oled.text(TEST_NAME + " TEST", 0, 0)

    if temp is None:
        oled.text("Temp: ERROR", 0, 12)
    else:
        oled.text("Temp:{:.1f}C".format(temp), 0, 12)

    oled.text("Fan:" + fan_state, 0, 24)
    oled.text("Time:{}s".format(elapsed), 0, 36)
    oled.text("OD C:{}".format(clear), 0, 48)

    oled.show()


def show_stop_screen(message):
    oled.fill(0)
    oled.text(message, 0, 8)
    oled.text("Fan OFF", 0, 24)
    oled.text("Pump OFF", 0, 40)
    oled.text("LED OFF", 0, 56)
    oled.show()


# ==================================================
# LOGGING FUNCTIONS
# ==================================================

def create_log_file():
    try:
        with open(LOG_FILE, "w") as f:
            f.write("time_s,test,temp_c,fan_state,clear,red,green,blue,white_r,white_g,white_b\n")

        print("Created log file:", LOG_FILE)

    except Exception as e:
        print("Could not create log file:", e)


def log_data(elapsed, temp, fan_state, clear, red, green, blue):
    try:
        with open(LOG_FILE, "a") as f:
            f.write("{},{},{},{},{},{},{},{},{},{},{}\n".format(
                elapsed,
                TEST_NAME,
                temp,
                fan_state,
                clear,
                red,
                green,
                blue,
                WHITE_R,
                WHITE_G,
                WHITE_B
            ))
            f.flush()

    except Exception as e:
        print("Log error:", e)


# ==================================================
# MAIN TEST
# ==================================================

def run_od_temperature_test():
    print("Starting", TEST_NAME, "test")
    print("Fan/cooling relay on GPIO16")
    print("Relay logic: 1 = ON, 0 = OFF")
    print("Pump uses GPIO18/GPIO19. ENA must be jumpered.")
    print("White RGB LED: R=25, G=26, B=27")
    print("White PWM:", WHITE_R, WHITE_G, WHITE_B)
    print("Data saved to", LOG_FILE)

    # Safe startup
    fan_off()
    pump_off()
    white_led_off()

    # Start pump
    if PUMP_ALWAYS_ON:
        pump_on()

    # Start white LED
    white_led_on()

    # Start OD sensor
    tcs_init()

    # Create CSV file
    create_log_file()

    start_time = time.time()
    fan_state = "OFF"

    while True:
        elapsed = time.time() - start_time
        elapsed_int = int(elapsed)

        temp = read_temp_average()
        clear, red, green, blue = read_tcs34725()

        # Safety stop after max time
        if elapsed >= MAX_TEST_TIME:
            print("Max test time reached. Stopping system.")
            fan_off()
            pump_off()
            white_led_off()
            show_stop_screen("STOP TIME")
            break

        # ==================================================
        # MAIN FAN CONTROL
        # Fan runs until 18 degrees is reached
        # ==================================================

        if temp is not None and temp > TARGET_TEMP:
            fan_on()
            fan_state = "ON"
        else:
            fan_off()
            fan_state = "OFF"

        show_screen(temp, fan_state, elapsed_int, clear, red, green, blue)
        log_data(elapsed_int, temp, fan_state, clear, red, green, blue)

        print(
            "Time:", elapsed_int,
            "s | Temp:", temp,
            "C | Fan:", fan_state,
            "| Clear:", clear,
            "| R:", red,
            "| G:", green,
            "| B:", blue
        )

        time.sleep(SAMPLE_INTERVAL)


# ==================================================
# RUN
# ==================================================

try:
    run_od_temperature_test()

except KeyboardInterrupt:
    print("Stopped by user")

    fan_off()
    pump_off()
    white_led_off()

    oled.fill(0)
    oled.text("Test stopped", 0, 8)
    oled.text("Fan OFF", 0, 24)
    oled.text("Pump OFF", 0, 40)
    oled.text("LED OFF", 0, 56)
    oled.show()