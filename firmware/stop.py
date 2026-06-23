# ============================================================
# DB4 emergency stop. Run this manually to force every output OFF.
# Uses the same pin map as the rest of the firmware (config.py).
# ============================================================

from machine import Pin, PWM

import config

# Pumps / relays to their OFF level.
Pin(config.ALGAE_PUMP_PIN, Pin.OUT).value(config.ALGAE_PUMP_OFF)
Pin(config.WASTE_PUMP_PIN, Pin.OUT).value(config.WASTE_PUMP_OFF)
Pin(config.PELTIER_RELAY_PIN, Pin.OUT).value(config.PELTIER_OFF)

# Cooling pump (L298N) off, including PWM.
Pin(config.COOL_IN1_PIN, Pin.OUT).value(0)
Pin(config.COOL_IN2_PIN, Pin.OUT).value(0)
try:
    pwm = PWM(Pin(config.COOL_PWM_PIN), freq=config.COOL_PWM_FREQ)
    pwm.duty(0)
    pwm.deinit()
except Exception:
    pass

# RGB LED off.
for pin in (config.LED_R_PIN, config.LED_G_PIN, config.LED_B_PIN):
    try:
        p = PWM(Pin(pin), freq=1000)
        p.duty(0)
        p.deinit()
    except Exception:
        pass
    Pin(pin, Pin.OUT).value(0)

print("=" * 32)
print("DB4 SYSTEM STOPPED - all outputs OFF")
print("=" * 32)
