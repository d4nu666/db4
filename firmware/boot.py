# ============================================================
# DB4 boot script. Runs automatically on power-up, before main.py.
# Its only job is to force every actuator into a safe OFF state
# so nothing pumps or cools during start-up.
#
# (The old boot.py ran a pump self-test on every boot - removed,
#  because it started pumps automatically with no supervision.)
# ============================================================

from machine import Pin

import config

# Drive each output to its OFF level immediately.
Pin(config.ALGAE_PUMP_PIN, Pin.OUT).value(config.ALGAE_PUMP_OFF)
Pin(config.WASTE_PUMP_PIN, Pin.OUT).value(config.WASTE_PUMP_OFF)
Pin(config.PELTIER_RELAY_PIN, Pin.OUT).value(config.PELTIER_OFF)
Pin(config.COOL_IN1_PIN, Pin.OUT).value(0)
Pin(config.COOL_IN2_PIN, Pin.OUT).value(0)

print("DB4 boot: actuators set to safe OFF state.")

# MicroPython runs main.py automatically after boot.py completes.
