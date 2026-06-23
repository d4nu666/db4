# ============================================================
# DB4 optical density sensing (TCS34725 + white LED).
# Estimates algae concentration from absorbance.
# The illumination LED is the shared StatusLED (actuators.py),
# so pass one in to avoid driving the RGB pins twice.
# ============================================================

import time
import math


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
        self._write8(self.REG_ENABLE, self.ENABLE_PON)
        time.sleep_ms(10)
        self._write8(self.REG_ATIME, integration_time)   # ~50 ms
        self._write8(self.REG_CONTROL, gain)             # 4x gain
        self._write8(self.REG_ENABLE, self.ENABLE_PON | self.ENABLE_AEN)
        time.sleep_ms(60)

    def _write8(self, reg, value):
        self.i2c.writeto_mem(self.address, self.COMMAND | reg, bytes([value]))

    def _read16(self, reg):
        data = self.i2c.readfrom_mem(self.address, self.COMMAND | reg, 2)
        return data[0] | (data[1] << 8)

    def read_raw(self):
        base = self.REG_CDATAL
        return {
            "clear": self._read16(base),
            "red": self._read16(base + 2),
            "green": self._read16(base + 4),
            "blue": self._read16(base + 6),
        }


class ODSensor:
    CHANNELS = ("clear", "red", "green", "blue")
    DEFAULT_BLANK = {"clear": 9829.53, "red": 4074.61,
                     "green": 3210.04, "blue": 2862.00}

    def __init__(self, tcs, light=None, samples=10, delay_ms=80):
        self.tcs = tcs
        self.light = light
        self.samples = samples
        self.delay_ms = delay_ms
        self.dark = {ch: 0.0 for ch in self.CHANNELS}
        self.blank = dict(self.DEFAULT_BLANK)

    def set_dark(self, **vals):
        self.dark = {ch: float(vals.get(ch, 0)) for ch in self.CHANNELS}

    def set_blank(self, **vals):
        self.blank = {ch: float(vals[ch]) for ch in self.CHANNELS}

    def read_average(self, light_on=True):
        if self.light is not None:
            self.light.white() if light_on else self.light.off()
            time.sleep_ms(120)

        sums = {ch: 0 for ch in self.CHANNELS}
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
        # Pure water must be in the OD path before calling this.
        self.blank = self.read_average(light_on=True)
        return self.blank

    def _od_channel(self, channel, sample_value):
        sample = sample_value - self.dark[channel]
        blank = self.blank[channel] - self.dark[channel]
        if blank <= 0:
            return 0.0
        if sample <= 0:
            sample = 1.0
        ratio = sample / blank
        if ratio <= 0:
            ratio = 0.0001
        return -math.log10(ratio)

    def read_od(self):
        raw = self.read_average(light_on=True)
        od = {ch: self._od_channel(ch, raw[ch]) for ch in self.CHANNELS}
        # Clear and blue give the most stable algae signal in our data.
        od_mean = (od["clear"] + od["blue"]) / 2.0

        result = {"raw_" + ch: raw[ch] for ch in self.CHANNELS}
        result.update({"od_" + ch: od[ch] for ch in self.CHANNELS})
        result["od_mean"] = od_mean
        return result


class AlgaeODModel:
    def __init__(self, od_at_5000_cells_ml=0.030, reference_cells_ml=5000.0):
        self.od_at_5000 = od_at_5000_cells_ml
        self.reference_cells_ml = reference_cells_ml

    def od_to_cells_ml(self, od_mean):
        if od_mean is None or od_mean == "" or self.od_at_5000 <= 0:
            return None
        cells = (od_mean / self.od_at_5000) * self.reference_cells_ml
        return max(0.0, cells)
