from machine import Pin, I2C
import time

# ==================================================
# DB4 OD CALIBRATION - 1.5k cells/mL
# Sensor: TCS34725
# I2C: SDA GPIO21, SCL GPIO22
# RGB LED: R GPIO25, G GPIO26, B GPIO27
# Output file: od_calibration.csv
# ==================================================

LOG_FILE = "algae_30k.csv"

SAMPLE_NAME = "algae_30k_cells_ml"
CONCENTRATION = 30000      # cells/mL

MEASUREMENT_TIME_S = 60       # total measuring time
SAMPLE_INTERVAL_S = 2         # seconds between readings

# ==================================================
# PINS
# ==================================================

i2c = I2C(0, scl=Pin(22), sda=Pin(21), freq=50000)

red = Pin(25, Pin.OUT)
green = Pin(26, Pin.OUT)
blue = Pin(27, Pin.OUT)

# ==================================================
# TCS34725 REGISTERS
# ==================================================

TCS_ADDR = 0x29
COMMAND_BIT = 0x80

ENABLE = 0x00
ATIME = 0x01
CONTROL = 0x0F
ID = 0x12

CDATAL = 0x14
RDATAL = 0x16
GDATAL = 0x18
BDATAL = 0x1A

PON = 0x01
AEN = 0x02

GAIN_1X = 0x00
GAIN_4X = 0x01
GAIN_16X = 0x02
GAIN_60X = 0x03

# ==================================================
# LED FUNCTIONS
# ==================================================

def led_off():
    red.value(0)
    green.value(0)
    blue.value(0)

def led_white():
    red.value(1)
    green.value(1)
    blue.value(1)

def led_blue():
    red.value(0)
    green.value(0)
    blue.value(1)

def led_green():
    red.value(0)
    green.value(1)
    blue.value(0)

# ==================================================
# SENSOR FUNCTIONS
# ==================================================

def write8(reg, value):
    i2c.writeto_mem(TCS_ADDR, COMMAND_BIT | reg, bytes([value]))

def read8(reg):
    return i2c.readfrom_mem(TCS_ADDR, COMMAND_BIT | reg, 1)[0]

def read16(reg):
    data = i2c.readfrom_mem(TCS_ADDR, COMMAND_BIT | reg, 2)
    return data[0] | (data[1] << 8)

def tcs_init():
    devices = i2c.scan()
    print("I2C devices:", [hex(d) for d in devices])

    if TCS_ADDR not in devices:
        raise RuntimeError("TCS34725 not found. Check SDA=21, SCL=22, VIN, GND.")

    print("TCS34725 ID:", hex(read8(ID)))

    # Integration time around 100 ms
    write8(ATIME, 0xD5)

    # Start with 4X gain
    # If values are too low, change to GAIN_16X
    # If values are near 65535, change to GAIN_1X
    write8(CONTROL, GAIN_4X)

    write8(ENABLE, PON)
    time.sleep_ms(10)

    write8(ENABLE, PON | AEN)
    time.sleep_ms(150)

def read_color():
    c = read16(CDATAL)
    r = read16(RDATAL)
    g = read16(GDATAL)
    b = read16(BDATAL)
    return r, g, b, c

def average_dark(seconds=5):
    led_off()
    time.sleep(1)

    total_r = 0
    total_g = 0
    total_b = 0
    total_c = 0
    n = 0

    start = time.time()

    while time.time() - start < seconds:
        r, g, b, c = read_color()
        total_r += r
        total_g += g
        total_b += b
        total_c += c
        n += 1
        time.sleep(0.2)

    return total_r / n, total_g / n, total_b / n, total_c / n

# ==================================================
# CSV SETUP
# ==================================================

def create_csv_if_needed():
    try:
        with open(LOG_FILE, "r") as f:
            pass
    except:
        with open(LOG_FILE, "w") as f:
            f.write(
                "time_s,sample,concentration_cells_ml,led_mode,"
                "r,g,b,c,dark_r,dark_g,dark_b,dark_c\n"
            )

# ==================================================
# MAIN PROGRAM
# ==================================================

led_off()
tcs_init()
create_csv_if_needed()

print("====================================")
print("OD CALIBRATION")
print("Sample:", SAMPLE_NAME)
print("Concentration:", CONCENTRATION, "cells/mL")
print("====================================")

print("Taking dark reading. Cover sensor. LED OFF.")
dark_r, dark_g, dark_b, dark_c = average_dark(seconds=5)

print("Dark R:", dark_r)
print("Dark G:", dark_g)
print("Dark B:", dark_b)
print("Dark C:", dark_c)

print("Put 1.5k cells/mL sample in OD holder.")
print("Make sure it is light-tight.")
time.sleep(3)

LED_MODE = "white"
led_white()

time.sleep(2)

print("Starting measurement...")

start_time = time.time()

while time.time() - start_time <= MEASUREMENT_TIME_S:
    t = time.time() - start_time

    r, g, b, c = read_color()

    line = "{:.1f},{},{},{},{},{},{},{},{:.2f},{:.2f},{:.2f},{:.2f}\n".format(
        t,
        SAMPLE_NAME,
        CONCENTRATION,
        LED_MODE,
        r,
        g,
        b,
        c,
        dark_r,
        dark_g,
        dark_b,
        dark_c
    )

    with open(LOG_FILE, "a") as f:
        f.write(line)

    print(
        "t={:.1f}s | {} | conc={} | R={} G={} B={} C={}".format(
            t, SAMPLE_NAME, CONCENTRATION, r, g, b, c
        )
    )

    time.sleep(SAMPLE_INTERVAL_S)

led_off()

print("====================================")
print("Finished OD calibration point.")
print("Data saved to:", LOG_FILE)
print("Now also measure a blank later with clean water.")
print("====================================")