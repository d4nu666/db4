from machine import Pin
import time

# ==============================
# ALGAE PUMP TEST
# ==============================
# Algae pump motor driver pins
# Change these only if your wiring is different
ALGAE_IN1_PIN = 14
ALGAE_IN2_PIN = 23

IN1 = Pin(ALGAE_IN1_PIN, Pin.OUT)
IN2 = Pin(ALGAE_IN2_PIN, Pin.OUT)
PWM_PIN = 32  # Not used in this test, but defined for completeness
def algae_pump_stop():
    IN1.value(0)
    IN2.value(0)
    print("Algae pump OFF")

def algae_pump_forward():
    IN1.value(1)
    IN2.value(0)
    print("Algae pump ON forward")

def algae_pump_reverse():
    IN1.value(0)
    IN2.value(1)
    print("Algae pump ON reverse")

# Safety: start OFF
algae_pump_stop()
time.sleep(2)

def algae_pump_forward(PWM_value=600):
    IN1.value(1)
    IN2.value(0)
    print("Algae pump ON forward with PWM:", PWM_value)

print("Starting algae pump test...")
print("The pump will run forward for 5 seconds, stop, then repeat.")

for i in range(3):
    print("Test cycle:", i + 1)

    algae_pump_forward()
    time.sleep(5)

    algae_pump_stop()
    time.sleep(3)

print("Test finished.")
algae_pump_stop()