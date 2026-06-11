from machine import ADC, Pin
import time
import math

# Thermistor middle point connected to GPIO34
adc = ADC(Pin(34))
adc.atten(ADC.ATTN_11DB)       # read up to about 3.3V
adc.width(ADC.WIDTH_12BIT)     # values 0-4095

# Adafruit 10k NTC thermistor values
SERIES_RESISTOR = 10000        # your fixed 10k resistor
THERMISTOR_NOMINAL = 10000     # 10k at 25C
TEMPERATURE_NOMINAL = 25       # 25C
BETA = 3950

def read_temp_c():
    raw = adc.read()

    if raw <= 0 or raw >= 4095:
        print("Bad reading:", raw)
        return None

    # Wiring:
    # 3V3 -> 10k resistor -> GPIO34 -> thermistor -> GND
    resistance = SERIES_RESISTOR * raw / (4095 - raw)

    steinhart = resistance / THERMISTOR_NOMINAL
    steinhart = math.log(steinhart)
    steinhart /= BETA
    steinhart += 1.0 / (TEMPERATURE_NOMINAL + 273.15)
    steinhart = 1.0 / steinhart
    temp_c = steinhart - 273.15

    return raw, resistance, temp_c

while True:
    result = read_temp_c()

    if result:
        raw, resistance, temp_c = result
        print("ADC:", raw, "Resistance:", round(resistance), "ohm", "Temp:", round(temp_c, 2), "C")

    time.sleep(1)