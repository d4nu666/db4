# ============================================================
# DB4 boot script. Runs automatically on power-up, before main.py.
# Its only job is to force every actuator into a safe OFF state
# so nothing pumps or cools during start-up.
#
# (The old boot.py ran a pump self-test on every boot - removed,
#  because it started pumps automatically with no supervision.)
# ============================================================
import sys
from machine import Pin, PWM
import os

try:
    os.chdir("/firmware")
except OSError:
    pass

for path in ["/", "/lib", "/firmware", "/firmware/lib"]:
    if path not in sys.path:
        sys.path.append(path)




import config

# Drive each output to its OFF level immediately.
Pin(config.ALGAE_PUMP_PIN, Pin.OUT).value(config.ALGAE_PUMP_OFF)
Pin(config.WASTE_PUMP_PIN, Pin.OUT).value(config.WASTE_PUMP_OFF)
Pin(config.PELTIER_RELAY_PIN, Pin.OUT).value(config.PELTIER_OFF)

# Cooling pump is PWM-only on GPIO32 - force duty to 0.
_cool = PWM(Pin(config.COOL_PWM_PIN), freq=config.COOL_PWM_FREQ)
_cool.duty(0)
_cool.deinit()

print("DB4 boot: actuators set to safe OFF state.")

# MicroPython runs main.py automatically after boot.py completes.
