# ============================================================
# DB4 actuators: cooling pump, biological pumps, status LED.
# All pin/polarity details come from config.py.
# ============================================================

from machine import Pin, PWM

import config


class CoolingPump:
    """Cooling water pump on GPIO32 (PWM-only, no IN1/IN2 direction pins)."""

    def __init__(self):
        self.pwm = PWM(Pin(config.COOL_PWM_PIN), freq=config.COOL_PWM_FREQ)
        self.duty = 0
        self.off()

    def set(self, duty):
        """Set pump speed. duty is clamped to [0, PWM_MAX]."""
        duty = int(max(0, min(config.PWM_MAX, duty)))
        self.duty = duty
        self.pwm.duty(duty)

    def off(self):
        self.pwm.duty(0)
        self.duty = 0

    @property
    def is_on(self):
        return self.duty > 0


class OnOffPump:
    """Single-input pump (L9110S), driven ON/OFF."""

    def __init__(self, pin, on_value=1, off_value=0):
        self.pin = Pin(pin, Pin.OUT)
        self.on_value = on_value
        self.off_value = off_value
        self.state = 0
        self.off()

    def on(self):
        self.pin.value(self.on_value)
        self.state = 1

    def off(self):
        self.pin.value(self.off_value)
        self.state = 0


class StatusLED:
    """RGB LED used for both OD illumination (white) and status colour."""

    def __init__(self, r=config.LED_R_PIN, g=config.LED_G_PIN,
                 b=config.LED_B_PIN, freq=1000):
        self.r = PWM(Pin(r), freq=freq)
        self.g = PWM(Pin(g), freq=freq)
        self.b = PWM(Pin(b), freq=freq)
        self.off()

    def _set(self, r, g, b):
        self.r.duty(max(0, min(config.PWM_MAX, int(r))))
        self.g.duty(max(0, min(config.PWM_MAX, int(g))))
        self.b.duty(max(0, min(config.PWM_MAX, int(b))))

    def off(self):
        self._set(0, 0, 0)

    def red(self):
        self._set(config.PWM_MAX, 0, 0)

    def green(self):
        self._set(0, config.PWM_MAX, 0)

    def blue(self):
        self._set(0, 0, config.PWM_MAX)

    def white(self):
        # White-balance values matching the OD calibration datasets.
        self._set(1023, 720, 430)


def make_algae_pump():
    return OnOffPump(config.ALGAE_PUMP_PIN,
                     config.ALGAE_PUMP_ON, config.ALGAE_PUMP_OFF)


def make_waste_pump():
    return OnOffPump(config.WASTE_PUMP_PIN,
                     config.WASTE_PUMP_ON, config.WASTE_PUMP_OFF)


def make_peltier():
    return OnOffPump(config.PELTIER_RELAY_PIN,
                     config.PELTIER_ON, config.PELTIER_OFF)
