# ============================================================
# DB4 OD SENSOR MODULE
# TCS34725 + RGB LED optical density measurement.
#
# OD = -log10((sample - dark) / (blank - dark))
#
# Default pure-water blank is taken from your pure_water.csv data:
# clear 9829.53, red 4074.61, green 3210.04, blue 2862.00
#
# Your 5k algae test gives OD_mean around 0.030, so:
# estimated_cells_ml = OD_mean / 0.030 * 5000
# ============================================================

import time
import math
from machine import Pin, PWM


class TCS34725:
    ADDRESS = 0x29
    COMMAND = 0x80

    REG_ENABLE = 0x00
    REG_ATIME = 0x01
    REG_CONTROL = 0x0F
    REG_CDATAL = 0x14

    ENABLE_PON = 0x01
    ENABLE_AEN = 0x02

    def __init__(self, i2c, address=ADDRESS, integration_time=0xEB, gain=0x01):
        self.i2c = i2c
        self.address = address
        self.write8(self.REG_ENABLE, self.ENABLE_PON)
        time.sleep_ms(10)
        self.write8(self.REG_ATIME, integration_time)  # about 50 ms
        self.write8(self.REG_CONTROL, gain)            # 4x gain
        self.write8(self.REG_ENABLE, self.ENABLE_PON | self.ENABLE_AEN)
        time.sleep_ms(60)

    def write8(self, reg, value):
        self.i2c.writeto_mem(self.address, self.COMMAND | reg, bytes([value]))

    def read16(self, reg):
        data = self.i2c.readfrom_mem(self.address, self.COMMAND | reg, 2)
        return data[0] | (data[1] << 8)

    def read_raw(self):
        c = self.read16(self.REG_CDATAL)
        r = self.read16(self.REG_CDATAL + 2)
        g = self.read16(self.REG_CDATAL + 4)
        b = self.read16(self.REG_CDATAL + 6)
        return {"clear": c, "red": r, "green": g, "blue": b}


class RGBLight:
    def __init__(self, red_pin=25, green_pin=26, blue_pin=27, freq=1000):
        self.red = PWM(Pin(red_pin), freq=freq)
        self.green = PWM(Pin(green_pin), freq=freq)
        self.blue = PWM(Pin(blue_pin), freq=freq)
        self.off()

    def set_pwm(self, r=0, g=0, b=0):
        self.red.duty(max(0, min(1023, int(r))))
        self.green.duty(max(0, min(1023, int(g))))
        self.blue.duty(max(0, min(1023, int(b))))

    def white(self):
        # Same white LED values used in your OD datasets.
        self.set_pwm(1023, 720, 430)

    def off(self):
        self.set_pwm(0, 0, 0)


class ODSensor:
    CHANNELS = ("clear", "red", "green", "blue")

    def __init__(self, tcs, light=None, samples=10, delay_ms=80):
        self.tcs = tcs
        self.light = light
        self.samples = samples
        self.delay_ms = delay_ms

        self.dark = {"clear": 0.0, "red": 0.0, "green": 0.0, "blue": 0.0}

        self.blank = {
            "clear": 9829.53,
            "red": 4074.61,
            "green": 3210.04,
            "blue": 2862.00,
        }

    def set_dark(self, clear=0, red=0, green=0, blue=0):
        self.dark = {
            "clear": float(clear),
            "red": float(red),
            "green": float(green),
            "blue": float(blue),
        }

    def set_blank(self, clear, red, green, blue):
        self.blank = {
            "clear": float(clear),
            "red": float(red),
            "green": float(green),
            "blue": float(blue),
        }

    def read_average(self, light_on=True):
        if self.light is not None:
            if light_on:
                self.light.white()
            else:
                self.light.off()
            time.sleep_ms(120)

        sums = {"clear": 0, "red": 0, "green": 0, "blue": 0}

        for _ in range(self.samples):
            raw = self.tcs.read_raw()
            for ch in self.CHANNELS:
                sums[ch] += raw[ch]
            time.sleep_ms(self.delay_ms)

        return {ch: sums[ch] / self.samples for ch in self.CHANNELS}

    def calibrate_dark(self):
        self.dark = self.read_average(light_on=False)
        return self.dark

    def calibrate_blank(self):
        # Put pure water in the OD path before calling this.
        self.blank = self.read_average(light_on=True)
        return self.blank

    def od_channel(self, channel, sample_value):
        sample_corrected = sample_value - self.dark[channel]
        blank_corrected = self.blank[channel] - self.dark[channel]

        if blank_corrected <= 0:
            return 0.0
        if sample_corrected <= 0:
            sample_corrected = 1.0

        ratio = sample_corrected / blank_corrected
        if ratio <= 0:
            ratio = 0.0001

        return -math.log10(ratio)

    def read_od(self):
        raw = self.read_average(light_on=True)

        od_clear = self.od_channel("clear", raw["clear"])
        od_red = self.od_channel("red", raw["red"])
        od_green = self.od_channel("green", raw["green"])
        od_blue = self.od_channel("blue", raw["blue"])

        # Your data shows clear and blue produce a stable algae signal.
        od_mean = (od_clear + od_blue) / 2.0

        return {
            "raw_clear": raw["clear"],
            "raw_red": raw["red"],
            "raw_green": raw["green"],
            "raw_blue": raw["blue"],
            "od_clear": od_clear,
            "od_red": od_red,
            "od_green": od_green,
            "od_blue": od_blue,
            "od_mean": od_mean,
        }


class AlgaeODModel:
    def __init__(self, od_at_5000_cells_ml=0.030, reference_cells_ml=5000.0):
        self.od_at_5000 = od_at_5000_cells_ml
        self.reference_cells_ml = reference_cells_ml

    def od_to_cells_ml(self, od_mean):
        if od_mean is None or od_mean == "":
            return None
        if self.od_at_5000 <= 0:
            return None
        cells = (od_mean / self.od_at_5000) * self.reference_cells_ml
        if cells < 0:
            cells = 0.0
        return cells
