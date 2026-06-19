from machine import Pin, PWM
import time

# ==================================================
# DB4 EMERGENCY STOP / STOP EVERYTHING
# ==================================================

# Relay logic for your relay module:
# ACTIVE LOW relay:
# 0 = ON
# 1 = OFF
RELAY_OFF = 1

# -----------------------------
# Relays
# -----------------------------
# Peltier / cooling / fan relay
fan_relay = Pin(16, Pin.OUT)

# Extra relay channel if connected
# Use this for waste pump / algae pump relay if you connected it here
relay_ch2 = Pin(17, Pin.OUT)

fan_relay.value(RELAY_OFF)
relay_ch2.value(RELAY_OFF)

# -----------------------------
# L298N pump motor driver
# -----------------------------
# IN1 -> GPIO18
# IN2 -> GPIO19
# ENA -> GPIO32
IN1 = Pin(18, Pin.OUT)
IN2 = Pin(19, Pin.OUT)

try:
    ENA = PWM(Pin(32), freq=1000)
    ENA.duty(0)
    ENA.deinit()
except:
    pass

IN1.value(0)
IN2.value(0)

# -----------------------------
# RGB LED OFF
# -----------------------------
# Your RGB LED pins
try:
    red = Pin(25, Pin.OUT)
    green = Pin(26, Pin.OUT)
    blue = Pin(27, Pin.OUT)

    red.value(0)
    green.value(0)
    blue.value(0)
except:
    pass

# -----------------------------
# Optional: also stop PWM on GPIO25
# only needed if you used GPIO25 as PWM before
# -----------------------------
try:
    pwm25 = PWM(Pin(25), freq=1000)
    pwm25.duty(0)
    pwm25.deinit()
except:
    pass

print("================================")
print("DB4 SYSTEM STOPPED")
print("Relays OFF")
print("Pump motor OFF")
print("RGB LED OFF")
print("PWM outputs OFF")
print("================================")

while True:
    time.sleep(1)