# ============================================================
# DB4 thermistor driver (10k NTC, Steinhart-Hart / beta model)
# ============================================================

import math
import time
from machine import Pin, ADC

import config


class Thermistor:
    def __init__(self, pin=config.THERMISTOR_PIN):
        self.adc = ADC(Pin(pin))
        self.adc.atten(ADC.ATTN_11DB)
        self.adc.width(ADC.WIDTH_12BIT)
        self._t0_k = config.NOMINAL_TEMPERATURE + 273.15

    def read_raw(self, samples=20):
        """Average valid ADC samples. Returns None if all invalid."""
        total = 0
        valid = 0
        for _ in range(samples):
            value = self.adc.read()
            if 0 < value < config.ADC_MAX:
                total += value
                valid += 1
            time.sleep_ms(5)
        return total / valid if valid else None

    def read(self, samples=20):
        """Return (raw_adc, resistance_ohm, temp_c). Any may be None."""
        raw = self.read_raw(samples)
        if raw is None:
            return None, None, None

        resistance = config.SERIES_RESISTOR * raw / (config.ADC_MAX - raw)

        # Beta-model Steinhart-Hart
        inv_t = (1.0 / self._t0_k) + (math.log(resistance / config.NOMINAL_RESISTANCE) / config.BETA)
        temp_c = (1.0 / inv_t) - 273.15
        return raw, resistance, temp_c
