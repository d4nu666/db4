from machine import Pin, ADC
import time
import math

# ==================================================
# THERMISTOR TEST - GPIO35
# 10k NTC thermistor + 10k series resistor
# ==================================================

THERMISTOR_PIN = 35

adc = ADC(Pin(THERMISTOR_PIN))
adc.atten(ADC.ATTN_11DB)
adc.width(ADC.WIDTH_12BIT)

SERIES_RESISTOR = 10000
NOMINAL_RESISTANCE = 10000
NOMINAL_TEMPERATURE = 25
BETA = 3950
ADC_MAX = 4095

print("Thermistor test started")
print("Thermistor pin: GPIO35")

def read_raw_average(samples=30):
    values = []

    for i in range(samples):
        raw = adc.read()
        values.append(raw)
        time.sleep_ms(10)

    # Remove extreme values to reduce noise
    values.sort()
    values = values[5:-5]

    total = 0
    count = 0

    for value in values:
        total += value
        count += 1

    return total / count

def read_temperature():
    raw = read_raw_average()

    if raw <= 0 or raw >= ADC_MAX:
        return raw, None, None

    resistance = SERIES_RESISTOR * raw / (ADC_MAX - raw)

    steinhart = resistance / NOMINAL_RESISTANCE
    steinhart = math.log(steinhart)
    steinhart /= BETA
    steinhart += 1.0 / (NOMINAL_TEMPERATURE + 273.15)
    steinhart = 1.0 / steinhart
    temp_c = steinhart - 273.15

    return raw, resistance, temp_c

while True:
    raw, resistance, temp_c = read_temperature()

    if temp_c is None:
        print("Invalid reading. Raw:", raw)
    else:
        print(
            "Raw avg:",
            round(raw, 1),
            "| Resistance:",
            int(resistance),
            "ohm | Temp:",
            round(temp_c, 2),
            "C"
        )

    time.sleep(1)